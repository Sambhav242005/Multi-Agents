
import sys
import os
import json
import requests
from src.services.diagram.diagram import generate_mermaid_link

# Add project root to path
sys.path.append(os.getcwd())

def test_diagram_generation():
    summary_data = {
        "name": "TestProject",
        "features": [
            {"name": "Login", "description": "User authentication"},
            {"name": "Dashboard", "description": "Main user view"},
            {"name": "Settings", "description": "User preferences"}
        ],
        "tech_stack": ["React", "Python", "PostgreSQL"]
    }
    
    summary_json = json.dumps(summary_data)
    
    print("Testing diagram generation...")
    try:
        url = generate_mermaid_link(summary_json)
        print(f"\nGenerated URL Length: {len(url)}")
        print(f"Generated URL (first 100 chars): {url[:100]}...")
        
        # Verify it's a mermaid.ink URL
        if url and url.startswith("https://mermaid.ink/img/"):
            print("SUCCESS: URL format is correct")
            
            # Check if URL is reachable
            try:
                response = requests.get(url)
                print(f"URL Status Code: {response.status_code}")
                if response.status_code == 200:
                    print("SUCCESS: Image is reachable")
                else:
                    print("FAILURE: Image is not reachable")
            except Exception as e:
                print(f"FAILURE: Could not fetch image: {e}")
                
        else:
            print("FAILURE: URL format is incorrect")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_diagram_generation()
