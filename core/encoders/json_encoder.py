

import json
from dataclasses import is_dataclass, fields



class JsonEncoder(json.JSONEncoder):
    def default(self, obj):
    # 1. Handle Dataclasses automatically
        if is_dataclass(obj):
         # Create a shallow dict of the fields
            # This avoids the recursive deepcopy that triggers the pickle error
            result = {}
            for f in fields(obj):
                # EXCLUDE the 'client' and other service-related fields
                if f.name in ['client']:
                    continue
                
                value = getattr(obj, f.name)
                result[f.name] = value
            return result
        # 2. Handle "Untouchable" classes by dumping their __dict__
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        # 3. Handle sets
        if isinstance(obj, set):
            return list(obj)
        return super().default(obj)
    
        