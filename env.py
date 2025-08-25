from dotenv import load_dotenv
import os

# load variables from .env file into environment
load_dotenv()

print("Environment variables loaded successfully.")

# access the value
GROQ_API_KEY = os.getenv("API_KEY")
# print(f"{api_key}")
