from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from env import GROQ_API_KEY
# --- Initialize model ---
model = ChatGroq(model="openai/gpt-oss-120b", api_key=GROQ_API_KEY)

# --- Create memory ---
memory = MemorySaver()

# --- Create agents ---
clarifier = create_react_agent(
    model=model,
    tools=[],
    prompt="""
You are Clarifier, an expert in gathering product requirements.
Your task is to ask focused questions about product features and business logic.

For each question, you have two options:
1. If you can reasonably infer the answer yourself, provide it in the "answer" field.
2. If you need specific input from the user, leave the "answer" field empty.

IMPORTANT: Only leave the answer empty for 3-5 critical questions that absolutely require user input.
For all other questions, provide reasonable answers yourself.

Your response must be a valid JSON object with this structure:
{
  "done": false,
  "resp": [
    {
      "question": "What is the primary purpose of your app?",
      "answer": "The primary purpose is to help users track their fitness goals."
    }
  ]
}

OR when needing user input:

{
  "done": false,
  "resp": [
    {
      "question": "What specific fitness metrics do you want to track?",
      "answer": ""
    }
  ]
}

Important:
- Respond with ONLY the JSON object, no other text
- Ensure the JSON is valid and properly formatted
- Each round, add at least one new question
- After gathering at least 5 features, set "done" to true
- Only leave answers empty for 3-5 critical questions that require user input
- For all other questions, provide reasonable answers yourself
""",
    checkpointer=memory,
    name="Clarifier",
    # response_format=ClarifierResp
)

product = create_react_agent(
    model=model,
    tools=[],
    prompt="""
You are Product, responsible for confirming requirements and providing feature details.
Based on the conversation history, generate a product description with at least 5 features.

Your response must be a valid JSON object with this structure:
{
  "name": "App Name",
  "description": "A brief description of the app",
  "features": [
    {
      "name": "Feature 1",
      "reason": "Why this feature is needed",
      "goal_oriented": 0.8,
      "development_time": "2 weeks",
      "cost_estimate": 5000.0
    }
  ]
}

Important:
- Respond with ONLY the JSON object, no other text
- Ensure the JSON is valid and properly formatted
- Include at least 5 features based on the conversation
- Each feature must have all required fields filled out
""",
    checkpointer=memory,
    name="Product"
)
