import argparse
import os
import json

from google import genai
from google.genai import types



from core.session import Session
from .agents import architect, skill_creator
from .commands import execute_protected_command
# from utils import  load_skill, write_skill_manifest, extract_skills_header
from .utils import extract_skills_headers, load_skill, write_skill_manifest


client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def run_gemini_task(session: Session, user_task):
    SYSTEM_PROMPT = architect(user_task=user_task, 
                              base_skills= extract_skills_headers(os.path.join("skills")), 
                              absolute_path=os.path.join("skills"))
    
    session.create_chat(client=client, system_instructions=SYSTEM_PROMPT, model="gemini-2.5-flash")
    
    loaded_skills = {'unix-file-manipulation': True}
    
    base_skills = [load_skill(os.path.join(os.getcwd(), "skills"), s) for s in loaded_skills.keys()]
    
    session.update_history(role="user", message=f"USER_TASK: {user_task}")
    
 

    max_turns = 30
    turn = 0
    while True:
        turn += 1
        print(f"\n--- TURN {turn} ---")
        if turn > max_turns:
            print("exhausted resource")
            break
        current_parts = [genai.types.Part.from_text(text = session.last_message())]
        
        if len(base_skills) > 0:
            for skill in base_skills:
                current_parts.append(genai.types.Part.from_text(text=f"NEW_SKILLS_LOADED:\n{skill}"))
        
        response = session.chat.send_message(message=current_parts)
           
        try:
            user_response = ""
            clean_json = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            if data.get("is_complete"):
                session.update_history(role="model", message=data["response_to_user"])
                print("✅ Task Completed!")
                break
            else:
                print(f"Agent Thought:{data['thought']}\n\n")
                session.update_history(role="model", message=data['thought'])

            if data['needs_user_information']:
                user_response = input("model requests you:" + data['response_to_user'] +"\n. Your response:" if data['response_to_user'] else data['thought'])
            
            
          
            
            if data.get("approval"):
                print(
                    f"Agent requires approval to proceed with the command:{json.dumps(data['command'], indent=4)}")
                user_approval = input("Approve command? (yes/no): ")
                if user_approval.lower() != 'yes':
                    print("Command disapproved by user. Exiting.")
                    return

            print(json.dumps(data, indent=4))
            print(data["needs_user_information"])
            if not data["command"] and not (data["needs_user_information"]==True):
                print("Not command presnet")
                session.update_history(role="user", message="Incorrect json. the command was populated.")
                continue
            
            result_output=""
            if data["command"]:
                print(f"Executing: {data['command']['binary']} {data['command']['args']}")
                result_output = execute_protected_command(data['command'])
                print(f"result_output: {result_output}")


            skills_to_load_content = ""
            if len(data["next_detected_skill_to_load"]):
                for skill_name in data["next_detected_skill_to_load"]:
                    if not skill_name in loaded_skills.keys():
                        skills_to_load_content += load_skill(os.path.join(
                            os.getcwd(), "skills"), skill_name) + "\n\n"
                        loaded_skills[skill_name] = True
                        
            
            print(f"skills-loaded:{skills_to_load_content}")
            learnings = data['learnings']
            
            # session.learnings.update(data.get('learnings', {}))
          

            next_agent_input_parts = [
                f"Continue with the task:",
                f"OUTPUT:{ user_response if user_response else result_output}",
                f"NEXT_SUBTASK:{data['next_subtask']}",
                f"LEARNINGS:{json.dumps(learnings)}",
                f"SKILLS:{skills_to_load_content}"
            ]
            session.update_history(role="user", message="\n".join(next_agent_input_parts))
        
                
  
        except json.JSONDecodeError:
            print("Error: Agent failed to provide valid JSON. Requesting retry...")
            session.update_history(
                role="user", message="Error: Your last response was not valid JSON. Please repeat using the strict JSON schema.")

            if turn >= max_turns:
                print("Max turns reached due to JSON errors. Exiting.")
                break
        except Exception as e:
            print(e)
            print(f"Error:{e}")
            session.update_history(role="user", message=str(e))
            raise
            break
        
    return session.last_message()


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
        session = Session.find_or_create(is_new=True, session_id=None)
        run_gemini_task(session=session, user_task=args.user_task)
    elif args.command == "generate-skill":
        metadata_dict = json.loads(args.metadata)
        generate_skill(args.skill_name, metadata_dict)
    else:
        # parser.print_help()
        session = Session.find_or_create(is_new=True, session_id=None)
        while True:
            user_task = input("Architect> ")
            thought = run_gemini_task(session=session, user_task=user_task)
            print(f"Model:{thought}")
        
# if __name__ == "__main__":
#     session:Session = Session.find_or_create(is_new=True, session_id=None)
#     session.persist()
   


