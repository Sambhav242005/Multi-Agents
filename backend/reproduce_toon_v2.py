from src.utils.toon import loads
import json

test_cases = [
    """
analysis:
  tech_stack:
    frontend:
      - React
      - TypeScript
    """,
    """
analysis:
  tech_stack:
    frontend: []
    """,
    """
analysis:
  tech_stack:
    frontend:
      - Item 1
    backend:
      - Item 2
    """,
    """
analysis:
  tech_stack:
    frontend:
      - Item 1
      - Item 2
  technical_challenges:
    title | severity
    Sync | High
    """
]

for i, tc in enumerate(test_cases):
    print(f"--- Test Case {i+1} ---")
    try:
        data = loads(tc)
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error: {e}")
