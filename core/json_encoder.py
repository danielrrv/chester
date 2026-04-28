
from abc import ABC, abstractmethod
import json
from dataclasses import is_dataclass, asdict



class JsonEncoder(json.JSONEncoder):
    def default(self, obj):
        # 1. Handle Dataclasses automatically
        if is_dataclass(obj):
            return asdict(obj)
        
        # 2. Handle "Untouchable" classes by dumping their __dict__
        # This works for 90% of standard Python classes
        if hasattr(obj, "__dict__"):
            return obj.__dict__
            
        return super().default(obj)
    
        