
from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections import abc
from dataclasses import dataclass
import logging
import copy

from typing import AsyncGenerator, Generator, Union, Any, List


from google import genai


from core.agents.agents import Agent
from core.commands.commands import AgentCommand
from core.mcp.mcp_server_config import StdioMCPServerConfiguration
from core.requests.request import ChesterRequest
from core.responses.response import ChesterResponse, ChesterResponseException, UserResponse
from core.session.session import Session
from core.skill.skill import Skill
from core.agents.async_execution import AsyncGeneratorTarget, AsyncExecutor 
logger = logging.getLogger(__name__)

MAX_TURN = 30

class Message(ABC):
    def __init__(self,text: str, command:AgentCommand = None):
        self.text = text
        self.command = command
    
    @abstractmethod
    def __repr__(self):
        pass
    @abstractmethod
    def __str__(self):
       pass

class InfoMessage(Message):
    def __init__(self, text: str):
        super().__init__(text)
    def __repr__(self):
        return f"InfoMessage(text={self.text})"
    def __str__(self):
        return super().__str__()
    
class AgentMessage(Message):
    def __init__(self, text):
        super().__init__( text)  
    def __repr__(self):
        return f"AgentMessage(text={self.text})"
    def __str__(self):
        return super().__str__()
class ErrorMessage(Message):
    def __init__(self,  text: str):
        super().__init__(text)
    def __repr__(self):
        return f"ErrorMessage( text={self.text})"
    def __str__(self):
        return super().__str__()
class ApprovalMessage(Message):
    def __init__(self,text: str, command: str):
        super().__init__(text, command)
        self.command = command
    def __repr__(self):
        return f"ApprovalMessage(text={self.text}, command={self.command})"
    def __str__(self):
        return super().__str__()

    
class NeedsUserInputMessage(Message):
    def __init__(self, session_id:str, text: str):
        super().__init__(session_id, text)
    def __repr__(self):
        return f"NeedsUserInputMessage(text={self.text})"
    def __str__(self):
        return super().__str__()

@dataclass
class ExecutionSessionCollection:
    name: str
    session: Session
    task: asyncio.Task
  
  
class Task:
    async def run(session: Session, request: ChesterRequest, is_sub_agent:bool = False)-> AsyncGenerator[Message, None]:
        """
        Orchestrates the interaction with the LLM to execute a user task.
        """

        yield InfoMessage(text=f"Using provider:{request.provider} | model: {request.model}| Session: {session.id}")

        # Create a new chat session with the LLM client and system instructions.
        # The model name is retrieved from the client itself.
        client = request.clients.get(request.master_client)

        await session.set_client(
            client=client, system_instructions=request.system_prompt)

        if not session.last_response.needs_approval and not request.user_response:
            # Update the session history with the initial user task.
            session.update_history(
                role='user', message=f'USER_TASK: {request.user_task}')

        while not session.last_response.is_complete:
            session.turn = session.turn + 1

            yield InfoMessage(text=f'--- TURN {session.turn} ---')

            if session.last_response and not session.last_response.is_complete:
                if session.last_response.needs_approval:
                    if not request.user_approval:
                        session.update_history(
                            role="user", message="Command disapproved by user")
                    elif session.last_response.command and request.user_approval:
                        yield InfoMessage( text=f'Executing command: {session.last_response.command}')
                        command_output = await session.last_response.command.execute(request.mcp_manager)

                        session.update_history(role="user", message=str(UserResponse(
                            request.user_task, command_output, session.last_response.learnings, session.last_response.plan)))
                elif session.last_response.needs_user_information:
                    if request.user_response:
                        session.update_history(role="user", message=str(
                            UserResponse(request.user_response, command_output=None)))

            # Prepare skills to be loaded, converting their content to genai.types.Part objects.
            # This ensures the model is aware of available tools for its reasoning process.
            # TODO: Abstract genai.types.Part for full LLM provider agnosticism.
            skills_to_load = [genai.types.Part(text=v.content) for _, v in session.skills.items() if not v.loaded]
            # Add the skills to the last message in the conversation.
            session.append_message_to_last_user_interaction(skills_to_load)
            # Combine the last message from the session history with any skills to be loaded as parts for the LLM.
            request.parts = session.last_message_parts()

            try:

                # Parse the raw response text into a structured ChesterResponse object.
                response: ChesterResponse = await client.send_message(
                    messages=request.parts)
                # stashing the last response.

                # Update token usage tracking.
                session.token_tracker.update(response.usage_metadata)
                session.title = response.intent
                if response.is_complete:
                    # If the model indicates the task is complete, update history and log success.
                    session.update_history(
                        role='model', message=response.response_to_user)
                    session.turn = 0
                    session.persist()
                    yield AgentMessage(text= session.last_assistant_message())
                    break
                else:
                    # If the task is not complete, log the agent's thought process and update history.
                    yield AgentMessage(text=f'Agent Thought: {response.thought}')
                    session.update_history(role='model', message=response.thought)

                session.last_response = copy.deepcopy(response)

                if response.next_detected_skill_to_load and len(response.next_detected_skill_to_load) > 0:
                    # If the agent requests loading new skills, add them to the request's skill set.
                    for skill_name in response.next_detected_skill_to_load:
                        if skill_name not in session.skills.keys():
                            yield InfoMessage(text=f'Agent requests loading new skill: {skill_name}')
                            session.add_skill(Skill(name=skill_name, loaded=False))


                if response.sub_agents and len(response.sub_agents) > 0:
                    yield InfoMessage(text=f'Creating sub-agents:  {len(response.sub_agents)} ')

                    targets:List[AsyncGeneratorTarget] =[] 
                    for sub_agent in response.sub_agents:
                        agent_session: Session = Session.find_or_create()


                        for skill in sub_agent.required_skills:
                            if skill not in agent_session.skills.keys():
                                agent_session.add_skill(Skill(name=skill, loaded=False))

                        sub_req = ChesterRequest(
                            user_task=sub_agent.task,
                            system_prompt=Agent(
                                role=sub_agent.agent_role,
                                role_description=sub_agent.role_description,
                                model=request.model,
                                task=sub_agent.task,
                                skills=[Skill(name=skill, loaded=False) for skill in sub_agent.required_skills],
                                path=session.pwd,
                                #TODO: Pull the in-memory-config
                                available_mcps=StdioMCPServerConfiguration.get_descriptions(request.mcp_manager.config)
                            ).to_prompt(sub_agent.context),
                            master_client=request.master_client,
                            clients=request.clients,
                            mcp_manager=request.mcp_manager,
                            provider=request.provider,
                            model=request.model,
                            user_response = "",
                            turn=0
                        )

                        targets.append(AsyncGeneratorTarget(Task.run, session=agent_session, request=sub_req, is_sub_agent = True))

                    async with AsyncExecutor.run(targets) as asx:
                        async for message in asx.read_from_queue():
                            AgentMessage(text= f"Sub-agent says: {message}")

                if response.needs_approval:
                    yield InfoMessage(text="Agent requests you to approve")
                    break
                if response.needs_user_information:
                    yield InfoMessage(text="Agent needs information to proceed")
                    break

                # Handle cases where no command is present and no user information is needed (potential JSON error from model).
                if not response.command and not response.needs_user_information and not (response.sub_agents and len(response.sub_agents) > 0):
                    yield InfoMessage(text=f'No command present in agent response, and no user information requested. Retrying.')
                    session.update_history(
                        role='user', message='Incorrect json. The command was not populated. Please provide a valid command or request user information.')
                    continue

                if response.command:
                    # If a command is present and approved, log it and execute it.
                    yield InfoMessage(text=f'Executing command: {response.command}')
                    command_output = await response.command.execute(request.mcp_manager)

                    # Update the session history with the formatted input for the next turn.
                    session.update_history(
                        role='user', message=str(UserResponse(response.next_subtask, command_output)))

            except ChesterResponseException:
                # Handle cases where the agent fails to provide valid JSON in its response.
                yield InfoMessage(text='Agent failed to provide valid JSON. Requesting retry...')
                session.update_history(
                    role='user', message='Error: Your last response was not valid JSON. Please repeat using the strict JSON schema.')
            except Exception as e:
                # Catch any other unexpected exceptions during the task execution.
                yield InfoMessage(text=f'An unexpected error occurred: {str(e)}')
                session.update_history(
                    role='user', message=f'Error: {str(e)}. Please try again or refine the task.')
            finally:
                session.persist()            
        if not is_sub_agent and request.mcp_manager:
            mcp_manager = request.mcp_manager
            await mcp_manager.cleanup()
        yield AgentMessage(text= session.last_assistant_message())
