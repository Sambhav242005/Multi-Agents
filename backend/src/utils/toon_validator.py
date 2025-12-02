from typing import Any, Dict, Optional, Tuple, Type
from pydantic import BaseModel, ValidationError
import src.utils.toon as toon

def validate_toon_string(text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Validates if a string is valid TOON.
    
    Args:
        text: The string to validate.
        
    Returns:
        A tuple containing:
        - The parsed dictionary if valid, None otherwise.
        - An error message if invalid, None otherwise.
    """
    try:
        # Try to find TOON block if embedded in markdown
        if "```toon" in text:
            import re
            match = re.search(r"```toon\n(.*?)\n```", text, re.DOTALL)
            if match:
                text = match.group(1)
        
        data = toon.loads(text)
        if not isinstance(data, dict):
             return None, "TOON content must be a dictionary/object"
        return data, None
    except Exception as e:
        return None, f"Invalid TOON format: {str(e)}"

def validate_toon_model(data: Dict[str, Any], model: Type[BaseModel]) -> Tuple[Optional[BaseModel], Optional[str]]:
    """
    Validates if a dictionary matches a Pydantic model (for TOON data).
    
    Args:
        data: The dictionary to validate.
        model: The Pydantic model class.
        
    Returns:
        A tuple containing:
        - The validated model instance if valid, None otherwise.
        - An error message if invalid, None otherwise.
    """
    try:
        instance = model(**data)
        return instance, None
    except ValidationError as e:
        return None, f"Schema validation failed: {str(e)}"
    except Exception as e:
        return None, f"Unexpected error validating model: {str(e)}"
