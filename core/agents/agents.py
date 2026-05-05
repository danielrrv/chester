from dataclasses import dataclass
import json
from typing import Dict, List, Optional
from abc import ABC, abstractmethod
from core.mcp.mcp_server_config import StdioServerParametersWithDescription
from core.models.model import Model
from core.skill.skill import Skill
from dataclasses import field


class Agent(ABC):

    task: str
    skills: List[Skill]
    available_mcps: Dict[str, Optional[StdioServerParametersWithDescription]]
    path: str
    avaible_sub_agents: List['Agent']
    # Sub-agents
    role: str
    role_description: str
    model: Model

    @abstractmethod
    def to_prompt(self) -> str:
        pass


@dataclass
class SubAgent(Agent):
    role: str
    role_description: str
    model: Model
    task: str
    skills: List[Skill]
    available_mcps: Dict[str, Optional[StdioServerParametersWithDescription]]
    path: str
    avaible_sub_agents: List['Agent'] = field(default_factory=list)

    def to_prompt(self) -> str:
        return f"""
        # ROLE
          You are a {self.role}. {self.role_description}, and your job is to help the user achieve their goal.
          You have access to a set of skills that you can use to achieve the goal {','.join([s.name for s in self.skills])} .
          You also have access to a set of MCP servers that you can use to achieve the goal: {json.dumps(self.available_mcps, indent=2)}.
          
        #INPUT CONTEXT:
        - **USER_TASK**: {self.task}
        - **ENVIRONMENT**: Absolute path is {self.path}.
        
        
        # OUTPUT FORMAT (Strict JSON)
        {json.dumps({
            "thought": "Analysis of progress, intent, and tool selection logic.",
            "summary_of_achievement": "Recap of successfully completed steps in this session.",
            "plan": [
                {"step": 1, "description": "Phase description",
                    "status": "COMPLETED/IN_PROGRESS/PENDING"}
            ],
            "environment": {
                "current_working_directory": self.path,
                "files_created": ["list_of_files"]
            },
            "command": {
                "mcp_call": {"server_name": "github|mongo|playwrigt", "tool_name": "browser", "arguments": {"arg1": "value1", "arg2": "value2"}},
                "binary": "executable_name",
                "args": ["arg1", "arg2"],
                "inline_script": "",
            },
            "needs_user_information": "True if there's a missing information, Put your question into response_to_user. False if you don't need extra information to proceed",
            "response_to_user": "Here is the summary of the files: [Summary Content...]",
            "learnings": "An Object of important and relevant learning from the session. Use key:value pair.",
            "next_detected_skill_to_load": ["slug_1", "slug_2"],
            "next_subtask": "The immediate next action after this command returns.",
            "needs_approval": "Indicate when you consider you need permission to proceed with the operation",
            "is_complete": False
        })}
         
      """


@dataclass
class Architect(Agent):

    task: str
    model: Model
    skills: List[Skill]
    path: str
    role: str = field(default="")
    available_mcps: Dict[str, Optional[StdioServerParametersWithDescription]] = field(
        default_factory=dict)
    role_description: str = field(default="")
    avaible_sub_agents: List[Agent] = field(default_factory=list)

    def to_prompt(self) -> str:
        return f"""

          # ROLE.
          You are the Autonomous Architect. You are responsible for both Strategic Planning and Tactical Execution. You analyze user intent, maintain a master execution plan, and generate precise system commands to achieve the goal.

          # OPERATING LOGIC (The Loop)
          1. **INTENT ANALYSIS**: On the first turn, decompose the USER_TASK into a multi-step PLAN.
          2. **PROGRESS EVALUATION**: On subsequent turns, analyze the HISTORY and ENVIRONMENT to update the status of your PLAN.
          3. **SKILL GAP ANALYSIS**: Check if the next step requires skills not currently in your BASE SKILLS. If so, request them in the JSON.
          4. **EXECUTION**: Synthesize the exact binary and arguments to progress the current subtask.

          # CONSTRAINTS
          - **Atomic Execution**: Only execute ONE command per turn.
          - **Artisan Quality**: Follow the strict formatting and deterministic rules defined in your SKILLS.
          - **State Awareness**: Every response must reflect the updated plan status and environment state.

          # BASE SKILLS (Injected Manifests). 
          - Read the corresponding skill and extract relevant commands and learn how to use it. Then apply it.
          - Do not call the binary as the skill name since the skill itself is not an executable.
          - Populate the next_detected_skill_to_load when you need to load a new skill. 
          
  
          ---
          {'\n---\n'.join([s.headers for s in self.skills])}
          ---

          # AVAILABLE MCP SERVERS:
          - Use mcp servers when needed.
          - When require one mcp server's tools, populate command with the mcp_call.
          ---
          {json.dumps(self.available_mcps, indent=3)}
          ---

          # AVAILABLE SUB-AGENTS:
          - Use sub-agents when you need to delegate a task to another agent.
          - When require one sub-agent, populate sub_agents field with the agent's role, task, and required skills.
          {json.dumps([ {'role': a.role, 'role_description': a.role_description, 'capabilities': [s.name for s in a.skills]} for a in self.avaible_sub_agents])}

          # INPUT CONTEXT
          - **USER_TASK**: {self.task}
          - **ENVIRONMENT**: Absolute path is {self.path}.
          - **HISTORY**: Sequential log of previous commands and outputs.

          # OUTPUT FORMAT (Strict JSON)
          {json.dumps({
                      "thought": "Analysis of progress, intent, and tool selection logic.",
                      "summary_of_achievement": "Recap of successfully completed steps in this session.",
                      "plan": [
                          {"step": 1, "description": "Phase description",
                           "status": "COMPLETED/IN_PROGRESS/PENDING"}
                      ],
                      "environment": {
                          "current_working_directory": self.path,
                          "files_created": ["list_of_files"]
                      },
                      "command": {
                          "mcp_call": {"server_name": "github|mongo|playwrigt", "tool_name": "browser", "arguments": {"arg1": "value1", "arg2": "value2"}},
                          "binary": "executable_name",
                          "args": ["arg1", "arg2"],
                          "inline_script": "",
                      },
                      "sub_agents": [
                          {
                              "agent_role": "role_description",
                              "agent_task": "task_description",
                              "skill_set": ["list_of_skills_to_use"]
                          }
                      ],
                      "needs_user_information": "True if there's a missing information, Put your question into response_to_user. False if you don't need extra information to proceed",
                      "response_to_user": "Here is the summary of the files: [Summary Content...]",
                      "learnings": "An Object of important and relevant learning from the session. Use key:value pair.",
                      "next_detected_skill_to_load": ["slug_1", "slug_2"],
                      "next_subtask": "The immediate next action after this command returns.",
                      "needs_approval": "Indicate when you consider you need permission to proceed with the operation",
                      "is_complete": False
                      })}

                >When to call a sub-agent: When you need to delegate a task to another agent, use the sub_agents field to define the agent's role, task, and required skills.


                IMPORTANT: Do not include inline_script and binary & args in the same response. Just pick the best way to execute the command.

                """





def skill_creator(skill, metadata):
    return f"""
       # ROLE
        You are a Senior Solutions Architect and Lead Developer. Your task is to generate a comprehensive "Skill Manifest" for a specific domain. This manifest will be used by other AI agents to understand how to execute tasks perfectly within that niche.

        # INPUT
        The user will provide a **Skill Topic** (e.g., "PostgreSQL Admin", "Tailwind Component Builder", "Kafka Auditor").

        # OUTPUT STRUCTURE
        You must output a structured Markdown file following this exact hierarchy:

        1. **Header Block**: name, description (when to trigger/not trigger), and License.
        2. **Skill Overview**: A concise summary for the agent use the skill.
        2. **Requirements for Outputs**: Formatting standards, error-handling rules, and industry-standard conventions.
        3. **Core Workflows**: Step-by-step instructions on how to handle data/tasks in this domain.
        4. **Code Style & Libraries**: Recommended libraries (e.g., pandas, openpyxl, pgx) and "Right vs. Wrong" code snippets.
        5. **Verification Checklist**: A mandatory list of checks the agent must perform before considering the task complete.
        6. **Best Practices**: Performance tips and common pitfalls.

        # INSTRUCTIONS FOR CREATION
        - **Precision Over Personality**: Focus on technical accuracy and "Determinism."
        - **Atomic Steps**: Break complex workflows into simple, executable code patterns.
        - **Guardrails**: Explicitly state what the agent should NOT do (e.g., "Do not hardcode secrets").
        - **Language**: Use the technical language of the domain (e.g., if it's SQL, talk about ACID, indices, and execution plans).

        # OUPUT FORMAT:
        ```markdown
        ----
        name: skill-name
        description: a concise skill description(50 words)
        ----
        
        <Relevant knowledge to an agent complete a tasks associated with the skill>
        ....
        
        ```
    
        # TRIGGER
        Generate a Skill Manifest for:{skill}
        Consider: {json.dumps(metadata)}

"""
