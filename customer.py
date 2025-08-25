import os
import json
from typing import List, Dict, Any
from pydantic import BaseModel, Field

from langgraph.prebuilt import create_react_agent
from langchain_groq import ChatGroq
from langchain.tools import Tool
from langchain_community.tools import DuckDuckGoSearchRun


# --- Setup ---
try:
    from env import GROQ_API_KEY
except ImportError:
    GROQ_API_KEY = None


# --- Schema ---
class FeatureDetail(BaseModel):
    """Details for a specific product feature."""
    reason: str = Field(description="Reasoning behind the feature's importance based on market feedback.")
    requirement: float = Field(description="A score from 0.0 to 1.0 indicating the feature's necessity.")

class OnlineResource(BaseModel):
    """Represents an online resource used for research."""
    url: str = Field(description="The URL of the resource.")
    resource_used: str = Field(description="Brief description of what information was extracted from the resource.")

class GraphData(BaseModel):
    """Data structure for generating a graph."""
    type: str = Field(description="Type of graph (e.g., 'bar_chart', 'pie_chart', 'line_graph').")
    data_in_table: List[Dict[str, Any]] = Field(description="Data for the graph in a tabular format (a list of dictionaries).")

class MarketAnalysisReport(BaseModel):
    """The final structure for the market analysis report."""
    target: List[str] = Field(description="The target market audience or customer segments.")
    feedback: str = Field(description="A summary of general customer feedback from online sources like reviews and forums.")
    rating: str = Field(description="An overall market rating or sentiment score (e.g., 'Positive', '7.5/10').")
    features: List[Dict[str, FeatureDetail]] = Field(description="A list of key product features. Each item is a dictionary with the feature name as the key.")
    online_search: List[OnlineResource] = Field(description="List of online resources used for the analysis.")
    graph: GraphData = Field(description="A graph representing a key market trend, competitor analysis, or feature comparison.")


# --- Tools ---
search = DuckDuckGoSearchRun()
tools = [
    Tool(
        name="DuckDuckGo_Search",
        func=search.run,
        description="Search the web for market trends, customer reviews, competitor analysis, and product features. Use targeted queries and include sources in the final JSON.",
    )
]


# --- Prompt ---
market_analyst_prompt = """
You are MarketAnalyst, an expert in performing structured market research.

Your task is to analyze the market for a given product or domain.
You must research the target audience, gather customer feedback, identify key product features, and present at least one data-driven graph for trends or competitor comparison.

Your response must be a single valid JSON object that strictly follows this schema:

{
  "target": ["List of target market segments"],
  "feedback": "Summary of customer feedback and sentiment",
  "rating": "Overall market sentiment or rating (e.g., 'Positive', '7.5/10')",
  "features": [
    {
      "Feature Name": {
        "reason": "Why this feature is important (based on market feedback)",
        "requirement": 0.85
      }
    }
  ],
  "online_search": [
    {
      "url": "https://example.com",
      "resource_used": "Short description of information taken"
    }
  ],
  "graph": {
    "type": "bar_chart | pie_chart | line_graph",
    "data_in_table": [
      {"label": "Competitor A", "value": 45},
      {"label": "Competitor B", "value": 30}
    ]
  }
}

Important:
- Respond with ONLY the JSON object, no extra text or explanation.
- Ensure the JSON is valid and properly formatted.
- Always include at least 3 features, 2 online resources, and one graph.
- The `requirement` score for features must be between 0.0 and 1.0.
- The `graph.data_in_table` must always be a list of dictionaries with numeric values.
- If data is missing, make a reasonable assumption (never leave fields empty).
"""


# --- LLM + Agent ---
model = ChatGroq(api_key=GROQ_API_KEY, model="openai/gpt-oss-120b", temperature=0.1)
agent = create_react_agent(model=model, tools=tools, prompt=market_analyst_prompt)


# --- Customer Function ---
def customer(query: str) -> str:
    """Run the market analysis and return JSON string."""
    user_msg = f"Analyze the market for: {query}"
    result = agent.invoke({"messages": [("user", user_msg)]})

    # Get the last model message
    messages = result.get("messages", [])
    if not messages:
        raise RuntimeError("Agent returned no messages.")

    output_text = messages[-1].content

    # Validate against JSON
    try:
        parsed = json.loads(output_text)
        # optional: validate with Pydantic
        MarketAnalysisReport.parse_obj(parsed)
        return json.dumps(parsed, indent=2)
    except Exception as e:
        raise ValueError(f"Model did not return valid JSON. Error: {e}\n\nRaw Output:\n{output_text}")


# --- Run ---
if __name__ == "__main__":
    if not GROQ_API_KEY:
        print("❌ Error: GROQ_API_KEY not found. Please create an 'env.py' file with your API key.")
    else:
        print("\n--- Final Market Analysis Report ---")
        print(customer("AI-powered fitness apps"))
