"""
cli.py
======

This module provides the command-line interface for the 'Autonomous Architect CLI'.
It handles argument parsing and dispatches commands to the appropriate core logic.
It has been refactored to correctly process asynchronous generators, specifically
`Task.run`, ensuring all yielded messages are consumed and displayed.
"""

import logging
import os
import json
import sys
import argparse
import asyncio
from typing import Any, Dict, List, Optional, cast

from core.mcp.mcp_manager import MCPManager
from core.mcp.mcp_server_config import StdioMCPServerConfiguration
from core.requests.request import ChesterRequest
from core.session.session import Model, Session
from core.task.task import AgentMessage, ApprovalMessage, ErrorMessage, InfoMessage, Message, NeedsUserInputMessage, Task
from core.agents.agents import Architect, skill_creator
from core.utils.utils import write_skill_manifest
from core.skill.skill import Skill
from core.clients.clients import LLMClient, get_client

# Configure logging for the CLI application.
logger = logging.getLogger(__name__)

def generate_skill(client: LLMClient, skill_name: str, metadata: Dict[str, Any]) -> None:
    """
    Generates a new skill manifest using the `skill_creator` agent.

    This function interacts with an LLM client to create a skill manifest
    based on the provided skill name and metadata, then writes it to disk.

    Args:
        client (LLMClient): The LLM client instance to use for content generation.
        skill_name (str): The name of the skill to be generated.
        metadata (Dict[str, Any]): A dictionary containing metadata for the skill.
    """
    # Log the initiation of skill manifest generation with details.
    logger.info(
        f'Generating skill manifest for: {skill_name} with metadata: {metadata}'
    )
    # Call the LLM client to generate content using the skill_creator agent.
    # The skill_creator function constructs a prompt for the LLM.
    response = client.generate_content(
        contents=skill_creator(skill=skill_name, metadata=metadata)
    )
    # Construct the full path to save the skill manifest.
    skills_directory = os.path.join(os.getcwd(), 'skills')
    # Write the generated skill manifest content to a file.
    write_skill_manifest(skills_directory, skill_name, response.text)
    # Log successful creation of the skill manifest.
    logger.info(f'Skill manifest for {skill_name} created successfully.')

async def process_task_messages(task_runner: Any) -> None:
    """
    Asynchronously processes and logs messages yielded by an async task generator.

    This helper function iterates over an asynchronous generator, which is expected
    to yield various Message types (InfoMessage, ErrorMessage, etc.). Each message
    is logged to the console with specific color formatting based on its type.

    Args:
        task_runner (Any): An asynchronous generator (e.g., the result of `Task.run`).
    """
    # Asynchronously iterate through each message yielded by the task_runner.
    async for message in task_runner:
        # Use a match statement to handle different types of messages gracefully.
        match message:
            case InfoMessage(text=message.text):
                # Log informational messages in blue.
                logger.info(f'\033[94m{message.text}\033[0m')
            case ErrorMessage(text=message.text):
                # Log error messages in red.
                logger.error(f'\033[91m{message.text}\033[0m')
            case ApprovalMessage(text=message.text, command=message.command):
                # Log approval messages in yellow.
                logger.info(f'\033[93m{message.text}\033[0m')
            case NeedsUserInputMessage(text=message.text):
                # Log messages requesting user input in green.
                logger.info(f'\033[92m{message.text}\033[0m')
            case AgentMessage(text=message.text):
                # Log agent-specific messages in green.
                logger.info(f'\033[92m{message.text}\033[0m')
            case _:
                # Log any other unhandled message type as a general info message.
                logger.info(message.text)

async def async_main() -> None:
    """
    Main asynchronous function for the Autonomous Architect CLI.

    This function sets up argument parsing, dispatches commands ('run-task',
    'generate-skill', or interactive chat), and handles the lifecycle of the
    application. It has been refactored to correctly manage asynchronous
    operations, especially the `Task.run` async generator.
    """
    # Ensure the script's directory is in the Python path for correct relative imports.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Insert the script directory into sys.path if it's not already present.
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    # Set up argument parsing for command-line interface (CLI) commands.
    parser = argparse.ArgumentParser(description='Autonomous Architect CLI')
    # Create subparsers for different commands.
    subparsers = parser.add_subparsers(
        dest='command', help='Available commands', required=True # 'required=True' ensures a command is always selected
    )

    # --- Subparser for the 'run-task' command ---
    run_task_parser = subparsers.add_parser(
        'run-task', help='Run an LLM task with the agent' # Help message for the run-task command
    )
    run_task_parser.add_argument(
        'user_task', type=str, help='The user task to execute' # Argument for the user's task description
    )
    run_task_parser.add_argument(
        '--session-id', type=str, default='session.txt',
        help='Path to the session file (default: session.txt)' # Argument for specifying a session file
    )
    run_task_parser.add_argument(
        '--approve', type=bool, default=False, action=argparse.BooleanOptionalAction,
        help='Approve the last procedure within the last task request' # Boolean argument for approval
    )
    run_task_parser.add_argument(
        '--user-response', type=str, default=None,
        help='The user response to a conversation inquiry' # String argument for user's response
    )
    # Allow specifying LLM provider and model, defaulting to Gemini
    run_task_parser.add_argument(
        '--llm-provider', type=str, default='gemini',
        help='The LLM provider to use (e.g., "gemini", "openai"). Default: "gemini"' # Argument for LLM provider
    )
    run_task_parser.add_argument(
        '--llm-model', type=str, default='gemini-2.5-flash',
        help='The specific LLM model to use (e.g., "gemini-2.5-flash", "gpt-4"). Default: "gemini-2.5-flash"' # Argument for LLM model
    )

    # --- Subparser for the 'generate-skill' command ---
    generate_skill_parser = subparsers.add_parser(
        'generate-skill', help='Generate a new skill manifest' # Help message for generate-skill command
    )
    generate_skill_parser.add_argument(
        'skill_name', type=str, help='Name of the skill to generate' # Argument for the skill's name
    )
    generate_skill_parser.add_argument(
        'metadata', type=str, help='Metadata for the skill as a JSON string' # Argument for skill metadata in JSON format
    )
    # Allow specifying LLM provider and model, defaulting to Gemini
    generate_skill_parser.add_argument(
        '--llm-provider', type=str, default='gemini',
        help='The LLM provider to use (e.g., "gemini", "openai"). Default: "gemini"' # Argument for LLM provider
    )
    generate_skill_parser.add_argument(
        '--llm-model', type=str, default='gemini-2.5-flash',
        help='The specific LLM model to use (e.g., "gemini-2.5-flash", "gpt-4"). Default: "gemini-2.5-flash"' # Argument for LLM model
    )

    # Parse the command-line arguments.
    args = parser.parse_args()

    # Handle the 'run-task' command.
    if args.command == 'run-task':
        # Find or create a session based on the provided session ID.
        session = Session.find_or_create(is_new=True, session_id=args.session_id)
        # Log the initiation of the run-task command.
        logger.info(
            f'Starting run-task for user_task: {args.user_task} with provider: {args.llm_provider}, model: {args.llm_model}'
        )
        # Dynamically instantiate the LLM client based on arguments.
        client = get_client(provider=args.llm_provider,
                            model_name=args.llm_model)

        # Initialize MCPManager and StdioMCPServerConfiguration.
        mcp_server_config = StdioMCPServerConfiguration(config_json='config/mcp_servers.json')
        mcp_manager = MCPManager(mcp_server_config)

        # Create a ChesterRequest object with initial parameters from CLI arguments.
        request = ChesterRequest(
            user_approval=args.approve,
            user_response=args.user_response,
            master_client=client.model, # Use the client's model as master client.
            clients={client.model: client},
            mcp_manager=mcp_manager,
            provider=args.llm_provider,
            model=args.llm_model,
            turn=session.turn
        )
        # Set system instructions for the Architect agent based on the user task.
        request.set_system_instructions(
            Architect(
                task=args.user_task,
                skills=[Skill(name=skill_name) for skill_name in Skill.all_names()],
                available_mcps=StdioMCPServerConfiguration.get_descriptions(mcp_manager.config),
                path=os.getcwd(),
                model=client.model
            ).to_prompt()
        )
        # Set the user task in the request.
        request.set_user_task(args.user_task)

        # Call Task.run, which is an async generator, and process all yielded messages.
        task_runner = Task.run(session=session, request=request)
        await process_task_messages(task_runner)

        # Log completion of the run-task command.
        logger.info('Run-task completed.')

    # Handle the 'generate-skill' command.
    elif args.command == 'generate-skill':
        # Parse the metadata JSON string into a dictionary.
        try:
            metadata_dict = json.loads(args.metadata)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON metadata provided: {e}")
            sys.exit(1)

        # Log the initiation of the generate-skill command.
        logger.info(
            f'Starting generate-skill for skill: {args.skill_name} with provider: {args.llm_provider}, model: {args.llm_model}'
        )
        # Dynamically instantiate the LLM client.
        # Corrected: Use model_name for get_client instead of model for consistency.
        client = get_client(provider=args.llm_provider,
                            model_name=args.llm_model)
        # Generate the skill manifest.
        generate_skill(client=client, skill_name=args.skill_name,
                       metadata=metadata_dict)
        # Log successful skill generation.
        logger.info(f'Generated skill {args.skill_name} successfully.')

    # Handle the default interactive chat loop if no specific command is given.
    else:
        # Prompt the user for a session ID.
        session_id = input('Architect> session_id: ').strip()
        # Find or create a session.
        session: Session = Session.find_or_create(session_id=session_id)
        # Add a default skill for interactive mode.
        session.add_skill(Skill(name='unix-file-manipulation'))
        # Log entry into the interactive chat loop.
        logger.info('Starting interactive chat loop.')

        # Default LLM client for interactive mode.
        client = get_client(provider='gemini', model_name=Model.gemini_2_5_flash.value)
        mcp_server_config = StdioMCPServerConfiguration(config_json='config/mcp_servers.json')
        mcp_manager = MCPManager(mcp_server_config)

        # Initialize user approval and response for the first turn.
        user_approval_for_request: bool = False
        user_response_for_request: Optional[str] = None

        # Infinite loop for interactive chat.
        while True:
            try:
                # Prompt for user task if no response is pending from previous turn.
                if not user_response_for_request:
                    user_task = input('Architect> ')
                    # Exit condition for the chat loop.
                    if user_task.lower() in ['exit', 'quit']:
                        logger.info('Exiting interactive chat.')
                        break
                else:
                    # If there's a pending user response, the task is implicit.
                    user_task = session.last_response.user_task if session.last_response and session.last_response.user_task else ''

                # Create a new ChesterRequest for each turn.
                request = ChesterRequest(
                    user_approval=user_approval_for_request,
                    user_response=user_response_for_request,
                    master_client=client.model,
                    clients={client.model: client},
                    mcp_manager=mcp_manager,
                    provider=client.model.value.split('-')[0],
                    model=client.model.value,
                    turn=session.turn
                )

                # Set system instructions based on the Architect agent and current user task.
                request.set_system_instructions(
                    Architect(
                        task=user_task,
                        skills=[Skill(name=skill_name) for skill_name in Skill.all_names()],
                        available_mcps=StdioMCPServerConfiguration.get_descriptions(
                            mcp_manager.config
                        ),
                        path=os.getcwd(),
                        model=client.model
                    ).to_prompt()
                )
                # Set the current user task in the request.
                request.set_user_task(user_task)

                # Reset user response and approval for the upcoming processing.
                user_response_for_request = None
                user_approval_for_request = False

                # Run the Task as an async generator and process all messages.
                task_runner = Task.run(session=session, request=request)
                await process_task_messages(task_runner)

                # After all messages for the current turn are processed,
                # check session's last response for interactive needs.
                last_response = session.last_response

                # If the task is complete, reset relevant flags and report tokens.
                if last_response and last_response.is_complete:
                    last_response.needs_approval = False
                    last_response.needs_user_information = False
                    session.token_tracker.report()

                # Handle requests for user approval.
                if last_response and last_response.needs_approval:
                    user_input = input('Approve command? (yes/no): ').strip()
                    user_approval_for_request = user_input.lower() == 'yes'

                # Handle requests for additional user information.
                if last_response and last_response.needs_user_information and not last_response.is_complete:
                    response_prompt = f"Model requests you: {last_response.response_to_user} Your response:"
                    user_response_for_request = input(response_prompt).strip()

            except KeyboardInterrupt:
                # Gracefully handle user interruption (Ctrl+C).
                logger.info('Interactive chat interrupted by user.')
                break
            except Exception as e:
                # Catch and log any unexpected errors during the chat loop.
                logger.exception(
                    'An error occurred in the interactive chat loop:'
                )

if __name__ == '__main__':
    # Entry point of the CLI application.
    # Run the asynchronous main function using asyncio.
    asyncio.run(async_main())
