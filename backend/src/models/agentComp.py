from typing import List, Dict, Any
from pydantic import BaseModel, Field

class ProductReqFeature(BaseModel):
    name: str
    reason: str
    goal_oriented: Any
    development_time: str
    cost_estimate: Any

class ProductResp(BaseModel):
    name: str
    description: str
    features: List[ProductReqFeature]

class ClarifierReq(BaseModel):
    question: str
    answer: str = ""  # Empty string means waiting for user input

class ClarifierResp(BaseModel):
    done: bool
    resp: List[ClarifierReq]

# --- Engineer Agent Models ---
class EngineerFeature(BaseModel):
    feature: str
    feasible: float
    reason: str
    implementation_time: str
    dependencies: List[str] = []
    conflicts: List[str] = []
    impact_score: float

class EngineerAnalysis(BaseModel):
    done: bool
    summary: str
    recommendations: List[str]
    features: List[EngineerFeature]

# --- Risk Agent Models ---
class RiskFeature(BaseModel):
    feature: str
    law_interaction: str
    is_potential_risk: bool
    potential_risk: str
    border_line_thing: str
    gdpr_compliance: str
    data_retention: str
    user_consent: str
    risk_level: str
    mitigation: str

class RiskAssessment(BaseModel):
    done: bool
    summary: str
    recommendations: List[str]
    features: List[RiskFeature]

# --- Customer Agent Models ---
class CustomerFeature(BaseModel):
    name: str = Field(alias="Feature Name")
    reason: str
    requirement: float

class OnlineResource(BaseModel):
    url: str
    resource_used: str

class GraphData(BaseModel):
    type: str
    data_in_table: List[Dict[str, Any]]

class CustomerAnalysis(BaseModel):
    target: List[str]
    feedback: str
    rating: str
    features: List[CustomerFeature]
    online_search: List[OnlineResource]
    graph: GraphData

# --- Summarizer Agent Models ---
class SummarizerOutput(BaseModel):
    summary: str

