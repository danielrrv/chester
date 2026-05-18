
import asyncio
from dataclasses import dataclass
import logging
import json
import copy
import queue
from typing import Dict, Union


from google import genai


from core.agents.agents import Agent
from core.encoders.json_encoder import JsonEncoder
from core.mcp.mcp_server_config import StdioMCPServerConfiguration
from core.requests.request import ChesterRequest
from core.responses.response import ChesterResponse, ChesterResponseException, UserResponse
from core.session.session import Session
from core.skill.skill import Skill

logger = logging.getLogger(__name__)

MAX_TURN = 30


# We need a function that receives a request. It has to execute it until the task is done.
# If the agent needs approval or needs user information, the agent can emit need task_responses_chan.
# In the case of needs approval or needs user information, the agent will do-while until the task_responses_chan has Approval or UserData
# back. It will have a default timeout of 60seconds until it returns the thread. In case the user responded, we resume the session with the new data,
# or with the approval or rejection.


async def run_indivual_agent_task(session: Session, request: ChesterRequest):

    logger.info(f"Using provider:{request.provider} | model: {request.model}")

    # Create a new chat session with the LLM client and system instructions.
    # The model name is retrieved from the client itself.
    client = client = request.clients.get(request.master_client)

    session.update_history(
        role='user', message=f'USER_TASK: {request.user_task}')

    while MAX_TURN > session.turn and not session.last_response.is_complete:

        session.turn = session.turn + 1
        logger.info(f'--- TURN {session.turn} ---')

        if session.last_response and not session.last_response.is_complete:
            if session.last_response.needs_approval:
                if not request.user_approval:
                    session.update_history(
                        role="user", message="Command disapproved by user")
                elif session.last_response.command and request.user_approval:
                    logger.info(
                        f'Executing command: {session.last_response.command}')
                    command_output = await session.last_response.command.execute(request.mcp_manager)
                    logger.info(f'Command result output: {command_output}')

                    session.update_history(role="user", message=str(UserResponse(
                        request.user_task, command_output, session.last_response.learnings, session.last_response.plan)))
            elif session.last_response.needs_user_information:
                if request.user_response:
                    session.update_history(role="user", message=str(
                        UserResponse(request.user_response, command_output=None)))

        # Prepare skills to be loaded, converting their content to genai.types.Part objects.
        # This ensures the model is aware of available tools for its reasoning process.
        # TODO: Abstract genai.types.Part for full LLM provider agnosticism.
        skills_to_load = [genai.types.Part.from_text(
            text=v.content) for _, v in session.skills.items() if not v.loaded]
        # Add the skills to the last message in the conversation.
        session.append_message_to_last_user_interaction(skills_to_load)
        # Combine the last message from the session history with any skills to be loaded as parts for the LLM.
        request.parts = session.last_message_parts()

        try:

            # Parse the raw response text into a structured ChesterResponse object.
            response: ChesterResponse = client.send_message(
                messages=request.parts)
            # stashing the last response.

            # Update token usage tracking.
            session.token_tracker.update(response.usage_metadata)

            if response.is_complete:
                # If the model indicates the task is complete, update history and log success.
                session.update_history(
                    role='model', message=response.response_to_user)
                session.turn = 0
                logger.info(
                    '✅ Task Completed! The sub-agent has finished the user task.')
                session.persist()
                break
            else:
                # If the task is not complete, log the agent's thought process and update history.
                logger.info(f'Agent Thought: {response.thought}')
                session.update_history(role='model', message=response.thought)

            session.last_response = copy.deepcopy(response)

            if response.next_detected_skill_to_load and len(response.next_detected_skill_to_load) > 0:
                # If the agent requests loading new skills, add them to the request's skill set.
                for skill_name in response.next_detected_skill_to_load:
                    if skill_name not in session.skills.keys():
                        logger.info(
                            f'Agent requests loading new skill: {skill_name}')
                        session.add_skill(Skill(name=skill_name, loaded=False))

            if response.needs_approval:
                logger.info("Agent requests you to approve")
                break
            if response.needs_user_information:
                logger.info("Agent needs information to proceed")
                break

            # Handle cases where no command is present and no user information is needed (potential JSON error from model).
            if not response.command and not response.needs_user_information:
                logger.warning(
                    'No command present in agent response, and no user information requested. Retrying with instruction.')
                session.update_history(
                    role='user', message='Incorrect json. The command was not populated. Please provide a valid command or request user information.')
                continue

            if response.command:
                # If a command is present and approved, log it and execute it.
                logger.info(f'Executing command: {response.command}')
                command_output = await response.command.execute(request.mcp_manager)
                logger.info(
                    f'Command result output: {response.command_result_output}')

                # Update the session history with the formatted input for the next turn.
                session.update_history(
                    role='user', message=str(UserResponse(response.next_subtask, command_output)))

        except ChesterResponseException:
            # Handle cases where the agent fails to provide valid JSON in its response.
            logger.error(
                'Agent failed to provide valid JSON. Requesting retry...')
            session.update_history(
                role='user', message='Error: Your last response was not valid JSON. Please repeat using the strict JSON schema.')
            # if turn >= max_turns:
            #     logger.error(
            #         'Max turns reached due to persistent JSON errors. Exiting.')
            #     break
        except Exception as e:
            # Catch any other unexpected exceptions during the task execution.
            logger.exception(
                'An unexpected error occurred during task execution:')
            session.update_history(
                role='user', message=f'Error: {str(e)}. Please try again or refine the task.')
        finally:
            session.persist()
    return session.last_assistant_message()


async def run_task(session: Session, request: ChesterRequest) -> str:
    """
    Orchestrates the interaction with the LLM to execute a user task.

    This function manages the conversational turns, skill loading, command execution,
    and user interactions (information requests, command approvals) within a session.
    It iteratively sends requests to the LLM and processes its responses
    until the task is complete or an error occurs.

    Args:
        session (Session): The current conversational session object.
        client (LLMClient): The instantiated LLM client for communication with the model.
        user_task (str): The initial task provided by the user.

    Returns:
        str: The last message from the model, typically indicating task completion,
             a request for user input, or an error summary.
    """
    # Initialize a ChesterRequest with the system prompt generated by the architect agent.
    # The architect agent is responsible for understanding the user's task and available skills.
    # The client's model is passed to the architect to tailor the prompt if needed.

    logger.info(f"Using provider:{request.provider} | model: {request.model}")

    # Create a new chat session with the LLM client and system instructions.
    # The model name is retrieved from the client itself.
    client = client = request.clients.get(request.master_client)

    session.set_client(
        client=client, system_instructions=request.system_prompt)

    if not session.last_response.needs_approval and not request.user_response:
        # Update the session history with the initial user task.
        session.update_history(
            role='user', message=f'USER_TASK: {request.user_task}')

    while MAX_TURN > session.turn and not session.last_response.is_complete:

        session.turn = session.turn + 1
        logger.info(f'--- TURN {session.turn} ---')

        if session.last_response and not session.last_response.is_complete:
            if session.last_response.needs_approval:
                if not request.user_approval:
                    session.update_history(
                        role="user", message="Command disapproved by user")
                elif session.last_response.command and request.user_approval:
                    logger.info(
                        f'Executing command: {session.last_response.command}')
                    command_output = await session.last_response.command.execute(request.mcp_manager)
                    logger.info(f'Command result output: {command_output}')

                    session.update_history(role="user", message=str(UserResponse(
                        request.user_task, command_output, session.last_response.learnings, session.last_response.plan)))
            elif session.last_response.needs_user_information:
                if request.user_response:
                    session.update_history(role="user", message=str(
                        UserResponse(request.user_response, command_output=None)))

        # Prepare skills to be loaded, converting their content to genai.types.Part objects.
        # This ensures the model is aware of available tools for its reasoning process.
        # TODO: Abstract genai.types.Part for full LLM provider agnosticism.
        skills_to_load = [genai.types.Part.from_text(
            text=v.content) for _, v in session.skills.items() if not v.loaded]
        # Add the skills to the last message in the conversation.
        session.append_message_to_last_user_interaction(skills_to_load)
        # Combine the last message from the session history with any skills to be loaded as parts for the LLM.
        request.parts = session.last_message_parts()

        try:

            # Parse the raw response text into a structured ChesterResponse object.
            response: ChesterResponse = client.send_message(
                messages=request.parts)
            # stashing the last response.

            # Update token usage tracking.
            session.token_tracker.update(response.usage_metadata)

            if response.is_complete:
                # If the model indicates the task is complete, update history and log success.
                session.update_history(
                    role='model', message=response.response_to_user)
                session.turn = 0
                session.persist()
                logger.info(
                    '✅ Task Completed! The agent has finished the user task.')
                break
            else:
                # If the task is not complete, log the agent's thought process and update history.
                logger.info(f'Agent Thought: {response.thought}')
                session.update_history(role='model', message=response.thought)

            session.last_response = copy.deepcopy(response)

            if response.next_detected_skill_to_load and len(response.next_detected_skill_to_load) > 0:
                # If the agent requests loading new skills, add them to the request's skill set.
                for skill_name in response.next_detected_skill_to_load:
                    if skill_name not in session.skills.keys():
                        logger.info(
                            f'Agent requests loading new skill: {skill_name}')
                        session.add_skill(Skill(name=skill_name, loaded=False))

           
            if response.sub_agents and len(response.sub_agents) > 0:
                logger.info(f'Agent created subagents: {response.sub_agents}')

                @dataclass
                class ExecutionSessionCollection:
                    name: str
                    session: Session
                    task: asyncio.Task
                agents_sessions: Dict[str, ExecutionSessionCollection] = {}

                async with asyncio.TaskGroup() as tg:
                    for sub_agent in response.sub_agents:
                        agent_session: Session = Session.find_or_create()
                        agents_sessions[agent_session.id] = ExecutionSessionCollection(
                            name=sub_agent.agent_role,
                            session=agent_session, task=None)
                        for skill in sub_agent.required_skills:
                            if skill not in agent_session.skills.keys():
                                agent_session.add_skill(
                                    Skill(name=skill, loaded=False))
                                agents_sessions[agent_session.id].task = tg.create_task(
                                    run_indivual_agent_task(session=agent_session,
                                                            request=ChesterRequest(
                                                                user_task=sub_agent.task,
                                                                system_prompt=Agent(
                                                                    role=sub_agent.agent_role,
                                                                    role_description=sub_agent.role_description,
                                                                    model=request.model,
                                                                    task=sub_agent.task,
                                                                    skills=[Skill(name=skill, loaded=False)
                                                                            for skill in sub_agent.required_skills],
                                                                    path=session.pwd,
                                                                    available_mcps=StdioMCPServerConfiguration.get_descriptions(request.mcp_manager.config))
                                                                .to_prompt(sub_agent.context),
                                                                master_client=request.master_client,
                                                                clients=request.clients,
                                                                mcp_manager=request.mcp_manager,
                                                                provider=request.provider,
                                                                model=request.model,
                                                                user_response = "",
                                                                turn=0
                                                            ))
                                )
                for session_id, execution_collection in agents_sessions.items():
                    print(
                        f"Task result for {session_id}: {execution_collection.task.result()}")
                    session.update_history(
                        role="user", message=f"Subagent  {execution_collection.name} is_complete={execution_collection.session.last_response.is_complete},\n The SubAgent {execution_collection.name} returns ={execution_collection.task.result()}\n\nSubAgent's plan: {json.dumps({execution_collection.session.last_response.plan})}")

            if response.needs_approval:
                logger.info("Agent requests you to approve")
                break
            if response.needs_user_information:
                logger.info("Agent needs information to proceed")
                break

            # Handle cases where no command is present and no user information is needed (potential JSON error from model).
            if not response.command and not response.needs_user_information and not (response.sub_agents and len(response.sub_agents) > 0):
                logger.warning(
                    'No command present in agent response, and no user information requested. Retrying with instruction.')
                session.update_history(
                    role='user', message='Incorrect json. The command was not populated. Please provide a valid command or request user information.')
                continue

            if response.command:
                # If a command is present and approved, log it and execute it.
                logger.info(f'Executing command: {response.command}')
                command_output = await response.command.execute(request.mcp_manager)
                logger.info(
                    f'Command result output: {response.command_result_output}')

                # Update the session history with the formatted input for the next turn.
                session.update_history(
                    role='user', message=str(UserResponse(response.next_subtask, command_output)))

        except ChesterResponseException:
            # Handle cases where the agent fails to provide valid JSON in its response.
            logger.error(
                'Agent failed to provide valid JSON. Requesting retry...')
            session.update_history(
                role='user', message='Error: Your last response was not valid JSON. Please repeat using the strict JSON schema.')
            # if turn >= max_turns:
            #     logger.error(
            #         'Max turns reached due to persistent JSON errors. Exiting.')
            #     break
        except Exception as e:
            # Catch any other unexpected exceptions during the task execution.
            logger.exception(
                'An unexpected error occurred during task execution:')
            session.update_history(
                role='user', message=f'Error: {str(e)}. Please try again or refine the task.')
        finally:
            session.persist()
    # await request.mcp_manager.cleanup
    if request.mcp_manager:
        mcp_manager = request.mcp_manager
        await mcp_manager.cleanup()
    return session.last_assistant_message()
