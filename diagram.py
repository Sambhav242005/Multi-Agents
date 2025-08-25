# diagramAgent.py - Updated implementation

import json
import base64
import uuid
import webbrowser
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool
from env import GROQ_API_KEY

# --- Initialize model ---
model = ChatGroq(model="openai/gpt-oss-120b", api_key=GROQ_API_KEY)

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
diagram_generator = create_react_agent(
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

Important:
- Always use the mermaid_visualizer tool after generating the diagram code
- Do not attempt to use any other tools
- Do not include any tool calls in your JSON response
- Your response must be a valid JSON object with this structure:
{
  "done": true,
  "diagram": "Mermaid code here",
  "explanation": "Explanation of the diagram"
}
- Respond with ONLY the JSON object, no other text
- Ensure JSON is valid and properly formatted
""",
    checkpointer=memory,
    name="DiagramGenerator",
)

def generate_mermaid_link(summary: str, open_in_browser: bool = False) -> str:
    """
    Generate a Mermaid diagram link from a product summary.
    Args:
        summary: Product summary as text or JSON string
        open_in_browser: Whether to automatically open the diagram in a browser
    Returns:
        URL to the generated Mermaid diagram
    """
    # Create a unique thread ID for this session
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # Invoke the diagram generator with the summary
    response = diagram_generator.invoke(
        {"messages": [("human", summary)]},
        config=config
    )

    # Process response to extract diagram code
    try:
        # Get the last message content
        last_message = response['messages'][-1]
        content = last_message.content

        # Try to parse as JSON
        try:
            result = json.loads(content)
            mermaid_code = result.get('diagram', '')
            if not mermaid_code:
                raise ValueError("No diagram code found in response")
        except json.JSONDecodeError:
            # If the response isn't JSON, try to extract the diagram code directly
            print("Response wasn't in JSON format. Attempting to extract diagram code...")
            # Look for mermaid code block
            import re
            mermaid_match = re.search(r'```mermaid\n(.*?)\n```', content, re.DOTALL)
            if mermaid_match:
                mermaid_code = mermaid_match.group(1)
            else:
                raise ValueError("Could not extract diagram code from response")

        # Encode the Mermaid code for URL
        graphbytes = mermaid_code.encode("ascii")
        base64_bytes = base64.b64encode(graphbytes)
        base64_string = base64_bytes.decode("ascii")

        # Create the URL that generates the image
        url = "https://mermaid.ink/img/" + base64_string

        # # Optionally open in browser
        # if open_in_browser:
        #     print("▶️  Opening diagram in your web browser...")
        #     webbrowser.open(url)
        #     print("✅ Done!")

        # Print explanation if available
        if 'result' in locals() and 'explanation' in result:
            explanation = result.get('explanation', '')
            if explanation:
                print("\nDiagram Explanation:")
                print(explanation)

        return url
    except Exception as e:
        print(f"Error generating diagram: {str(e)}")
        print("Raw response content:")
        print(content if 'content' in locals() else "No content available")
        raise
