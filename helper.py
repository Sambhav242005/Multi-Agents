from typing import Optional
import json
import re
from pydantic import BaseModel

def process_agent_response(response_content: str, response_model: BaseModel) -> Optional[BaseModel]:
    """Parse and validate the agent response as the given model"""
    try:
        # Try to extract JSON from the response
        json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            response_dict = json.loads(json_str)
            return response_model(**response_dict)
    except Exception as e:
        print(f"Error processing response: {e}")
    return None

def get_user_input(question: str) -> str:
    """Prompt user for input and return their response"""
    print(f"\n[USER INPUT NEEDED]")
    print(f"Question: {question}")
    user_answer = input("Your answer: ")
    return user_answer
