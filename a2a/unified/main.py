# main.py (Paths Updated)

from fastapi import FastAPI
import uvicorn

# Import routers and agent cards from the agent modules
from insurance_agent import insurance_router, INSURANCE_AGENT_CARD
from reimbursement_agent import reimbursement_router, REIMBURSEMENT_AGENT_CARD

# Initialize the FastAPI application
app = FastAPI(
    title="A2A Multi-Agent Server",
    description="This server hosts multiple agents for an Agent-to-Agent (A2A) communication setup with updated paths.",
    version="1.0.1" # Incremented version
)

# Include the routers for each agent with updated prefixes
app.include_router(insurance_router, prefix="", tags=["Health Insurance Quote Agent"])
app.include_router(reimbursement_router, prefix="/reimbursement", tags=["Expense Reimbursement Agent"])


@app.get("/agents", summary="List All Available Agent Cards", response_model=dict)
async def list_all_agents():
    """
    Provides a list of all agent cards available on this server.
    The URLs in the agent cards now point to their new locations.
    """
    return {
        "available_agents": [
            INSURANCE_AGENT_CARD, 
            REIMBURSEMENT_AGENT_CARD.dict() 
        ]
    }

if __name__ == "__main__":
    print("Starting A2A Multi-Agent Server on http://localhost:10003")
    print("Access OpenAPI docs at http://localhost:10003/docs")
    print("List all agents at http://localhost:10003/agents")
    print(f"Insurance Agent Card at: {INSURANCE_AGENT_CARD['url']}/.well-known/agent.json")
    print(f"Insurance Agent at: {INSURANCE_AGENT_CARD['url']}")
    print(f"Reimbursement Agent Card at: {REIMBURSEMENT_AGENT_CARD.url}") # Accessing Pydantic model field
    print(f"Reimbursement Agent Streaming Task at: http://localhost:10003/reimbursement/tasks/sendSubscribe")
    uvicorn.run(app, host="0.0.0.0", port=10003)

