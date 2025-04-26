import httpx
from actions.api.common.types import (
    AgentCard,
    A2AClientJSONError,
)
import json


class A2ACardResolver:
    """
    A resolver class for retrieving and parsing an agent card from a specified base URL.

    This class is responsible for fetching the agent card JSON from a given URL
    and converting it into an `AgentCard` object. It handles URL formatting and
    raises appropriate errors for HTTP or JSON decoding issues.

    Attributes:
        base_url (str): The base URL from which the agent card is retrieved.
        agent_card_path (str): The relative path to the agent card JSON file.

    Methods:
        get_agent_card() -> AgentCard:
            Fetches and parses the agent card JSON into an `AgentCard` object.
    """
    def __init__(self, base_url, agent_card_path="/.well-known/agent.json"):
        self.base_url = base_url.rstrip("/")
        self.agent_card_path = agent_card_path.lstrip("/")

    def get_agent_card(self) -> AgentCard:
        with httpx.Client() as client:
            response = client.get(self.base_url + "/" + self.agent_card_path)
            response.raise_for_status()
            try:
                return AgentCard(**response.json())
            except json.JSONDecodeError as e:
                raise A2AClientJSONError(str(e)) from e
