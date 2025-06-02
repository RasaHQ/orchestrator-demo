# insurance_agent.py (Corrected Parts Structure)

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator, ValidationError
from typing import Optional, List, Dict, Any, Literal 
from datetime import date, datetime
import asyncio
import json
import re # For parsing the text prompt

ENDPOINT_PREFIX = ""

# --- Data Models ---
# Internal model for structured quote request, after parsing
class InsuranceQuoteRequestData(BaseModel):
    policy_type: str
    residency: str
    primary_birthdate: date
    partner_birthdate: Optional[date] = None

class PolicyQuote(BaseModel):
    policy_name: str
    monthly_cost: float

# --- Pydantic models to match the structure sent by the A2AClient ---

class ServerTextPart(BaseModel):
    text: str
    type: Literal["text"]

# This model represents the wrapper structure for each part in the client's `message.parts` list.
# The client's `a2a.types.Part` serializes with a "root" key.
class ServerPart(BaseModel):
    root: ServerTextPart # Assuming the client primarily sends TextPart within the root.
                         # If other part types (FilePart, etc.) were possible and needed handling,
                         # `root` would be a Union: `Union[ServerTextPart, ServerFilePart, ...]`
                         # with a discriminator based on the `type` field within those part models.

class ServerMessage(BaseModel):
    role: str
    parts: List[ServerPart] # Changed from List[ServerTextPart] to List[ServerPart]
    messageId: str
    contextId: Optional[str] = None
    taskId: Optional[str] = None

class ServerMessageSendConfiguration(BaseModel):
    acceptedOutputModes: Optional[List[str]] = None

class ServerMessageSendParams(BaseModel):
    id: str 
    message: ServerMessage
    configuration: Optional[ServerMessageSendConfiguration] = None

    class Config:
        extra = "ignore"

# --- Agent Router ---
insurance_router = APIRouter()

# --- Agent Card (Unchanged) ---
HOST = "localhost"
PORT = 10003
INSURANCE_AGENT_CARD = {
    "name": "Insurance Quote Agent",
    "description": "This agent provides health insurance quotes by calling a dedicated API, with streaming updates.",
    "url": f"http://{HOST}:{PORT}{ENDPOINT_PREFIX}",
    "version": "1.0.0",
    "capabilities": {"streaming": True, "pushNotifications": False, "stateTransitionHistory": False},
    "defaultInputModes": ["text", "text/plain"],
    "defaultOutputModes": ["text", "text/plain", "text/event-stream"],
    "skills": [{
        "id": "get_insurance_quote_stream",
        "name": "Get Insurance Quote (Streaming)",
        "description": "Fetches health insurance quotes for individuals, couples, or families and streams them.",
        "tags": ["insurance", "quotes", "health", "streaming"],
        "examples": [
            "Can you get me a health insurance quote with streaming updates?",
            "I need a quote for a couple, both residents, born 1990-01-01 and 1992-02-02, stream the results."
        ]
    }]
}

# --- Helper Functions ---
def calculate_age(birthdate: date) -> int:
    today = date.today()
    age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    return age

def calculate_arbitrary_price(request_data: InsuranceQuoteRequestData) -> float:
    base_price = 100.0
    if request_data.policy_type == "couple": base_price *= 1.9
    elif request_data.policy_type == "family": base_price *= 2.8
    elif request_data.policy_type == "single parent family": base_price *= 1.7
    if request_data.residency == "international student": base_price *= 1.3
    elif request_data.residency == "international worker": base_price *= 1.5
    primary_age = calculate_age(request_data.primary_birthdate)
    if primary_age > 60: base_price *= 1.8
    elif primary_age > 40: base_price *= 1.4
    elif primary_age < 25: base_price *= 0.9
    if request_data.partner_birthdate:
        partner_age = calculate_age(request_data.partner_birthdate)
        if partner_age > 60: base_price *= 1.2
        elif partner_age > 40: base_price *= 1.1
    return round(base_price, 2)

def parse_insurance_request_from_text(text: str) -> Optional[InsuranceQuoteRequestData]:
    text = text.lower()
    pattern = re.compile(
        r"quote for a (?P<policy_type>individual|couple|family|single parent family)"
        r".*?(?P<residency>resident|international student|international worker)"
        r".*?born (?P<bdate1>\d{4}-\d{2}-\d{2})"
        r"(?:.*?and (?P<bdate2>\d{4}-\d{2}-\d{2}))?",
        re.IGNORECASE
    )
    match = pattern.search(text)

    if not match:
        return None
    data = match.groupdict()
    try:
        policy_type = data['policy_type'].strip()
        residency = data['residency'].strip()
        if "residents" in residency: residency = "resident"
        primary_birthdate = datetime.strptime(data['bdate1'], "%Y-%m-%d").date()
        partner_birthdate = None
        if data.get('bdate2'):
            partner_birthdate = datetime.strptime(data['bdate2'], "%Y-%m-%d").date()
        if policy_type in ["couple", "family"] and not partner_birthdate:
            print(f"Parsing warning: Policy type {policy_type} usually requires a partner birthdate.")
        return InsuranceQuoteRequestData(
            policy_type=policy_type,
            residency=residency,
            primary_birthdate=primary_birthdate,
            partner_birthdate=partner_birthdate,
        )
    except (ValueError, KeyError) as e:
        print(f"Error parsing dates or missing fields from regex match: {e}")
        return None

# --- API Endpoints ---
@insurance_router.get("/.well-known/agent.json", summary="Get Insurance Agent Card", response_model=dict)
async def get_agent_card_insurance():
    return INSURANCE_AGENT_CARD

@insurance_router.post("/", summary="Get Health Insurance Quote (Streaming)")
async def get_insurance_quote_streaming(payload: ServerMessageSendParams): 
    """
    Parses text from the incoming message, fetches health insurance quotes,
    and streams them back using Server-Sent Events (SSE).
    """
    print(payload)
    async def event_generator():
        try:
            if not payload.message or not payload.message.parts or not payload.message.parts:
                error_message = {"error": "Invalid message structure", "details": "Missing message or parts list."}
                yield f"event: error\ndata: {json.dumps(error_message)}\n\n"
                return

            # Access the text from the 'root' of the first part
            # Pydantic validation for ServerMessageSendParams -> ServerMessage -> List[ServerPart] -> ServerPart.root: ServerTextPart
            # should ensure this structure if validation passes.
            first_part_wrapper = payload.message.parts[0]
            
            # Ensure the root of the part is indeed a ServerTextPart (though Pydantic should enforce this if only ServerTextPart is allowed in ServerPart.root)
            if not isinstance(first_part_wrapper.root, ServerTextPart):
                 error_message = {"error": "Invalid message part content", "details": "First message part's root is not a valid text part."}
                 yield f"event: error\ndata: {json.dumps(error_message)}\n\n"
                 return

            user_text = first_part_wrapper.root.text
            
            print(f"Received text for parsing: {user_text}") 
            parsed_request_data = parse_insurance_request_from_text(user_text)

            if not parsed_request_data:
                error_message = {
                    "error": "Parsing failed",
                    "details": "Could not understand the insurance request from the provided text. "
                               "Please use a format like: 'quote for a couple, resident, born YYYY-MM-DD and YYYY-MM-DD'."
                }
                yield f"event: error\ndata: {json.dumps(error_message)}\n\n"
                return

            base_monthly_cost = calculate_arbitrary_price(parsed_request_data)
            policies_data = [
                {"policy_name": "Basic", "monthly_cost": round(base_monthly_cost, 2)},
                {"policy_name": "Bronze", "monthly_cost": round(base_monthly_cost * 1.35, 2)},
                {"policy_name": "Silver", "monthly_cost": round(base_monthly_cost * 1.75, 2)},
                {"policy_name": "Gold", "monthly_cost": round(base_monthly_cost * 2.25, 2)},
            ]
            for policy_data in policies_data:
                yield f"data: {json.dumps(policy_data)}\n\n"
                await asyncio.sleep(0.5)
            yield "event: end\ndata: Stream finished\n\n"

        except ValidationError as ve: 
            print(f"Pydantic ValidationError during processing: {ve.errors(include_url=False, include_input=False)}")
            error_message = {"error": "Invalid request payload structure during processing", "details": ve.errors(include_url=False, include_input=False)}
            yield f"event: error\ndata: {json.dumps(error_message)}\n\n"
        except Exception as e:
            print(f"Error in insurance event_generator: {type(e).__name__} - {e}") 
            error_message = {"error": "An unexpected error occurred during quote streaming", "details": "Internal server error"}
            yield f"event: error\ndata: {json.dumps(error_message)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
