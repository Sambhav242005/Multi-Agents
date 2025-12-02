import requests
import json

url = "http://localhost:8000/generate_engineer"
headers = {"Content-Type": "application/json"}
data = {
    "customer_data": {
        "target_audience": ["Fitness enthusiasts", "Busy professionals"],
        "pain_points": ["Lack of time", "Motivation"],
        "customer_personas": [
            {"name": "John", "age": 30, "goals": "Stay fit"}
        ]
    }
}

try:
    print("Sending request to", url)
    response = requests.post(url, headers=headers, json=data)
    print("Status Code:", response.status_code)
    print("Response JSON:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
