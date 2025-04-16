from typing import Any, Dict, List, Text
import logging
import requests
import uuid

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from actions.api.common.types import AgentCard
from actions.api.remote_agent_connection import (
    RemoteAgentConnections,
    TaskUpdateCallback
)
from google.adk.tools.tool_context import ToolContext

from actions.db import add_contact, get_contacts, Contact

logger = logging.getLogger(__name__)


class ReimbursementAgent(Action):

    def name(self) -> str:
        agent_url = "http://localhost:10002"
        self.agent = self._register_agent(agent_url)
        card_resolver = A2ACardResolver(address)
        card = card_resolver.get_agent_card()
        self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
        self.remote_agent_connections[card.name] = remote_connection
        return "action_a2a_reimbursement_agent"

    def _get_agent_card(remote_agent_address: str) -> AgentCard:
        agent_card = requests.get(
            f"http://{remote_agent_address}/.well-known/agent.json"
        )
        return AgentCard(**agent_card.json())

    def _register_agent(self, url):
        agent_data = self._get_agent_card(url)
        if not agent_data.url:
            agent_data.url = url
        self._agents.append(agent_data)
        self._host_agent.register_agent_card(agent_data)
        # Now update the host agent definition
        self._initialize_host()

    async def send_task(self, message: str, tool_context: ToolContext):
        """Sends a task either streaming (if supported) or non-streaming.

        This will send a message to the remote agent named agent_name.

        Args:
        agent_name: The name of the agent to send the task to.
        message: The message to send to the agent for the task.
        tool_context: The tool context this method runs in.

        Yields:
        A dictionary of JSON data.
        """
        state = tool_context.state
        agent_name = self.agent["name"]
        state["agent"] = agent_name
        card = self.cards[agent_name]
        client = self.remote_agent_connections[agent_name]

        if not client:
            raise ValueError(f"Client not available for {agent_name}")
        if "task_id" in state:
            taskId = state["task_id"]
        else:
            taskId = str(uuid.uuid4())
        sessionId = state["session_id"]
        task: Task
        messageId = ""
        metadata = {}
        if "input_message_metadata" in state:
            metadata.update(**state["input_message_metadata"])
            if "message_id" in state["input_message_metadata"]:
                messageId = state["input_message_metadata"]["message_id"]
        if not messageId:
            messageId = str(uuid.uuid4())
        metadata.update(**{"conversation_id": sessionId, "message_id": messageId})
        request: TaskSendParams = TaskSendParams(
            id=taskId,
            sessionId=sessionId,
            message=Message(
                role="user",
                parts=[TextPart(text=message)],
                metadata=metadata,
            ),
            acceptedOutputModes=["text", "text/plain", "image/png"],
            # pushNotification=None,
            metadata={"conversation_id": sessionId},
        )
        task = await client.send_task(request, self.task_callback)
        # Assume completion unless a state returns that isn't complete
        state["session_active"] = task.status.state not in [
            TaskState.COMPLETED,
            TaskState.CANCELED,
            TaskState.FAILED,
            TaskState.UNKNOWN,
        ]
        if task.status.state == TaskState.INPUT_REQUIRED:
            # Force user input back
            tool_context.actions.skip_summarization = True
            tool_context.actions.escalate = True
        elif task.status.state == TaskState.CANCELED:
            # Open question, should we return some info for cancellation instead
            raise ValueError(f"Agent {agent_name} task {task.id} is cancelled")
        elif task.status.state == TaskState.FAILED:
            # Raise error for failure
            raise ValueError(f"Agent {agent_name} task {task.id} failed")
        response = []
        if task.status.message:
            # Assume the information is in the task message.
            response.extend(convert_parts(task.status.message.parts, tool_context))
        if task.artifacts:
            for artifact in task.artifacts:
                response.extend(convert_parts(artifact.parts, tool_context))
        return response

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[str, Any]
    ) -> List[Dict[Text, Any]]:
        email = tracker.get_slot("email")

        logger.debug(f"subscribing email: {email}")

        # TODO: Add the email to the newsletter database

        return []
