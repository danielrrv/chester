"""
cli.py
======

This module provides the command-line interface for the 'Autonomous Architect CLI'.
It handles argument parsing and dispatches commands to the appropriate core logic.
"""

import logging
import os
import json
import sys
import argparse
import asyncio

from core.mcp.mcp_manager import MCPManager
from core.mcp.mcp_server_config import StdioMCPServerConfiguration
from core.requests.request import ChesterRequest
from core.session.session import Model, Session
from core.task import run_task
from .agents.agents import Architect, skill_creator
from .utils.utils import write_skill_manifest
from .skill.skill import Skill
from .clients.clients import LLMClient, get_client

logger = logging.getLogger(__name__)

def generate_skill(client: LLMClient, skill_name: str, metadata: dict):
    """
    Generates a new skill manifest using the skill_creator agent.
    """
    logger.info(
        f'Generating skill manifest for: {skill_name} with metadata: {metadata}')
    response = client.generate_content(
        contents=skill_creator(skill=skill_name, metadata=metadata))
    write_skill_manifest(os.path.join(
        os.getcwd(), 'skills'), skill_name, response.text)
    logger.info(f'Skill manifest for {skill_name} created successfully.')

def main():
    # Ensure the script's directory is in the Python path for correct relative imports.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    # Set up argument parsing for command-line interface (CLI) commands.
    parser = argparse.ArgumentParser(description='Autonomous Architect CLI')
    subparsers = parser.add_subparsers(
        dest='command', help='Available commands')

    # --- Subparser for the 'run-task' command ---
    run_task_parser = subparsers.add_parser(
        'run-task', help='Run an LLM task with the agent')
    run_task_parser.add_argument(
        'user_task', type=str, help='The user task to execute')
    run_task_parser.add_argument('--session-id', type=str, default='session.txt',
                                 help='Path to the session file (default: session.txt)')
    run_task_parser.add_argument('--approve', type=bool, default=False,
                                 help='Approve the last procedure within the last task request')
    run_task_parser.add_argument('--user_response', type=str, default=False,
                                 help='The user response to a conversation inquiry')
    # Allow specifying LLM provider and model, defaulting to Gemini
    run_task_parser.add_argument('--llm-provider', type=str, default='gemini',
                                 help='The LLM provider to use (e.g., "gemini", "openai"). Default: "gemini"')
    run_task_parser.add_argument('--llm-model', type=str, default='gemini-2.5-flash',
                                 help='The specific LLM model to use (e.g., "gemini-2.5-flash", "gpt-4"). Default: "gemini-2.5-flash"')

    # --- Subparser for the 'generate-skill' command ---
    generate_skill_parser = subparsers.add_parser(
        'generate-skill', help='Generate a new skill manifest')
    generate_skill_parser.add_argument(
        'skill_name', type=str, help='Name of the skill to generate')
    generate_skill_parser.add_argument(
        'metadata', type=str, help='Metadata for the skill as a JSON string')
    # Allow specifying LLM provider and model, defaulting to Gemini
    generate_skill_parser.add_argument('--llm-provider', type=str, default='gemini',
                                       help='The LLM provider to use (e.g., "gemini", "openai"). Default: "gemini"')
    generate_skill_parser.add_argument('--llm-model', type=str, default='gemini-2.5-flash',
                                       help='The specific LLM model to use (e.g., "gemini-2.5-flash", "gpt-4"). Default: "gemini-2.5-flash"')

    args = parser.parse_args()

    if args.command == 'run-task':
        # Handle the 'run-task' command: find or create a session and run the task.
        session = Session.find_or_create(is_new=True, session_id=None)
        logger.info(
            f'Starting run-task for user_task: {args.user_task} with provider: {args.llm_provider}, model: {args.llm_model}')
        # Dynamically instantiate the LLM client
        client = get_client(provider=args.llm_provider,
                            model_name=args.llm_model)
        run_task(session=session, client=client, user_task=args.user_task)
        logger.info('Run-task completed.')
    elif args.command == 'generate-skill':
        # Handle the 'generate-skill' command: parse metadata and invoke skill generation.
        metadata_dict = json.loads(args.metadata)
        logger.info(
            f'Starting generate-skill for skill: {args.skill_name} with provider: {args.llm_provider}, model: {args.llm_model}')
        # Dynamically instantiate the LLM client
        client = get_client(provider=args.llm_provider,
                            model=Model[args.llm_model])
        generate_skill(client=client, skill_name=args.skill_name,
                       metadata=metadata_dict)
        logger.info(f'Generated skill {args.skill_name} successfully.')
    else:
        session_id = input('Architect> session_id: ').strip()
        # Default interactive chat loop if no specific command is given.
        session: Session = Session.find_or_create(session_id=session_id)
        session.add_skill(Skill(name='unix-file-manipulation'))
        logger.info('Starting interactive chat loop.')

        # Default LLM client for interactive mode.
        client = get_client(provider='gemini', model=Model.gemini_2_5_flash)
        mcp_server_config = StdioMCPServerConfiguration(config_json='config/mcp_servers.json')
        mcp_manager = MCPManager(mcp_server_config)
        user_approval = False
        
        request: ChesterRequest = ChesterRequest(
            user_approval=user_approval,
            user_response='',
            master_client= Model.gemini_2_5_flash,
            clients={ Model.gemini_2_5_flash: client},
            mcp_manager=mcp_manager,
            # Infer provider from model name for now.
            provider=client.model.value.split('-')[0],
            model=client.model.value,
            turn=session.turn
        )

        while True:
            try:               
                if not request.user_response:
                    user_task = input('Architect> ')
            
                    if user_task.lower() in ['exit', 'quit']:
                        logger.info('Exiting interactive chat.')
                        break
                        
                    request.set_system_instructions(
                       Architect(
                            task=user_task,
                            skills=[Skill(name=skill_name) for skill_name in Skill.all_names()],
                            available_mcps=StdioMCPServerConfiguration.get_descriptions(
                                mcp_manager.config),
                            path=os.getcwd(),
                            model=Model.gemini_2_5_flash
                        ).to_prompt()
                    )

                # For the interactive loop, we can default to Gemini, or add input for provider/model
                # For now, default to Gemini
                request.set_user_task(user_task)
                thought = asyncio.run(run_task(session=session, request=request))
                logger.info(f'Model response: {thought}')
                
                if session.last_response.is_complete:
                    session.last_response.needs_approval = False
                    session.last_response.needs_user_information = False
                    request.user_response = None
                    session.token_tracker.report()
                if session.last_response.needs_approval:
                    user_approval = input('Approve command? (yes/no): ').strip()
                    request.user_approval = True if user_approval.lower() =='yes' else False
                if session.last_response.needs_user_information and not session.last_response.is_complete:
                   user_response = input( 'Model requests you: ' + session.last_response.response_to_user + 'Your response:').strip()
                   request.user_response = user_response
                
                
             
            except KeyboardInterrupt:
                logger.info('Interactive chat interrupted by user.')
                break
            except Exception as e:
                logger.exception(
                    'An error occurred in the interactive chat loop:')

if __name__ == '__main__':
    main()
