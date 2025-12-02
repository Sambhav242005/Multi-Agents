from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import uuid
from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage, AIMessage
from src.agents.agent import get_clarifier_agent, get_product_agent, get_classifier_agent
from src.models.agentComp import ClarifierResp, ProductResp, EngineerAnalysis, RiskAssessment, CustomerAnalysis, SummarizerOutput
from src.agents.engineer import get_engineer_agent
from src.agents.customer import get_customer_agent
from src.agents.risk import get_risk_agent
from src.agents.summarizer import get_summarizer_agent
import src.utils.toon as toon
from src.config.model_config import get_model

app = FastAPI(title="Product Conversation API")

# Pydantic models for request/response
class ClarifierRequest(BaseModel):
    messages: List[Dict[str, str]]
    model_provider: Optional[str] = "openai"

class ClassifierRequest(BaseModel):
    idea: str
    model_provider: Optional[str] = "openai"

class ProductRequest(BaseModel):
    requirements: str
    model_provider: Optional[str] = "openai"

class CustomerRequest(BaseModel):
    product_data: Dict[str, Any]
    model_provider: Optional[str] = "openai"

class EngineerRequest(BaseModel):
    customer_data: Dict[str, Any]
    model_provider: Optional[str] = "openai"

class RiskRequest(BaseModel):
    engineer_data: Dict[str, Any]
    model_provider: Optional[str] = "openai"

class SummaryRequest(BaseModel):
    final_data: Dict[str, Any]
    model_provider: Optional[str] = "openai"

class DiagramRequest(BaseModel):
    project_summary: Dict[str, Any]  # Can be product data or full project summary

# Helper function
def safe_parse(response: str) -> Dict[str, Any]:
    """Safely parse response string as TOON or JSON"""
    try:
        data = toon.parse_response(response)
        if not data:
            data = json.loads(response)
        return data
    except Exception:
        # If parsing fails, return the raw text wrapped in a dict
        return {"raw_content": response, "error": "Failed to parse response"}

def process_agent_response(response: str, response_model):
    """Process agent response and parse into the given model using JSON"""
    try:
        # Parse TOON
        if isinstance(response, str):
            data = safe_parse(response)
        else:
            data = response
        
        return response_model(**data)
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return None

# API Endpoints
@app.get("/")
async def health_check():
    return {"status": "healthy"}

@app.post("/clarify")
async def clarify(request: ClarifierRequest):
    """Run Clarifier agent step"""
    try:
        model = get_model(provider=request.model_provider)
        clarifier = get_clarifier_agent(model)
        
        # Convert dict messages to LangChain messages
        lc_messages = []
        for msg in request.messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_messages.append(AIMessage(content=msg["content"]))
        
        # If no messages, start with default prompt (though client should handle this)
        if not lc_messages:
             return {"error": "No messages provided"}

        config = {"configurable": {"thread_id": str(uuid.uuid4())}} # Dummy thread ID for LangGraph
        clarifier_result = clarifier.invoke({"messages": lc_messages}, config)
        clarifier_messages = clarifier_result["messages"]
        clarifier_response = clarifier_messages[-1].content
        
        # Parse response
        print(f"DEBUG: Clarifier Raw Response: {clarifier_response}")
        clarifier_obj = process_agent_response(clarifier_response, ClarifierResp)
        print(f"DEBUG: Clarifier Parsed Object: {clarifier_obj}")
        
        response_data = {
            "response": clarifier_response,
            "parsed": clarifier_obj.model_dump() if clarifier_obj else None,
            "done": clarifier_obj.done if clarifier_obj else False
        }
        
        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in clarifier: {str(e)}")

@app.post("/classify")
async def classify(request: ClassifierRequest):
    """Run Classifier agent step"""
    try:
        model = get_model(provider=request.model_provider)
        classifier = get_classifier_agent(model)
        
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        
        classifier_result = classifier.invoke(
            {"messages": [HumanMessage(content=f"Idea: {request.idea}")]},
            config
        )
        classifier_response = classifier_result["messages"][-1].content
        
        # Parse TOON
        classifier_data = safe_parse(classifier_response)
        
        return {
            "classification": classifier_data,
            "raw_response": classifier_response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in classifier: {str(e)}")

from src.services.diagram.diagram import generate_mermaid_link

@app.post("/generate_product")
async def generate_product(request: ProductRequest):
    """Generate product data from requirements"""
    try:
        model = get_model(provider=request.model_provider)
        product_agent = get_product_agent(model)
        
        trigger_message = HumanMessage(content=f"Requirements: {request.requirements}\\n\\nBased on the above requirements, please generate the full product specification.")
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        
        product_result = product_agent.invoke({"messages": [trigger_message]}, config)
        product_response = product_result["messages"][-1].content
        product_obj = process_agent_response(product_response, ProductResp)

        if product_obj:
            # Ensure at least 5 features
            if len(product_obj.features) < 5:
                retry_message = HumanMessage(content="Generate a product response with at least 5 features based on our conversation.")
                product_result = product_agent.invoke({"messages": [trigger_message, AIMessage(content=product_response), retry_message]}, config)
                product_response = product_result["messages"][-1].content
                product_obj = process_agent_response(product_response, ProductResp)

            # Generate diagram
            try:
                diagram_url = generate_mermaid_link(product_obj.model_dump_json())
            except Exception as e:
                print(f"Diagram generation failed: {e}")
                diagram_url = None
            
            return {
                "product_data": product_obj.model_dump() if product_obj else None,
                "diagram_url": diagram_url,
                "raw_response": product_response
            }
        else:
            print(f"Failed to parse product response: {product_response}")
            raise HTTPException(status_code=500, detail=f"Failed to parse product data. Raw: {product_response[:500]}")
    except Exception as e:
        print(f"Exception in generate_product: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating product: {str(e)}")

@app.post("/generate_customer")
async def generate_customer(request: CustomerRequest):
    """Generate customer analysis from product data"""
    try:
        model = get_model(provider=request.model_provider)
        customer_agent = get_customer_agent(model)
        
        product_str = toon.dumps(request.product_data)
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        
        customer_result = customer_agent.invoke(
            {"messages": [HumanMessage(content=product_str)]},
            config
        )
        customer_response = customer_result["messages"][-1].content
        
        # Track tokens
        from src.utils.token_tracker import token_tracker
        usage_metadata = customer_result["messages"][-1].response_metadata.get("token_usage") if hasattr(customer_result["messages"][-1], "response_metadata") else None
        if usage_metadata:
            token_tracker.track_usage(usage_metadata)

        customer_data = safe_parse(customer_response)
        
        return {
            "customer_data": customer_data,
            "raw_response": customer_response
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating customer analysis: {str(e)}")

@app.post("/generate_engineer")
async def generate_engineer(request: EngineerRequest):
    """Generate engineer analysis from customer data"""
    try:
        model = get_model(provider=request.model_provider)
        engineer_agent = get_engineer_agent(model)
        
        customer_str = toon.dumps(request.customer_data)
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        
        engineer_result = engineer_agent.invoke(
            {"messages": [HumanMessage(content=customer_str)]},
            config
        )
        engineer_response = engineer_result["messages"][-1].content
        
        # Track tokens
        from src.utils.token_tracker import token_tracker
        usage_metadata = engineer_result["messages"][-1].response_metadata.get("token_usage") if hasattr(engineer_result["messages"][-1], "response_metadata") else None
        if usage_metadata:
            token_tracker.track_usage(usage_metadata)

        engineer_data = safe_parse(engineer_response)

        # Avoid double wrapping if 'analysis' key already exists
        if isinstance(engineer_data, dict) and "analysis" in engineer_data:
            final_data = engineer_data
        else:
            final_data = {"analysis": engineer_data}

        return {
            "engineer_data": final_data,
            "raw_response": engineer_response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating engineer analysis: {str(e)}")

@app.post("/generate_risk")
async def generate_risk(request: RiskRequest):
    """Generate risk assessment from engineer data"""
    try:
        model = get_model(provider=request.model_provider)
        risk_agent = get_risk_agent(model)
        
        engineer_data = request.engineer_data
        engineer_analysis = engineer_data.get("analysis", engineer_data)
        engineer_str = toon.dumps(engineer_analysis)
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}

        risk_result = risk_agent.invoke(
            {"messages": [HumanMessage(content=engineer_str)]},
            config
        )
        risk_response = risk_result["messages"][-1].content
        
        # Track tokens
        from src.utils.token_tracker import token_tracker
        usage_metadata = risk_result["messages"][-1].response_metadata.get("token_usage") if hasattr(risk_result["messages"][-1], "response_metadata") else None
        if usage_metadata:
            token_tracker.track_usage(usage_metadata)

        risk_data = safe_parse(risk_response)

        return {
            "risk_data": {"assessment": risk_data},
            "raw_response": risk_response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating risk assessment: {str(e)}")

@app.post("/generate_summary")
async def generate_summary(request: SummaryRequest):
    """Generate final summary from all data"""
    try:
        model = get_model(provider=request.model_provider)
        summarizer = get_summarizer_agent(model)
        
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        
        summary_result = summarizer.invoke(
            {"messages": [HumanMessage(content=toon.dumps(request.final_data, indent=2))]},
            config
        )
        summary_response = summary_result["messages"][-1].content
        print(f"DEBUG: Raw Summary Response: {summary_response}")
        
        summary_obj = process_agent_response(summary_response, SummarizerOutput)
        if summary_obj:
            print(f"DEBUG: Parsed Summary Object: {summary_obj}")
            summary = summary_obj.summary
        else:
            print("DEBUG: Failed to parse summary object, falling back to safe_parse")
            summary_data = safe_parse(summary_response)
            summary = summary_data.get("summary", summary_response)
            
        tts_file = "https://example.com/speech.mp3"
        
        return {
            "summary": summary,
            "tts_file": tts_file,
            "raw_response": summary_response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")

@app.post("/generate_diagram")
async def generate_diagram(request: DiagramRequest):
    """Generate a Mermaid diagram from project summary"""
    try:
        diagram_url = generate_mermaid_link(json.dumps(request.project_summary))
        return {
            "diagram_url": diagram_url,
            "status": "success"
        }
    except Exception as e:
        print(f"Diagram generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating diagram: {str(e)}")
