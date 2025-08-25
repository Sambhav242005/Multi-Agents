from typing import List
from pydantic import BaseModel

class ProductReqFeature(BaseModel):
    name: str
    reason: str
    goal_oriented: float
    development_time: str
    cost_estimate: float

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
