from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from src.config.model_config import get_model

# --- Create memory ---
memory = MemorySaver()

from src.config.model_limits import get_agent_limit

# --- Create agents ---
def get_clarifier_agent(model, max_questions=None):
    if max_questions is None:
        max_questions = get_agent_limit("clarifier", "max_questions", 5)
    
    max_tokens = get_agent_limit("clarifier", "max_tokens", 1000)
    if max_tokens:
        model = model.bind(max_tokens=max_tokens)
        
    return create_react_agent(
        model=model,
        tools=[],
        prompt=f"""
You are Clarifier, an expert in gathering product requirements.
Your task is to ask focused questions about product features and business logic to the user.

Instructions:
1. Ask 3-5 distinct questions that will help clarify the product idea.
2. Do NOT infer or make up answers. You must ask the user.
3. Leave the "answer" field EMPTY for every question you ask.
4. If the user has provided answers in the chat history, use that context to ask follow-up questions or set "done" to true if you have enough information.

Limit the total number of questions to a maximum of {max_questions}.

Your response must be in TOON (Token-Oriented Object Notation) format:

```toon
done: false
resp:
  question | answer
  What is the target audience? | 
  What are the key features? | 
```

Important:
- Respond with ONLY the TOON data.
- ALWAYS include the header line "question | answer" before the list of questions.
- ALWAYS leave the answer field empty when asking a question.
- Set "done" to true ONLY when you have a clear understanding of the product requirements (usually after 2-3 rounds of Q&A).
""",
        checkpointer=memory,
        name="Clarifier",
    )

def get_product_agent(model, max_features=None):
    if max_features is None:
        max_features = get_agent_limit("product", "max_features", 5)
    
    max_tokens = get_agent_limit("product", "max_tokens", 1500)
    if max_tokens:
        model = model.bind(max_tokens=max_tokens)
        
    return create_react_agent(
        model=model,
        tools=[],
        prompt=f"""
You are Product, responsible for confirming requirements and providing feature details.
Based on the conversation history, generate a product description with at least {max_features} features.

Your response must be in TOON format:

```toon
name: App Name
description: A brief description of the app
features:
  name | reason | goal_oriented | development_time | cost_estimate
  Feature 1 | Why needed | 0.8 | 2 weeks | 5000.0
```

Important:
- Respond with ONLY the TOON data
- ALWAYS include the header line "name | reason | goal_oriented | development_time | cost_estimate" before the list of features.
- Include at least {max_features} features
- Follow the exact indentation and CSV-like structure for lists
""",
        checkpointer=memory,
        name="Product"
    )

def get_classifier_agent(model):
    """
    Creates an agent responsible for classifying user input into a product idea.
    """
    return create_react_agent(
        model=model,
        tools=[],
        prompt="""
You are the Classifier Agent.
Your job is to analyze the user's input and extract the core product idea.

Input: {input}

Instructions:
1. Identify the main product concept or problem being solved.
2. Categorize the domain (e.g., Health & Fitness, Productivity, Social, etc.).
3. Assess the complexity (Low, Medium, High).

Output format:
Your response must be in TOON (Token-Oriented Object Notation) format:

```toon
idea: The core product idea summary
domain: The primary domain
complexity: Low/Medium/High
```
""",
        checkpointer=memory,
        name="Classifier"
    )

# Backward compatibility (uses default model)
try:
    from src.config.model_config import default_model
    if default_model:
        clarifier = get_clarifier_agent(default_model)
        product = get_product_agent(default_model)
    else:
        clarifier = None
        product = None
except Exception:
    clarifier = None
    product = None
