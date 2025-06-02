# reimbursement_agent.py (Corrected)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional # Added Optional
from datetime import datetime # Moved import for clarity and to ensure it's available

# --- Pydantic Models for Agent Card Structure ---

class AgentSkill(BaseModel):
    id: str
    name: str
    description: str
    tags: List[str]
    examples: List[str]

class AgentCapabilities(BaseModel):
    streaming: bool
    pushNotifications: bool = False 
    stateTransitionHistory: bool = False

class AgentCard(BaseModel):
    name: str
    description: str
    url: str
    version: str
    defaultInputModes: List[str]
    defaultOutputModes: List[str]
    capabilities: AgentCapabilities
    skills: List[AgentSkill]

# --- Request Model for Reimbursement ---

class ReimbursementRequest(BaseModel):
    amount: float = Field(..., gt=0, description="The amount to be reimbursed, must be greater than 0.")
    purpose: str = Field(..., min_length=1, description="The purpose of the reimbursement.")

class ReimbursementResponse(BaseModel):
    status: str
    message: str
    reimbursement_id: Optional[str] = None # Example of adding an ID

# --- Agent Router ---
reimbursement_router = APIRouter()

# --- Agent Card Definition ---
HOST = "localhost"
PORT = 10003

REIMBURSEMENT_SKILL = AgentSkill(
    id='process_reimbursement',
    name='Process Reimbursement Tool',
    description='Helps with the reimbursement process for users given the amount and purpose of the reimbursement.',
    tags=['reimbursement', 'expense', 'finance'],
    examples=[
        'Can you reimburse me $20 for my lunch with the clients?',
        'I need to get $50 back for office supplies.'
    ],
)

REIMBURSEMENT_AGENT_CARD = AgentCard(
    name='Reimbursement Agent',
    description='This agent handles the reimbursement process for the employees given the amount and purpose of the reimbursement.',
    url=f'http://{HOST}:{PORT}/reimbursement/', 
    version='1.0.0',
    defaultInputModes=['text', 'text/plain'],
    defaultOutputModes=['text', 'text/plain'],
    capabilities=AgentCapabilities(streaming=True), 
    skills=[REIMBURSEMENT_SKILL],
)

# --- API Endpoints ---

@reimbursement_router.get("/", summary="Get Reimbursement Agent Card", response_model=AgentCard)
async def get_agent_card_reimbursement():
    """
    Provides the agent card for the Expense Reimbursement Agent.
    """
    return REIMBURSEMENT_AGENT_CARD

@reimbursement_router.post("/process_reimbursement", summary="Process an Expense Reimbursement", response_model=ReimbursementResponse)
async def process_reimbursement(request: ReimbursementRequest):
    """
    Processes an expense reimbursement request.
    Given an amount and purpose, this endpoint will simulate the reimbursement process.
    """
    try:
        reimbursement_id = f"REIMB-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}" 
        
        print(f"Processing reimbursement for ${request.amount} for '{request.purpose}'. ID: {reimbursement_id}")

        return ReimbursementResponse(
            status="success",
            message=f"Reimbursement request for ${request.amount} for '{request.purpose}' has been successfully submitted. Your Reimbursement ID is {reimbursement_id}.",
            reimbursement_id=reimbursement_id
        )
    except ValueError as e: 
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error in process_reimbursement: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred during reimbursement processing.")
