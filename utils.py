import os
from pathlib import Path
import re
from typing import Optional



def extract_skill_header(file_path: str) -> Optional[str]:
    """
    Lee un archivo Markdown de habilidades y extrae el bloque entre '---'.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Buscamos el contenido entre los dos primeros delimitadores '---'
            # re.DOTALL permite que el punto (.) incluya saltos de línea
            match = re.search(r'^---\s*(.*?)\s*---', content, re.DOTALL | re.MULTILINE)
            
            if match:
                return match.group(1).strip()
            return None
            
    except FileNotFoundError:
        print(f"Error: El archivo {file_path} no existe.")
        return None
    except Exception as e:
        print(f"Error inesperado: {e}")
        return None
    

        
def extract_skills_headers(skills_path):
    loaded_skills = ""
    root_folder = Path(skills_path)
    skill_folders: list[Path]= [f for f in  root_folder.iterdir() if f.is_dir()]    
    for folder in skill_folders:
        files = [f for f in folder.iterdir() if f.is_file() and f.name.endswith(".md")]
        for file in files:
            loaded_skills += extract_skill_header(os.path.join(skills_path, folder.name, file.name))+"\n\n---\n\n" 
                
    return loaded_skills
    
    
def load_skill(skills_path, skill_name):
    try:
         with open(os.path.join(skills_path, skill_name, "SKILL.md"), 'r', encoding='utf-8') as f:
            content = f.read()
            return content
    except FileNotFoundError:
        print(f"Error: El archivo {skills_path}/{skill_name}/SKILL.md no existe.")
        return None
    except Exception as e:
        print(f"Error inesperado: {e}")
        return None
          
                
def write_skill_manifest(skills_path: str, skill_name:str, content: str)-> None:
    try:
        os.makedirs(os.path.join(skills_path, skill_name), exist_ok=True)
    except OSError:
        raise
    with open(os.path.join(skills_path, skill_name, "SKILL.md"), "w") as skill_md:
        skill_md.write(content)
    return None