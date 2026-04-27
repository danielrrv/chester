import os
import json
import sys
import argparse
from dataclasses import dataclass, field



from google import genai


from core.request import ChesterRequest
from core.response import ChesterResponse
from core.session import Model, Session
from .agents import architect, skill_creator
from .utils import write_skill_manifest
from .skill import Skill


client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

model: Model = Model.gemini_2_5_flash


## Act as Senior python engineer and suggest a good roadmap for the application with entry point at Look main.py.
def run_gemini_task(session: Session, user_task):


    request: ChesterRequest = ChesterRequest(
        system_prompt=architect(user_task=user_task, base_skills= Skill.all_headers(), absolute_path=os.getcwd()),
        skills={'unix-file-manipulation': Skill(name='unix-file-manipulation')}
    )

    session.create_chat(
        client=client, system_instructions=request.system_prompt, model=model)

    session.update_history(role='user', message=f'USER_TASK: {user_task}')

    max_turns = 30
    turn = 0

    while True:
        turn += 1
        print(f'\n--- TURN {turn} ---')
        if turn > max_turns:
            print('Exhausted session')
            break
        
        skills_to_load = [genai.types.Part.from_text(text=v.content) for _, v in request.skills.items() if not v.loaded]
        request.parts = [genai.types.Part.from_text(text=session.last_message())] + skills_to_load 
        print(request.parts)
        raw_response = session.chat.send_message(message=request.parts)

        session.token_tracker.update(raw_response.usage_metadata)

        try:

            response: ChesterResponse = ChesterResponse.from_text(raw_response.text)

            if response.is_complete:
                session.update_history(role='model', message=response.response_to_user)
                print('✅ Task Completed!')
                break
            else:
                print(f"Agent Thought:{response.thought}\n\n")
                session.update_history(role='model', message=response.thought)

            if response.needs_user_information:
                response.user_response = input('model requests you:' + response.response_to_user +
                                               '\n. Your response:' if response.response_to_user else response.thought)

            if response.needs_approval:
                print(
                    f"Agent requires approval to proceed with the command:{response.command}")
                user_approval = input('Approve command? (yes/no): ')
                if user_approval.lower() != 'yes':
                    print('Command disapproved by user. Exiting.')
                    return

            if not response.command and (not response.needs_user_information == True):
                print('Not command present')
                session.update_history(role='user', message='Incorrect json. the command was populated.')
                continue
            # return
            if response.command:
                print(f"Executing: {response.command}")
                response.command_result_output = response.command.execute()
                print(f'result_output: {response.command_result_output}')

            if response.next_detected_skill_to_load and len(response.next_detected_skill_to_load) > 0:
                for skill_name in response.next_detected_skill_to_load:
                    if skill_name not in request.skills.keys():
                        print(f'Agent requests loading new skill: {skill_name}')
                        request.skills[skill_name]= Skill(name=skill_name)
                        
            next_agent_input_parts = [f'Continue with the task: {response.next_subtask}\n',
                                      f'OUTPUT:{(response.user_response if response.user_response else response.command_result_output)}\n',
                                      f'LEARNINGS:{response.learnings}']
            session.update_history(role='user', message='\n'.join(next_agent_input_parts))
        
        except json.JSONDecodeError:
            print('Error: Agent failed to provide valid JSON. Requesting retry...')
            session.update_history(
                role='user', message='Error: Your last response was not valid JSON. Please repeat using the strict JSON schema.')
            if turn >= max_turns:
                print('Max turns reached due to JSON errors. Exiting.')
                break
        except Exception as e:
            print(e)
            print(f'Error:{e}')
            session.update_history(role='user', message=str(e))
            raise
           
    return session.last_message()


def generate_skill(skill_name, metadata):
    response = client.models.generate_content(
        model='gemini-2.5-flash', contents = skill_creator(skill=skill_name, metadata=metadata))
    write_skill_manifest(os.path.join(
        os.getcwd(), 'skills'), skill_name, response.text)


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    parser = argparse.ArgumentParser(description='Autonomous Architect CLI')
    subparsers = parser.add_subparsers(
        dest='command', help='Available commands')
    run_task_parser = subparsers.add_parser(
        'run-task', help='Run a Gemini task with the agent')
    run_task_parser.add_argument(
        'user_task', type=str, help='The user task to execute')
    run_task_parser.add_argument('--session-file', type=str, default='session.txt',
                                 help='Path to the session file (default: session.txt)')
    generate_skill_parser = subparsers.add_parser(
        'generate-skill', help='Generate a new skill manifest')
    generate_skill_parser.add_argument(
        'skill_name', type=str, help='Name of the skill to generate')
    generate_skill_parser.add_argument(
        'metadata', type=str, help='Metadata for the skill as a JSON string')
    args = parser.parse_args()
    if args.command == 'run-task':
        session = Session.find_or_create(is_new=True, session_id=None)
        run_gemini_task(session=session, user_task=args.user_task)
    elif args.command == 'generate-skill':
        metadata_dict = json.loads(args.metadata)
        generate_skill(args.skill_name, metadata_dict)
    else:
        session: Session = Session.find_or_create(is_new=True, session_id=None)
        while True:
            user_task = input('Architect> ')
            thought = run_gemini_task(session=session, user_task=user_task)
            print(f'Model:{thought}')
            session.token_tracker.report()
