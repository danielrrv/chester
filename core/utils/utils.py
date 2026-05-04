import os
from pathlib import Path
import re
from typing import Optional



def extract_uuid_from_filename(filename: str) -> str:
    """
    Extracts a UUID from a string formatted as 'session_uuid.json'.
    Works with both standard 8-4-4-4-12 UUIDs and compact hex UUIDs.
    """
    # Regex breakdown:
    # session_ : matches the literal prefix
    # (.*?)    : captures any character (non-greedy) into Group 1
    # \.json   : matches the literal extension
    pattern = r"session_(.*?)\.json"
    
    match = re.search(pattern, filename)
    
    if match:
        return match.group(1)
    
    # Fallback or error handling for your orchestrator
    raise ValueError(f"Could not extract UUID from filename: {filename}")
    

                
def write_skill_manifest(skills_path: str, skill_name:str, content: str)-> None:
    try:
        os.makedirs(os.path.join(skills_path, skill_name), exist_ok=True)
    except OSError:
        raise
    with open(os.path.join(skills_path, skill_name, "SKILL.md"), "w") as skill_md:
        skill_md.write(content)
    return None