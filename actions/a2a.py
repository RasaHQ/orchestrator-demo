import yaml
import uuid
from typing import Dict, Optional
import logging

from actions.api.common.types import AgentCard, Task, TaskSendParams, TaskState, Message
from actions.api.common.client import A2AClient, A2ACardResolver
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from actions.api.common.types import TextPart

logger = logging.getLogger(__name__)

class RemoteAgentConnections:
    """Handles connections and communication with a single remote agent"""
    
    def __init__(self, agent_card: AgentCard):
        self.agent_card = agent_card
        self.client = A2AClient(agent_card)

    async def send_task(self, request: TaskSendParams) -> Task:
        """Send task to remote agent and return completed response"""
        # Non-streaming implementation
        response = await self.client.send_task(request.model_dump())
        return response.result
        

class ActionA2A(Action):
    """Custom action for A2A client functionality"""
    
    def __init__(self):
        # super().__init__(name)
        self.agents: Dict[str, RemoteAgentConnections] = {}
        self.load_agents()

    def name(self) -> str:
        return "action_a2a"

    def load_agents(self):
        """Load agent configurations from a2a.yml"""
        try:
            with open("a2a.yml", "r") as file:
                config = yaml.safe_load(file)["remote_agents"]
                for agent in config:
                    logger.info(f"Loading agent: {agent['name']}, {agent['url']}")
                    cardresolver = A2ACardResolver(agent["url"])
                    agent_card = cardresolver.get_agent_card()
                    self.agents[agent["name"]] = RemoteAgentConnections(
                        cardresolver.get_agent_card()
                    )
                    logger.info(f"Loaded agent: {agent_card.name}, vers: {agent_card.version}")
        except Exception as e:
            logger.error(f"Failed to load A2A agent {agent['name']}: {str(e)}")

    async def run(self, dispatcher, tracker, domain):
        """Execute A2A client action"""
        
        agent_name = tracker.get_slot("a2a_agent_name")
        if not agent_name or agent_name not in self.agents:
            logger.error(f"Invalid A2A agent specified: {agent_name}")
            dispatcher.utter_message(text=f"Invalid A2A agent specified: {agent_name}. Try again later")
            return [SlotSet("a2a_status", "error")]
            
        current_message = tracker.latest_message
        session_id = tracker.sender_id
        
        request = TaskSendParams(
            id=str(uuid.uuid4()),
            sessionId=session_id,
            message=Message(
                role="user",
                parts=[TextPart(text=current_message["text"])],
                metadata=current_message["metadata"]
            )
        )

        try:
            connection = self.agents[agent_name]
            task = await connection.send_task(request)
            
            # Process response
            status = task.status.state
            if status == TaskState.COMPLETED:
                self._send_response(dispatcher, task)
                return [SlotSet("a2a_status", "completed")]
            elif status == TaskState.INPUT_REQUIRED:
                dispatcher.utter_message("Please provide additional information")
                return [SlotSet("a2a_status", "input-required")]
            else:
                dispatcher.utter_message("Request encountered an unexpected error")
                return [SlotSet("a2a_status", "error")]
                
        except Exception as e:
            dispatcher.utter_message(text=f"Agent call failed: {str(e)}")
            return [SlotSet("a2a_status", "error")]

        return []

    def _send_response(self, dispatcher, task):
        """Send back response parts as utterances"""
        # Send message parts
        if task.status.message:
            for part in task.status.message.parts:
                if part.type == "text":
                    dispatcher.utter_message(part.text)
        
        # Send artifact text parts
        for artifact in task.artifacts:
            for part in artifact.parts:
                if part.type == "text":
                    dispatcher.utter_message(part.text)