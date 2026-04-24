# Autonomous Architect

Autonomous Architect is an AI-powered autonomous agent framework designed to interpret user tasks, formulate a plan, and execute system commands to achieve a specified goal.

## Features

- **AI-Powered Planning:** Leverages Google's Gemini models to understand tasks and create multi-step execution plans.
- **Extensible Skill System:** Capabilities can be extended by adding new "skills," which define how to interact with different tools or APIs.
- **Autonomous Skill Generation:** The agent can generate new skill manifests using its AI capabilities.
- **Interactive Execution:** Runs in a loop, executing commands, evaluating results, and adapting its plan until the task is complete.
- **Command-Line Interface:** Provides tools to run tasks and manage skills directly from the terminal.

## Installation

1.  **Prerequisites:**
    *   Python 3.x
    *   Git

2.  **Clone the repository:**
    bash
    git clone <repository_url>
    cd autonomous-architect
    

3.  **Install dependencies:**
    bash
    pip install -r requirements.txt
    

4.  **Set up your API Key:**
    The agent requires a Google Gemini API key. Set it as an environment variable:
    bash
    export GEMINI_API_KEY='your_api_key_here'
    

## Usage

The application is controlled via `core/main.py`.

### Running a Task

To have the agent perform a task, use the `run-task` command:

bash
python3 core/main.py run-task "Analyze the current directory and create a summary of its contents."


### Generating a New Skill

To generate a new skill manifest, use the `generate-skill` command:

bash
python3 core/main.py generate-skill "new-skill-name" '{"description": "A brief description of the new skill."}'

