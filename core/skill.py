import sys
import os
from pathlib import Path
from core.utils import load_skill

class Skill:

    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.documentation = None
        self.loaded_sub_skills_docs = {}

    def load(self):
        print(f'Loading skill: {self.name}')
        skills_base_path = 'skills'
        primary_skill_loaded = False
        skill_content = load_skill(skills_base_path, self.name)
        if skill_content:
            self.documentation = skill_content
            display_content = skill_content[:100].replace('\n', ' ').replace('\r', '')
            print(f'   Successfully loaded content for {self.name} (first 100 chars): {display_content}...')
            primary_skill_loaded = True
        else:
            print(f'   Failed to load documentation for primary skill: {self.name}')
            return False
        sub_skills_load_successful = True
        if hasattr(self, 'next_detected_skill_to_load') and self.next_detected_skill_to_load:
            print(f'Attempting to load {len(self.next_detected_skill_to_load)} detected sub-skills:')
            for skill_slug in self.next_detected_skill_to_load:
                sub_skill_doc = load_skill(skills_base_path, skill_slug)
                if sub_skill_doc:
                    self.loaded_sub_skills_docs[skill_slug] = sub_skill_doc
                    display_content = sub_skill_doc[:100].replace('\n', ' ').replace('\r', '')
                    print(f' - Successfully loaded documentation for sub-skill: {skill_slug} (first 100 chars): {display_content}...')
                else:
                    print(f' - Failed to load documentation for sub-skill: {skill_slug}')
                    sub_skills_load_successful = False
        else:
            print('No next_detected_skill_to_load attribute found or it is empty.')
        return primary_skill_loaded and sub_skills_load_successful

    def execute(self, *args, **kwargs):
        pass
