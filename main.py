import argparse
import os
import json

from google import genai
from google.genai import types

import logging
from agents import architect, skill_creator
from commands import execute_protected_command
# from utils import  load_skill, write_skill_manifest, extract_skills_header
from utils import extract_skills_headers, load_skill, write_skill_manifest


def write_history_content(role, message) -> dict[any]:
    return {"role": role, "parts": [{"text": message}]}


def load_session(session_file):
    if os.path.exists(session_file):
        with open(session_file, 'r') as f:
            session_data = json.load(f)
        return session_data
    return None


def save_session(session_file, user_task, history: list, loaded_skills, learnings, system_prompt):
    return
    session_data = {
        "user_task": user_task,
        "history": history,
        "loaded_skills": loaded_skills,
        "learnings": learnings,
        "system_prompt": system_prompt
    }
    with open(session_file, 'w') as f:
        json.dump(session_data, f, indent=4)


client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def run_gemini_task(session_file, user_task=None):
    session_data = load_session(session_file)
    if session_data:
        print(f"Loaded session from {session_file}")
        user_task = session_data["user_task"]
        history = session_data["history"]
        loaded_skills = session_data["loaded_skills"]
        learnings = session_data["learnings"]
        system_instruction_from_session = session_data["system_prompt"]
        base_skills_initial = "\n\n---".join([load_skill(os.path.join(
            os.getcwd(), "skills"), s) for s in loaded_skills.keys()])

        chat = client.chats.create(
            model="gemini-2.5-flash",
            config={"system_instruction": system_instruction_from_session},
            history=[history[-1]]
        )
    else:
        print("Starting new session.")
        if not user_task:
            print("Error: user_task is required for a new session.")
            return
        SYSTEM_PROMPT = architect(user_task=user_task, base_skills=extract_skills_headers(
            os.path.join("skills")), absolute_path=os.path.join("skills"))
        history = []
        loaded_skills = {'unix-file-manipulation': True}
        learnings = {}

        base_skills_initial = "\n\n---".join([load_skill(os.path.join(
            os.getcwd(), "skills"), s) for s in loaded_skills.keys()])

        chat = client.chats.create(
            model="gemini-2.5-flash",
            config={"system_instruction": SYSTEM_PROMPT, "response_mime_type":"application/json"},
            history=history
        )
        system_instruction_from_session = SYSTEM_PROMPT

    
    
    initial_input_to_agent = f"USER_TASK: {user_task}"
    history.append(write_history_content(role="user", message=initial_input_to_agent))

    print(initial_input_to_agent)
    max_turns = 30
    turn = 0
    # return
    # return
    while True:
        turn += 1
        print(f"\n--- TURN {turn} ---")

        if history:
            response = chat.send_message(message=[
                genai.types.Part(text=history[-1]['parts'][0]['text']),
                genai.types.Part.from_bytes(data=bytes(base_skills_initial, encoding='utf-8'), mime_type="text/markdown")
            ])
            
        else:
            print("Error: No initial message in history for chat.send_message.")
            break

        try:
            clean_json = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)

            print(f"Agent Thought:{data['thought']}")
            history.append(write_history_content(
                role="model", message=data['thought']))

            if data.get("is_complete"):
                print("✅ Task Completed!")
                
                save_session(session_file, user_task, history, loaded_skills,
                             learnings, system_instruction_from_session)
                break

            if data.get("approval"):
                print(
                    f"Agent requires approval to proceed with the command:{json.dumps(data['command'], indent=4)}")
                user_approval = input("Approve command? (yes/no): ")
                if user_approval.lower() != 'yes':
                    print("Command disapproved by user. Exiting.")
                    save_session(session_file, user_task, history, loaded_skills,
                                 learnings, system_instruction_from_session)
                    return

            skills_to_load_content = ""
            if len(data["next_detected_skill_to_load"]):
                for skill_name in data["next_detected_skill_to_load"]:
                    if not skill_name in loaded_skills.keys():
                        skills_to_load_content += load_skill(os.path.join(
                            os.getcwd(), "skills"), skill_name) + "\n\n"
                        loaded_skills[skill_name] = True
            if not data["command"] or data["command"]["binary"]:
                print("Not command presnet")
            print(
                f"Executing: {data['command']['binary']} {data['command']['args']}")
            result_output = execute_protected_command(data['command'])

            print(f"result_output: {result_output}")
            print(f"skills:{skills_to_load_content}")

            learnings.update(data.get('learnings', {}))

            next_agent_input_parts = [
                f"Continue with the task:",
                f"OUTPUT:{result_output}",
                f"NEXT_SUBTASK:{data['next_subtask']}",
                f"LEARNINGS:{json.dumps(learnings)}",
                f"SKILLS:{skills_to_load_content}"
            ]

            user_feedback = input(
                "Your turn (press Enter to continue, 'exit' to quit, or type a message for the agent): ")
            if user_feedback.lower() == 'exit':
                print("Exiting interactive session.")
                save_session(session_file, user_task, history, loaded_skills,
                             learnings, system_instruction_from_session)
                break

            if user_feedback:
                next_agent_input_parts.append(
                    f"USER_FEEDBACK: {user_feedback}")

            history.append(write_history_content(
                role="user", message="\n".join(next_agent_input_parts)))
  
        except json.JSONDecodeError:
            print("Error: Agent failed to provide valid JSON. Requesting retry...")
            history.append(write_history_content(
                role="user", message="Error: Your last response was not valid JSON. Please repeat using the strict JSON schema."))

            if turn >= max_turns:
                print("Max turns reached due to JSON errors. Exiting.")
                save_session(session_file, user_task, history, loaded_skills,
                             learnings, system_instruction_from_session)
                break
        except Exception as e:
            print(f"Error:{e}")
            history.append(write_history_content(role="user", message=e))
            save_session(session_file, user_task, history, loaded_skills,
                     learnings, system_instruction_from_session)
            break



def generate_skill(skill_name, metadata):

    response = client.models.generate_content(
        model="gemini-2.5-flash", contents=skill_creator(skill=skill_name, metadata=metadata))
    write_skill_manifest(os.path.join(
        os.getcwd(), "skills"), skill_name, response.text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous Architect CLI")
    subparsers = parser.add_subparsers(
        dest="command", help="Available commands")

    # Subparser for run_gemini_task
    run_task_parser = subparsers.add_parser(
        "run-task", help="Run a Gemini task with the agent")
    run_task_parser.add_argument(
        "user_task", type=str, help="The user task to execute")
    run_task_parser.add_argument("--session-file", type=str, default="session.txt",
                                 help="Path to the session file (default: session.txt)")

    # Subparser for generate_skill
    generate_skill_parser = subparsers.add_parser(
        "generate-skill", help="Generate a new skill manifest")
    generate_skill_parser.add_argument(
        "skill_name", type=str, help="Name of the skill to generate")
    generate_skill_parser.add_argument(
        "metadata", type=str, help="Metadata for the skill as a JSON string")

    args = parser.parse_args()

    if args.command == "run-task":
        run_gemini_task(args.session_file, args.user_task)
    elif args.command == "generate-skill":
        metadata_dict = json.loads(args.metadata)
        generate_skill(args.skill_name, metadata_dict)
    else:
        parser.print_help()
