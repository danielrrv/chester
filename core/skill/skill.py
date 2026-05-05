from dataclasses import dataclass, field
import re
import sys
import os
from pathlib import Path
from typing import Optional



@dataclass
class Skill:
    _SKILL_PATH = "skills"
    _SKILL_FILE_NAME = "SKILL.md"
    name: str = field(default_factory=str)
    _headers: str = None
    _content: str = None
    loaded: bool = False

    def __dict__(self):
        return {"name": self.name, "loaded": self.loaded}

    @property
    def headers(self) -> Optional[str]:

        if self._headers:
            return self._headers
        try:
            return self.load_header()
        except FileNotFoundError:
            raise

    @property
    def content(self) -> Optional[str]:
        if self._content:
            return self._content
        try:
            self.loaded = True
            return self.load_content()
        except FileNotFoundError:
            raise
    
    @staticmethod
    def all_names() -> list[str]:
        return [f.stem for f in Path(Skill._SKILL_PATH).iterdir() if f.is_dir()]

    
    @staticmethod
    def all_headers() -> str:
        loaded_skills = ""
        skill_folders: list[Path] = [f for f in Path(
            os.path.join(Skill._SKILL_PATH)).iterdir() if f.is_dir()]
        for folder in skill_folders:
            try:
                loaded_skills += Skill(folder.stem).headers + "\n\n---\n\n"
            except FileNotFoundError:
                continue
        return loaded_skills

    def load_header(self) -> Optional[str]:
        try:
            with open(os.path.join(Skill._SKILL_PATH, self.name, Skill._SKILL_FILE_NAME), 'r', ) as f:
                content = f.read()

                match = re.search(r'^---\s*(.*?)\s*---',
                                  content, re.DOTALL | re.MULTILINE)

                if match:
                    self._headers = match.group(1).strip()
                    return self._headers
                return None

        except FileNotFoundError:
            print(f"The skill {self.name} doesn't exist")
            raise
        except Exception as e:
            print(
                f"Unexpected error loading name and description for '{self.name}' skill: {e}")
            return None

    def load_content(self) -> Optional[str]:
        try:
            with open(os.path.join(Skill._SKILL_PATH, self.name, Skill._SKILL_FILE_NAME), 'r', encoding='utf-8') as f:
                content = f.read()
                match = re.search(r'^---\s*(.*?)\s*---',
                                  content, re.DOTALL | re.MULTILINE)

                if match:
                    self._content = content[match.end() + 1:]
                    return self._content
                return None
        except FileNotFoundError:
            print(f"Skill {self.name} doesn't exist")
            return None
        except Exception as e:
            print(
                f"Unexpected error loading name and description for '{self.name}' skill: {e}")
            return None
