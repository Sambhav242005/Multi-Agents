from typing import Optional
import json
import re
from pydantic import BaseModel

from src.utils import toon
from src.utils.token_tracker import token_tracker

def process_agent_response(response_content: str, response_model: BaseModel, usage_metadata: Optional[dict] = None) -> Optional[BaseModel]:
    """Parse and validate the agent response as the given model"""
    
    # Track usage if provided
    if usage_metadata:
        token_tracker.track_usage(usage_metadata)

    try:
        # Try to extract JSON from the response first
        json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            response_dict = json.loads(json_str)
            return response_model(**response_dict)
    except Exception as e:
        print(f"JSON parsing failed: {e}")

    # If JSON fails, try TOON
    try:
        toon_dict = toon.parse_response(response_content)
        if toon_dict:
            return response_model(**toon_dict)
    except Exception as e:
        print(f"TOON parsing failed: {e}")
        
    return None

def get_user_input(question: str) -> str:
    """Prompt user for input and return their response"""
    print(f"\n[USER INPUT NEEDED]")
    print(f"Question: {question}")
    user_answer = input("Your answer: ")
    return user_answer
