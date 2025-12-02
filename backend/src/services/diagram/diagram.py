import json
import base64
import uuid
import re
from typing import Optional, Dict, Any
from langchain_core.messages import HumanMessage
from src.config.model_config import get_model
import src.utils.toon as toon

def validate_mermaid_syntax(mermaid_code: str) -> bool:
    """
    Basic validation of Mermaid syntax.
    Checks for common diagram types and basic structure.
    """
    if not mermaid_code or len(mermaid_code.strip()) < 10:
        return False
    
    # Check if it starts with a valid diagram type
    valid_starts = [
        'graph', 'flowchart', 'sequenceDiagram', 'classDiagram',
        'stateDiagram', 'erDiagram', 'gantt', 'pie', 'gitGraph'
    ]
    
    first_line = mermaid_code.strip().split('\n')[0].strip()
    return any(first_line.startswith(start) for start in valid_starts)

def clean_mermaid_code(code: str) -> str:
    """Clean and format Mermaid code for better readability."""
    # Remove any markdown code blocks if present
    code = re.sub(r'```mermaid\s*\n?', '', code)
    code = re.sub(r'```\s*$', '', code)
    
    # Remove excessive whitespace
    lines = [line.rstrip() for line in code.split('\n')]
    # Remove empty lines at start and end
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    
    return '\n'.join(lines)

def generate_mermaid_direct(summary: str, max_retries: int = 2) -> Optional[str]:
    """
    Generate Mermaid diagram using direct structured prompt with examples.
    This is more reliable than ReAct agents.
    """
    model = get_model()
    
    prompt = f"""You are a Mermaid diagram expert. Generate a clear, well-structured Mermaid flowchart diagram from this project summary.

EXAMPLE 1:
Input: {{"name": "TaskManager", "features": [{{"name": "Create Tasks"}}, {{"name": "Set Reminders"}}, {{"name": "Share Lists"}}]}}
Output:
{{
  "diagram": "flowchart TD\\n    A[TaskManager App] --> B[Create Tasks]\\n    A --> C[Set Reminders]\\n    A --> D[Share Lists]\\n    B --> E[Local Storage]\\n    C --> E\\n    D --> F[Cloud Sync]\\n    E --> F",
  "explanation": "Shows main app connecting to three core features with data flow to storage and cloud"
}}

EXAMPLE 2:
Input: {{"name": "EcommerceApp", "features": [{{"name": "Product Catalog"}}, {{"name": "Shopping Cart"}}, {{"name": "Checkout"}}], "tech_stack": ["React", "Node.js", "MongoDB"]}}
Output:
{{
  "diagram": "flowchart TD\\n    subgraph Frontend\\n        A[React App]\\n        B[Product Catalog]\\n        C[Shopping Cart]\\n        D[Checkout]\\n    end\\n    subgraph Backend\\n        E[Node.js API]\\n        F[MongoDB]\\n    end\\n    A --> B\\n    A --> C\\n    A --> D\\n    B --> E\\n    C --> E\\n    D --> E\\n    E --> F",
  "explanation": "Architecture showing frontend components connected to backend API and database"
}}

Now generate a diagram for this project:

Project Summary:
{summary}

INSTRUCTIONS:
1. Analyze the summary and identify key components, relationships, and workflows
2. Generate a Mermaid flowchart using 'flowchart TD' syntax
3. Use subgraphs to organize related components (Frontend, Backend, Features, etc.)
4. Include clear node labels with meaningful connections
5. Keep it organized and readable with proper spacing
6. Use \\n for new lines in the diagram string
7. Return ONLY valid JSON in this exact format (no markdown, no extra text):

{{
  "diagram": "flowchart TD\\n    ...",
  "explanation": "Brief explanation"
}}

CRITICAL: Return ONLY the JSON object, nothing before or after it."""

    for attempt in range(max_retries):
        try:
            response = model.invoke([HumanMessage(content=prompt)])
            content = response.content
            
            # Try to parse as JSON first
            try:
                result = json.loads(content)
                diagram_code = result.get('diagram', '')
            except json.JSONDecodeError:
                # Try TOON format
                parsed = toon.parse_response(content)
                if parsed and 'diagram' in parsed:
                    diagram_code = parsed['diagram']
                else:
                    # Try to extract from markdown
                    match = re.search(r'```mermaid\s*\n(.*?)\n```', content, re.DOTALL)
                    if match:
                        diagram_code = match.group(1)
                    else:
                        print(f"Attempt {attempt + 1}: Could not parse response")
                        if attempt < max_retries - 1:
                            continue
                        return None
            
            # Clean and validate
            diagram_code = clean_mermaid_code(diagram_code)
            
            if validate_mermaid_syntax(diagram_code):
                return diagram_code
            else:
                print(f"Attempt {attempt + 1}: Invalid Mermaid syntax")
                if attempt < max_retries - 1:
                    continue
                    
        except Exception as e:
            print(f"Attempt {attempt + 1} error: {e}")
            if attempt < max_retries - 1:
                continue
    
    return None

def generate_mermaid_from_toon(toon_data: Dict[str, Any]) -> Optional[str]:
    """
    Convert structured TOON/JSON data into a Mermaid diagram.
    This approach builds the diagram programmatically.
    """
    try:
        diagram_lines = ["flowchart TD"]
        node_id = 0
        
        def add_node(label: str, parent_id: Optional[str] = None) -> str:
            nonlocal node_id
            current_id = f"N{node_id}"
            node_id += 1
            
            # Escape special characters in labels
            safe_label = label.replace('"', '\\"').replace('[', '(').replace(']', ')')
            diagram_lines.append(f"    {current_id}[\"{safe_label}\"]")
            
            if parent_id:
                diagram_lines.append(f"    {parent_id} --> {current_id}")
            
            return current_id
        
        # Start with main project
        if isinstance(toon_data, dict):
            root_label = toon_data.get('name', toon_data.get('product', {}).get('name', 'Project'))
            root_id = add_node(root_label)
            
            # Add features or components
            features = toon_data.get('features', [])
            if features:
                diagram_lines.append(f"    subgraph Features")
                for feature in features[:5]:  # Limit to 5 for clarity
                    if isinstance(feature, dict):
                        feature_name = feature.get('name', 'Feature')
                    else:
                        feature_name = str(feature)
                    add_node(feature_name, root_id)
                diagram_lines.append("    end")
            
            # Add tech stack if present
            tech_stack = toon_data.get('tech_stack', toon_data.get('engineer', {}).get('tech_stack', []))
            if tech_stack:
                diagram_lines.append(f"    subgraph Technology")
                for tech in tech_stack[:5]:
                    add_node(tech, root_id)
                diagram_lines.append("    end")
        
        diagram_code = '\n'.join(diagram_lines)
        
        if validate_mermaid_syntax(diagram_code):
            return diagram_code
        
    except Exception as e:
        print(f"Error in TOON-to-diagram conversion: {e}")
    
    return None

def generate_mermaid_link(summary: str) -> str:
    """
    Generate a Mermaid diagram link from a project summary.
    Uses multiple approaches for reliability.
    
    Args:
        summary: Product summary as text or JSON string
    
    Returns:
        URL to the generated Mermaid diagram
    """
    mermaid_code = None
    
    # Approach 1: Try direct structured generation (most reliable)
    print("Attempting direct generation...")
    mermaid_code = generate_mermaid_direct(summary)
    
    # Approach 2: If direct fails, try TOON conversion
    if not mermaid_code:
        print("Direct generation failed, trying TOON conversion...")
        try:
            # Parse summary as JSON/TOON
            if isinstance(summary, str):
                try:
                    data = json.loads(summary)
                except json.JSONDecodeError:
                    data = toon.parse_response(summary)
            else:
                data = summary
            
            if data:
                mermaid_code = generate_mermaid_from_toon(data)
        except Exception as e:
            print(f"TOON conversion error: {e}")
    
    # If both approaches fail, create a simple fallback
    if not mermaid_code:
        print("Using fallback diagram...")
        mermaid_code = """flowchart TD
    A[Project] --> B[Features]
    A --> C[Components]
    B --> D[Implementation]
    C --> D"""
    
    # Encode the Mermaid code for URL
    try:
        graphbytes = mermaid_code.encode("ascii")
        base64_bytes = base64.b64encode(graphbytes)
        base64_string = base64_bytes.decode("ascii")
        
        # Create the URL that generates the image
        # Using !scale=2 for higher resolution (2x)
        url = "https://mermaid.ink/img/" + base64_string + "?bgColor=white!scale=4"
        
        return url
    except Exception as e:
        print(f"Error encoding diagram: {e}")
        raise ValueError(f"Failed to generate diagram URL: {str(e)}")
