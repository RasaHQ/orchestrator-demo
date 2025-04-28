import yaml
import uuid
from typing import Dict, Optional, Any, Callable
import logging

from actions.api.common.types import AgentCard, Task, TaskSendParams, TaskState, Message, TaskStatusUpdateEvent, TaskStatus, TaskArtifactUpdateEvent
from actions.api.common.client import A2AClient, A2ACardResolver
from actions.api.common.types import TextPart, SendTaskRequest, SendTaskResponse

# from actions.api.a2a.client import A2AClient, A2ACardResolver
# from actions.api.a2a.types import TaskState, Task, AgentCard
# from actions.api.a2a.push_notification_auth import PushNotificationReceiverAuth
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet

logger = logging.getLogger(__name__)

TaskCallbackArg = Task | TaskStatusUpdateEvent | TaskStatusUpdateEvent
TaskUpdateCallback = Callable[[TaskCallbackArg], Task]

class RemoteAgentConnections:
    """Handles connections and communication with a single remote agent"""

    def __init__(self, agent_card: AgentCard):
        self.agent_card = agent_card
        self.client = A2AClient(agent_card)

    async def send_task(
        self,
        request: TaskSendParams,
        task_callback: TaskUpdateCallback | None,
    ) -> Task | None:
        if self.agent_card.capabilities.streaming:
            task = None
            if task_callback:
                task_callback(Task(
                    id=request.id,
                    sessionId=request.sessionId,
                    status=TaskStatus(
                        state=TaskState.SUBMITTED,
                        message=request.message,
                    ),
                    history=[request.message],
                ))
            logger.debug(f"Sending request to remote agent: {request.model_dump()}")
            async for response in self.client.send_task_streaming(request.model_dump()):
                logger.debug(f">>> stream event => {response.result.model_dump_json(exclude_none=True)}")
                merge_metadata(response.result, request)
                # For task status updates, we need to propagate metadata and provide
                # a unique message id.
                if (hasattr(response.result, 'status') and
                    hasattr(response.result.status, 'message') and
                    response.result.status.message):
                    merge_metadata(response.result.status.message, request.message)
                    m = response.result.status.message
                    logger.debug(f">>> Received status update: {m}")
                    if not m.metadata:
                        m.metadata = {}
                    if 'message_id' in m.metadata:
                        m.metadata['last_message_id'] = m.metadata['message_id']
                    m.metadata['message_id'] = str(uuid.uuid4())
                if task_callback:
                    task = task_callback(response.result)
                if hasattr(response.result, 'final') and response.result.final:
                    break
            return task
        else:
            response = await self.client.send_task(request.model_dump())
            merge_metadata(response.result, request)
            # For task status updates, we need to propagate metadata and provide
            # a unique message id.
            if (hasattr(response.result, 'status') and
                hasattr(response.result.status, 'message') and
                response.result.status.message):
                merge_metadata(response.result.status.message, request.message)
                m = response.result.status.message
                if not m.metadata:
                    m.metadata = {}
                if 'message_id' in m.metadata:
                    m.metadata['last_message_id'] = m.metadata['message_id']
                m.metadata['message_id'] = str(uuid.uuid4())

            if task_callback:
                task_callback(response.result)
            return response.result

def merge_metadata(target, source):
    if not hasattr(target, 'metadata') or not hasattr(source, 'metadata'):
        return
    if target.metadata and source.metadata:
        target.metadata.update(source.metadata)
    elif source.metadata:
        target.metadata = dict(**source.metadata)


    # async def send_task(self, request: TaskSendParams) -> Task:
    #     """Send task to remote agent and return completed response"""
    #     # Non-streaming implementation
    #     response = await self.client.send_task(request.model_dump())
    #     return response.result

    # async def send_task(self, payload: dict[str, Any]) -> SendTaskResponse:
    #     # log payload
    #     logger.debug("Sending task to remote agent", payload=payload)
    #     request = SendTaskRequest(params=payload)
    #     return SendTaskResponse(**await self._send_request(request))

def get_message_id(m: Message | None) -> str  | None:
  if not m or not m.metadata or 'message_id' not in m.metadata:
    return None
  return m.metadata['message_id']

def get_last_message_id(m: Message | None) -> str | None:
  if not m or not m.metadata or 'last_message_id' not in m.metadata:
    return None
  return m.metadata['last_message_id']

def task_still_open(task: Task | None) -> bool:
  if not task:
    return False
  return task.status.state in [
      TaskState.SUBMITTED, TaskState.WORKING, TaskState.INPUT_REQUIRED
  ]
class ActionA2A(Action):
    """Custom action for A2A client functionality"""

    _tasks: list[Task]
    _task_map: dict[str, str]

    def __init__(self):
        # super().__init__(name)
        # The self.agents dictionary is used to store and manage connections to remote agents.
        self.agents: Dict[str, RemoteAgentConnections] = {}
        self.load_agents()
        self.agent_card = None
        self._tasks = []
        self._task_map = {}
        # self.task_callback: Optional[TaskUpdateCallback] = None

    def add_task(self, task: Task):
        self._tasks.append(task)

    def update_task(self, task: Task):
        for i, t in enumerate(self._tasks):
            if t.id == task.id:
                self._tasks[i] = task
                return

    def attach_message_to_task(self, message: Message | None, task_id: str):
        if message and message.metadata and 'message_id' in message.metadata:
            self._task_map[message.metadata['message_id']] = task_id

    def insert_id_trace(self, message: Message | None):
        if not message:
            return
        message_id = get_message_id(message)
        last_message_id = get_last_message_id(message)
        if message_id and last_message_id:
            self._next_id[last_message_id] = message_id

    def insert_message_history(self, task: Task, message: Message | None):
        if not message:
            return
        if task.history is None:
            task.history = []
        message_id = get_message_id(message)
        if not message_id:
            return
        if get_message_id(task.status.message) not in [
            get_message_id(x) for x in task.history
        ]:
            task.history.append(task.status.message)
        else:
            print("Message id already in history", get_message_id(task.status.message), task.history)

    def add_or_get_task(self, task: TaskCallbackArg):
        current_task = next(filter(lambda x: x.id == task.id, self._tasks), None)
        if not current_task:
            conversation_id = None
            if task.metadata and 'conversation_id' in task.metadata:
                conversation_id = task.metadata['conversation_id']
            current_task = Task(
                id=task.id,
                status=TaskStatus(state = TaskState.SUBMITTED), #initialize with submitted
                metadata=task.metadata,
                artifacts = [],
                sessionId=conversation_id,
            )
            self.add_task(current_task)
            return current_task

        return current_task

    def process_artifact_event(self, current_task:Task, task_update_event: TaskArtifactUpdateEvent):
        artifact = task_update_event.artifact
        if not artifact.append:
            #received the first chunk or entire payload for an artifact
            if artifact.lastChunk is None or artifact.lastChunk:
                #lastChunk bit is missing or is set to true, so this is the entire payload
                #add this to artifacts
                if not current_task.artifacts:
                    current_task.artifacts = []
                current_task.artifacts.append(artifact)
            else:
                #this is a chunk of an artifact, stash it in temp store for assemling
                if not task_update_event.id in self._artifact_chunks:
                    self._artifact_chunks[task_update_event.id] = {}
                self._artifact_chunks[task_update_event.id][artifact.index] = artifact
        else:
            # we received an append chunk, add to the existing temp artifact
            current_temp_artifact = self._artifact_chunks[task_update_event.id][artifact.index]
            # TODO handle if current_temp_artifact is missing
            current_temp_artifact.parts.extend(artifact.parts)
            if artifact.lastChunk:
                current_task.artifacts.append(current_temp_artifact)
                del self._artifact_chunks[task_update_event.id][artifact.index]

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
                    self.agent_card = cardresolver.get_agent_card()
                    self.agents[agent["name"]] = RemoteAgentConnections(
                        cardresolver.get_agent_card()
                    )
                    logger.info(
                        f"Loaded agent: {self.agent_card.name}, vers: {self.agent_card.version}"
                    )
        except Exception as e:
            logger.error(f"Failed to load A2A agent {agent['name']}: {str(e)}")

    def task_callback(self, task: TaskCallbackArg):
        if isinstance(task, TaskStatusUpdateEvent):
            current_task = self.add_or_get_task(task)
            current_task.status = task.status
            self.attach_message_to_task(task.status.message, current_task.id)
            self.insert_message_history(current_task, task.status.message)
            self.update_task(current_task)
            self.insert_id_trace(task.status.message)
            return current_task
        elif isinstance(task, TaskArtifactUpdateEvent):
            current_task = self.add_or_get_task(task)
            self.process_artifact_event(current_task, task)
            self.update_task(current_task)
            return current_task
            # Otherwise this is a Task, either new or updated
        elif not any(filter(lambda x: x.id == task.id, self._tasks)):
            self.attach_message_to_task(task.status.message, task.id)
            self.insert_id_trace(task.status.message)
            self.add_task(task)
            return task
        else:
            self.attach_message_to_task(task.status.message, task.id)
            self.insert_id_trace(task.status.message)
            self.update_task(task)
            return task

    async def run(self, dispatcher, tracker, domain):
        """Execute A2A client action"""
        current_message = tracker.latest_message
        session_id = tracker.sender_id

        agent_name = tracker.get_slot("a2a_agent_name")
        a2a_message = tracker.get_slot("a2a_message")
        logger.debug(f"=== Agent name: {agent_name}, a2a_message slot: {a2a_message}, current_message: {current_message['text']} ===")
        if not agent_name or agent_name not in self.agents:
            logger.error(f"Invalid A2A agent specified: {agent_name}")
            dispatcher.utter_message(
                text=f"Invalid A2A agent specified: {agent_name}. Try again later"
            )
            return [SlotSet("a2a_status", "error")]

        request = TaskSendParams(
            id=str(uuid.uuid4()),
            sessionId=session_id,
            message=Message(
                role="user",
                parts=[TextPart(text=current_message["text"])],
                metadata=None,
                # metadata=current_message["metadata"]
            ),
            acceptedOutputModes=["text"],
            pushNotification=None,
            historyLength=None,
            metadata=None
        )

        try:
            connection = self.agents[agent_name]
            # task = await connection.send_task(payload)
            task = await connection.send_task(request, self.task_callback)

            # Process response
            status = task.status.state
            logger.debug(f"== Task status: {status} ==")
            if status == TaskState.COMPLETED:
                self._send_response(dispatcher, task)
                return [SlotSet("a2a_status", "completed")]
            elif status == TaskState.INPUT_REQUIRED:
                self._send_response(dispatcher, task)
                # dispatcher.utter_message("Please provide additional information")
                return [SlotSet("a2a_status", "input-required")]
            else:
                dispatcher.utter_message("Request encountered an unexpected error")
                return [SlotSet("a2a_status", "error")]

        except Exception as e:
            logger.error(f"Agent call failed: {str(e)}")
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
                if part.type == "data" and "instructions" in part.data:
                    logger.debug(f"Uttering instructions: {part.data['instructions']}")
                    dispatcher.utter_message(part.data["instructions"])
