import json
import base64
import uuid
import webbrowser
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool
from src.config.env import OPENAI_API_KEY

# --- Create memory ---
memory = MemorySaver()

# --- Define visualization tool ---
@tool
def mermaid_visualizer(diagram_code: str) -> str:
    """
    Visualizes a Mermaid diagram by providing the code and rendering instructions.
    Returns the Mermaid code and instructions for viewing.
    """
    return f"""
    Mermaid Diagram Generated:
    ```mermaid
    {diagram_code}
    ```
    To view this diagram:
    1. Copy the entire code block above
    2. Paste it into a Mermaid live editor like https://mermaid.live
    3. Or use Mermaid plugins in VS Code, Notion, or other supported platforms
    """

# --- Create diagram generator agent ---
# --- Create diagram generator agent ---
def get_diagram_generator_agent(model):
    return create_react_agent(
        model=model,
        tools=[mermaid_visualizer],
        prompt="""
You are DiagramGenerator, an expert in creating visual diagrams using Mermaid syntax.
Your task is to take a product summary or JSON description and generate a Mermaid diagram that visualizes the product's architecture, components, or workflow.
Follow these steps:
1. Analyze the input product summary/JSON to identify key components and relationships
2. Generate appropriate Mermaid code (flowchart, sequence diagram, class diagram, etc.)
3. Use the mermaid_visualizer tool to display the diagram
4. Provide an explanation of what the diagram represents
5. Ask for feedback and offer to make improvements
Your response must be a valid JSON object with this structure:
{
  "done": false,
  "diagram": "Mermaid code here",
  "explanation": "Explanation of the diagram",
  "feedback_question": "What would you like to improve in this diagram?"
}
OR when final version is ready:
{
  "done": true,
  "diagram": "Final Mermaid code",
  "explanation": "Final explanation of the diagram"
}
Important:
- Respond with ONLY the JSON object, no other text
- Ensure JSON is valid and properly formatted
- Always use the mermaid_visualizer tool after generating diagram code
- For complex products, start with a high-level diagram before adding details
- Set "done" to true only when user confirms satisfaction with the diagram
""",
        checkpointer=memory,
        name="DiagramGenerator",
    )

# Backward compatibility
try:
    # We can't easily import default_model here without circular imports potentially, 
    # but let's try or just set to None.
    # Actually, we can import it inside the function if needed.
    diagram_generator = None 
except Exception:
    diagram_generator = None

def generate_mermaid_link(summary: str, open_in_browser: bool = True, model=None) -> str:
    """
    Generate a Mermaid diagram link from a product summary.

    Args:
        summary: Product summary as text or JSON string
        open_in_browser: Whether to automatically open the diagram in a browser
        model: Optional Chat model instance. If None, uses default.

    Returns:
        URL to the generated Mermaid diagram
    """
    if model is None:
        from src.config.model_config import get_model as get_default_model
        model = get_default_model(agent_type="diagram")
        if model is None:
             raise ValueError("No model provided and default model is not available.")

    agent = get_diagram_generator_agent(model)

    # Create a unique thread ID for this session
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # Invoke the diagram generator with the summary
    response = agent.invoke(
        {"messages": [("human", summary)]},
        config=config
    )

    # Process response to extract diagram code
    try:
        # Get the last message content
        last_message = response['messages'][-1]
        # Try to parse as JSON
        result = json.loads(last_message.content)
        mermaid_code = result.get('diagram', '')

        if not mermaid_code:
            raise ValueError("No diagram code found in response")

        # Encode the Mermaid code for URL
        graphbytes = mermaid_code.encode("utf-8")
        base64_bytes = base64.b64encode(graphbytes)
        base64_string = base64_bytes.decode("ascii")

        # Create the URL that generates the image
        url = "https://mermaid.ink/img/" + base64_string

        # Optionally open in browser
        if open_in_browser:
            print("▶️  Opening diagram in your web browser...")
            webbrowser.open(url)
            print("✅ Done!")

        # Print explanation if available
        explanation = result.get('explanation', '')
        if explanation:
            print("\nDiagram Explanation:")
            print(explanation)

        # Print feedback question if not done
        if not result.get('done', False):
            feedback_question = result.get('feedback_question', '')
            if feedback_question:
                print("\nFeedback Question:")
                print(feedback_question)

        return url

    except json.JSONDecodeError:
        # Handle case where response isn't JSON
        print("Response wasn't in JSON format. Raw content:")
        print(last_message.content)
        raise ValueError("Failed to parse diagram generator response")
    except Exception as e:
        print(f"Error generating diagram: {str(e)}")
        raise

# Example usage:
if __name__ == "__main__":
    # Example with text summary
    text_summary = "A fitness tracking app with user profiles, workout logging, and progress charts"
    print("Generating diagram from text summary...")
    diagram_url = generate_mermaid_link(text_summary)
    print(f"Diagram URL: {diagram_url}")

    # Example with JSON
    product_json = """
    {
      "name": "E-commerce Platform",
      "components": ["User Auth", "Product Catalog", "Shopping Cart", "Payment Gateway"],
      "flow": "User browses products → Adds to cart → Checks out → Pays"
    }
    """
    print("\nGenerating diagram from JSON...")
    diagram_url = generate_mermaid_link(product_json)
    print(f"Diagram URL: {diagram_url}")
