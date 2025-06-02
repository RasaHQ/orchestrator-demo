import yaml
import uuid
from typing import Dict, Optional, Any, Callable
import logging
import httpx
import datetime

from pydantic import BaseModel, Field, TypeAdapter

# from .card_resolver import A2ACardResolver
# from .client import A2AClient

from a2a.client import A2AClient, A2ACardResolver
from a2a.types import (
    AgentCard,
    AgentCapabilities,
    AgentSkill,
    Artifact,
    FilePart,
    FileWithBytes,
    GetTaskRequest,
    JSONRPCErrorResponse,
    Message,
    MessageSendConfiguration,
    MessageSendParams,
    Part,
    Role,
    SendMessageRequest,
    SendStreamingMessageRequest,
    Task,
    TaskArtifactUpdateEvent,
    TextPart,
    TaskQueryParams,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)
from actions.api.common.utils.push_notification_auth import PushNotificationReceiverAuth


class Event(BaseModel):
    id: str
    actor: str = ""
    # TODO: Extend to support internal concepts for models, like function calls.
    content: Message
    timestamp: float


# from actions.api.common.types import (
#     AgentCard,
#     Task,
#     TaskState,
#     Message,
# TaskStatusUpdateEvent,
# TaskStatus,
# TaskArtifactUpdateEvent,
#     AgentCapabilities,
#     AgentSkill,
#     Artifact,
# )
# from actions.api.common.types import TextPart
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet

logger = logging.getLogger(__name__)

TaskCallbackArg = Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent
TaskUpdateCallback = Callable[[TaskCallbackArg, AgentCard], Task]


class RemoteAgentConnections:
    """Handles connections and communication with a single remote agent"""

    def __init__(self, agent_card: AgentCard):
        self.agent_card = agent_card
        self.client = A2AClient(httpx.AsyncClient(timeout=30), agent_card=agent_card)

    @property
    def events(self) -> list[Event]:
        return sorted(self._events.values(), key=lambda x: x.timestamp)

    async def send_message(
        self,
        request: MessageSendParams,
        task_callback: TaskUpdateCallback | None,
    ) -> Task | Message | None:
        if self.agent_card.capabilities.streaming:
            task = None
            async for response in self.client.send_message_streaming(
                SendStreamingMessageRequest(params=request)
            ):
                if not response.root.result:
                    return response.root.error
                # In the case a message is returned, that is the end of the interaction.
                event = response.root.result
                if isinstance(event, Message):
                    return event

                # Otherwise we are in the Task + TaskUpdate cycle.
                if task_callback and event:
                    task = task_callback(event, self.agent_card)
                if hasattr(event, "final") and event.final:
                    break
            return task
        else:  # Non-streaming
            response = await self.client.send_message(
                SendMessageRequest(params=request)
            )
            if isinstance(response.root, JSONRPCErrorResponse):
                return response.root.error
            if isinstance(response.root.result, Message):
                return response.root.result

            if task_callback:
                task_callback(response.root.result, self.agent_card)
            return response.root.result

    async def send_task(
        self,
        request: MessageSendParams,
        task_callback: TaskUpdateCallback | None,
    ) -> Task | None:
        if self.agent_card.capabilities.streaming:
            task = None
            if task_callback:
                task_callback(
                    Task(
                        id=request.id,
                        sessionId=request.message.sessionId,
                        status=TaskStatus(
                            state=TaskState.SUBMITTED,
                            message=request.message,
                        ),
                        history=[request.message],
                    )
                )
            logger.debug(f">>> Sending request to remote agent: {request.model_dump()}")
            response_stream = self.client.send_message_streaming(
                SendStreamingMessageRequest(
                    id=str(uuid.uuid4()),
                    params=request,
                )
            )
            async for result in response_stream:
                if isinstance(result.root, JSONRPCErrorResponse):
                    logger.error(f"Error: {result.root.error}")
                    return None
                event = result.root.result
                logger.debug(
                    f">>> stream event => {event.model_dump_json(exclude_none=True)}"
                )
                if task_callback:
                    task = task_callback(event)
                if isinstance(event, Task) and event.status.state in [
                    TaskState.COMPLETED,
                    TaskState.ERROR,
                ]:
                    break
            return task
        else:
            try:
                response = await self.client.send_message(
                    SendMessageRequest(
                        id=str(uuid.uuid4()),
                        params=request,
                    )
                )
                event = response.root.result
                if task_callback:
                    task_callback(event)
                return event
            except Exception as e:
                logger.error(f"Failed to complete the call: {e}")
                return None


def merge_metadata(target, source):
    if not hasattr(target, "metadata") or not hasattr(source, "metadata"):
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


def get_message_id(m: Message | None) -> str | None:
    if not m or not m.metadata or "message_id" not in m.metadata:
        return None
    return m.metadata["message_id"]


def get_last_message_id(m: Message | None) -> str | None:
    if not m or not m.metadata or "last_message_id" not in m.metadata:
        return None
    return m.metadata["last_message_id"]


def task_still_open(task: Task | None) -> bool:
    if not task:
        return False
    return task.status.state in [
        TaskState.SUBMITTED,
        TaskState.WORKING,
        TaskState.INPUT_REQUIRED,
    ]


class ActionA2A(Action):
    """Custom action for A2A client functionality"""

    _tasks: list[Task]
    _task_map: dict[str, str]

    def __init__(self):
        # super().__init__(name)
        # The self.agents dictionary is used to store and manage connections to remote agents.
        self.agents: Dict[str, RemoteAgentConnections] = {}
        logger.info(f"Loaded agents:")
        for agent in self.agents:
            logger.info(f"  - {agent}")
        self.agent_card = None
        self._tasks = []
        self._task_map = {}
        self._events: dict[str, Event] = {}
        self.dispatcher: Optional[Callable] = None # need dispatcher to send messages back to Rasa as they are streamed via A2A SSE
        # self.task_callback: Optional[TaskUpdateCallback] = None
        return None

    def add_task(self, task: Task):
        self._tasks.append(task)

    def update_task(self, task: Task):
        for i, t in enumerate(self._tasks):
            if t.id == task.id:
                self._tasks[i] = task
                return

    def attach_message_to_task(self, message: Message | None, task_id: str):
        if message and message.metadata and "message_id" in message.metadata:
            self._task_map[message.metadata["message_id"]] = task_id

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
            print(
                "Message id already in history",
                get_message_id(task.status.message),
                task.history,
            )

    def add_or_get_task(self, event: TaskCallbackArg):
        task_id = None
        if isinstance(event, Message):
            task_id = event.taskId
        elif isinstance(event, Task):
            task_id = event.id
        else:
            task_id = event.taskId
        if not task_id:
            task_id = str(uuid.uuid4())
        current_task = next(filter(lambda x: x.id == task_id, self._tasks), None)
        if not current_task:
            context_id = event.contextId
            current_task = Task(
                id=task_id,
                # initialize with submitted
                status=TaskStatus(state=TaskState.submitted),
                artifacts=[],
                contextId=context_id,
            )
            self.add_task(current_task)
            return current_task

        return current_task

    def process_artifact_event(
        self, current_task: Task, task_update_event: TaskArtifactUpdateEvent
    ):
        artifact = task_update_event.artifact
        if not task_update_event.append:
            # received the first chunk or entire payload for an artifact
            if task_update_event.lastChunk is None or task_update_event.lastChunk:
                # lastChunk bit is missing or is set to true, so this is the entire payload
                # add this to artifacts
                if not current_task.artifacts:
                    current_task.artifacts = []
                current_task.artifacts.append(artifact)
            else:
                # this is a chunk of an artifact, stash it in temp store for assembling
                if artifact.artifactId not in self._artifact_chunks:
                    self._artifact_chunks[artifact.artifactId] = []
                self._artifact_chunks[artifact.artifactId].append(artifact)
        else:
            # we received an append chunk, add to the existing temp artifact
            current_temp_artifact = self._artifact_chunks[artifact.artifactId][-1]
            # TODO handle if current_temp_artifact is missing
            current_temp_artifact.parts.extend(artifact.parts)
            if task_update_event.lastChunk:
                if current_task.artifacts:
                    current_task.artifacts.append(current_temp_artifact)
                else:
                    current_task.artifacts = [current_temp_artifact]
                del self._artifact_chunks[artifact.artifactId][-1]

    def name(self) -> str:
        return "action_a2a"

    async def load_agents(self):
        """
        Load agent configurations from a2a.yml
        - Get agent card at {agent["base_url]}{agent["agent_card_path"]}
        """
        with open("a2a.yml", "r") as file:
            config = yaml.safe_load(file)["remote_agents"]
            for agent in config:
                logger.info(
                    f"Loading agent: {agent['name']}, {agent['base_url']}{agent['agent_card_path']}"
                )
                async with httpx.AsyncClient(timeout=30) as httpx_client:
                    card_resolver = A2ACardResolver(
                        httpx_client, agent["base_url"], agent["agent_card_path"]
                    )
                    try:
                        self.agent_card = await card_resolver.get_agent_card()
                        # self.agent_card["url"] = agent.get("agent_endpoint_path", "/")
                        logger.info(f"Agent card: {self.agent_card}")
                        logger.info(f"agent['name']: {agent['name']}")
                        self.agents[agent["name"]] = RemoteAgentConnections(
                            self.agent_card
                            # card_resolver.get_agent_card()
                        )
                        logger.info(
                            f"Loaded agent: {self.agent_card.name}, vers: {self.agent_card.version}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to load A2A agent card {agent['name']}: {str(e)}"
                        )

    async def ensure_agents_loaded(self):
        if not self.agents:
            await self.load_agents()
            logger.info(f"Loaded agents:")
            for agent in self.agents:
                logger.info(f"  - {agent}")

# In class ActionA2A:

    # Modify task_callback to ensure it calls the dispatching logic
    def task_callback(self, event_data: TaskCallbackArg, agent_card: AgentCard) -> Task: # Renamed `task` arg to `event_data` for clarity
        # This method is responsible for updating the internal state of the task
        # and also for triggering dispatch of any messages from the event_data.

        current_task: Optional[Task] = None

        if isinstance(event_data, TaskStatusUpdateEvent):
            logger.info(f"DETAILED_EVENT_LOG: TaskStatusUpdateEvent received. Status: {event_data.status.state}")
            if event_data.status.message:
                logger.info(f"DETAILED_EVENT_LOG: TaskStatusUpdateEvent - Message object: {event_data.status.message.model_dump_json(exclude_none=True, indent=2)}")
                for i, part_wrapper in enumerate(event_data.status.message.parts):
                    # Assuming part_wrapper is a 'Part' pydantic model which has a 'root' field
                    # that can be TextPart, FunctionCallPart etc.
                    logger.info(f"DETAILED_EVENT_LOG: Part {i} kind: {part_wrapper.root.kind if hasattr(part_wrapper, 'root') else 'N/A'}")
                    logger.info(f"DETAILED_EVENT_LOG: Part {i} content: {part_wrapper.model_dump_json(exclude_none=True, indent=2)}")
            else:
                logger.info("DETAILED_EVENT_LOG: TaskStatusUpdateEvent - No message object in status.")
            current_task = self.add_or_get_task(event_data)
            current_task.status = event_data.status
            self.attach_message_to_task(event_data.status.message, current_task.id)
            self.insert_message_history(current_task, event_data.status.message)
            self.update_task(current_task)
        elif isinstance(event_data, TaskArtifactUpdateEvent):
            logger.info(f"DETAILED_EVENT_LOG: TaskArtifactUpdateEvent received. Status: {event_data.artifact.name}")
            current_task = self.add_or_get_task(event_data)
            self.process_artifact_event(current_task, event_data)
            self.update_task(current_task)
        elif isinstance(event_data, Task):
            logger.info(f"DETAILED_EVENT_LOG: Task event received: {event_data.model_dump_json(exclude_none=True, indent=2)}")
            # This could be an initial task submission confirmation or a full task update
            # Check if task already exists
            existing_task = next((t for t in self._tasks if t.id == event_data.id), None)
            if existing_task:
                # Update existing task
                existing_task.status = event_data.status # Essential
                if event_data.artifacts: existing_task.artifacts = event_data.artifacts # Or merge
                if event_data.history: existing_task.history = event_data.history # Or merge
                # Update other fields as necessary
                self.attach_message_to_task(event_data.status.message, existing_task.id)
                current_task = existing_task
                self.update_task(current_task)
            else:
                # New task
                self.attach_message_to_task(event_data.status.message, event_data.id)
                self.add_task(event_data) # event_data is already a Task object
                current_task = event_data
        else: # Should not happen if TaskCallbackArg is comprehensive
            logger.warning(f"Unhandled event type in task_callback: {type(event_data)}")
            # Attempt to get a task anyway, though it might be incomplete
            current_task = self.add_or_get_task(event_data)


        # Now, call a method to dispatch the message from this event_data, if any
        self._dispatch_event_content(event_data, agent_card)
        
        # Log the event internally (your existing emit_event logic can be repurposed for this)
        self._log_event_internally(event_data, agent_card)


        if not current_task: # Should always have a task by now from add_or_get_task
             # This is a fallback, ideally current_task is always set.
             current_task = self.add_or_get_task(event_data)
             logger.warning(f"current_task was unexpectedly None in task_callback, re-fetched for event {event_data.id if hasattr(event_data, 'id') else event_data.taskId}")


        return current_task # Must return the updated task

    def _dispatch_event_content(self, event_data: TaskCallbackArg, agent_card: AgentCard):
        """Extracts content from the event and dispatches it."""
        if not self.dispatcher:
            logger.warning("Dispatcher not set in ActionA2A, cannot send message to user.")
            return

        content_message: Optional[Message] = None
        context_id = event_data.contextId
        task_id = event_data.taskId if hasattr(event_data, "taskId") else getattr(event_data, "id", None)


        if isinstance(event_data, TaskStatusUpdateEvent):
            if event_data.status.message:
                content_message = event_data.status.message
            # Avoid dispatching generic "submitted" or "working" if no actual text
            elif event_data.status.state in [TaskState.submitted, TaskState.working] and \
                 (not event_data.status.message or not any(p.root.text for p in event_data.status.message.parts if hasattr(p.root, 'text'))):
                 logger.debug(f"Skipping dispatch for status update: {event_data.status.state} without specific message content.")
                 return # Don't dispatch simple status changes without text
            else: # Create a message for other states if no explicit message
                logger.debug(f"Creating message for task status: {event_data.status.state} without explicit message content.")
                content_message = Message(
                    parts=[Part(root=TextPart(text=f"Task status: {str(event_data.status.state)}"))], # type: ignore
                    role=Role.agent,
                    messageId=str(uuid.uuid4()),
                    contextId=context_id,
                    taskId=task_id,
                )
        elif isinstance(event_data, TaskArtifactUpdateEvent):
            # Dispatch text parts of the artifact.
            # The user's log shows the artifact text is "Here is a reimbursement request form for you to fill out:\n\n```json..."
            # This should be dispatched.
            artifact_text_parts = [part.root.text for part in event_data.artifact.parts if part.root.kind == "text" and part.root.text]
            if artifact_text_parts:
                full_text = "\n".join(artifact_text_parts)
                # Create a message object to dispatch
                content_message = Message(
                    parts=[Part(root=TextPart(text=full_text))], # type: ignore
                    role=Role.agent,
                    messageId=str(uuid.uuid4()),
                    contextId=context_id,
                    taskId=task_id
                )
            else:
                logger.debug(f"Artifact update event for {event_data.artifact.name} has no text parts to dispatch immediately.")
                return # No text to dispatch from this artifact event

        elif isinstance(event_data, Task):
            # This is a full Task object. It might be an initial echo or a final task state.
            # Only dispatch if it's not just a "submitted" confirmation without a specific message.
            if event_data.status and event_data.status.message and event_data.status.state != TaskState.submitted:
                content_message = event_data.status.message
            elif event_data.status and event_data.status.state != TaskState.submitted: # e.g. completed with artifacts but no direct message
                 pass # Artifacts handled by TaskArtifactUpdateEvent, or final task processing in run()

        if content_message and content_message.parts:
            logger.debug(f"Dispatching content from event for task {task_id}: {content_message.model_dump_json(exclude_none=True)}")
            for part in content_message.parts:
                if hasattr(part.root, "text") and part.root.text: # Check if text exists and is not empty
                    self.dispatcher.utter_message(text=part.root.text)
                # You can add handling for other part kinds (data, file) here if needed,
                # similar to your _send_response method.
                elif part.root.kind == 'data' and hasattr(part.root, "data"):
                    instructions = part.root.data.get('instructions', '')
                    if instructions:
                        self.dispatcher.utter_message(text=instructions)


    def _log_event_internally(self, task_event_data: TaskCallbackArg, agent_card: AgentCard):
        """
        This replaces the main functionality of your original emit_event,
        which was to create an Event object and add it to self._events.
        """
        content = None
        context_id = task_event_data.contextId
        task_id_from_event = task_event_data.taskId if hasattr(task_event_data, "taskId") else getattr(task_event_data, "id", None)

        if isinstance(task_event_data, TaskStatusUpdateEvent):
            if task_event_data.status.message:
                content = task_event_data.status.message
            else: # Create a simple message for logging status if no actual message content
                content = Message(
                    parts=[Part(root=TextPart(text=f"Status: {str(task_event_data.status.state)}"))], #type: ignore
                    role=Role.agent, messageId=str(uuid.uuid4()),
                    contextId=context_id, taskId=task_id_from_event
                )
        elif isinstance(task_event_data, TaskArtifactUpdateEvent):
            # For logging, you might want a simpler representation or just the artifact name
            content = Message(
                parts=[Part(root=TextPart(text=f"Artifact received: {task_event_data.artifact.name}"))], #type: ignore
                role=Role.agent, messageId=str(uuid.uuid4()),
                contextId=context_id, taskId=task_id_from_event
            )
        elif isinstance(task_event_data, Task): # Full Task object
            if task_event_data.status and task_event_data.status.message:
                content = task_event_data.status.message
            elif task_event_data.artifacts: # Log based on artifacts if no direct message
                parts = [Part(root=TextPart(text=f"Task with artifact: {a.name}")) for a in task_event_data.artifacts] #type: ignore
                content = Message(
                    parts=parts, role=Role.agent, messageId=str(uuid.uuid4()),
                    taskId=task_event_data.id, contextId=context_id
                )
            else: # Log based on status if nothing else
                 content = Message(
                    parts=[Part(root=TextPart(text=f"Task status: {str(task_event_data.status.state)}"))], #type: ignore
                    role=Role.agent, messageId=str(uuid.uuid4()),
                    taskId=task_event_data.id, contextId=context_id
                )
        
        if content:
            # Create and add your internal Event object
            event_to_log = Event(
                id=str(uuid.uuid4()),
                actor=agent_card.name,
                content=content, # This is a Message object
                timestamp=datetime.datetime.utcnow().timestamp(),
            )
            self.add_event(event_to_log) # Your existing method to add to self._events

    def emit_event(self, task: TaskCallbackArg, agent_card: AgentCard):
        content = None
        context_id = task.contextId
        if isinstance(task, TaskStatusUpdateEvent):
            if task.status.message:
                content = task.status.message
            else:
                content = Message(
                    parts=[Part(root=TextPart(text=str(task.status.state)))],
                    role=Role.agent,
                    messageId=str(uuid.uuid4()),
                    contextId=context_id,
                    taskId=task.taskId,
                )
        elif isinstance(task, TaskArtifactUpdateEvent):
            content = Message(
                parts=task.artifact.parts,
                role=Role.agent,
                messageId=str(uuid.uuid4()),
                contextId=context_id,
                taskId=task.taskId,
            )
        elif task.status and task.status.message:
            content = task.status.message
        elif task.artifacts:
            parts = []
            for a in task.artifacts:
                parts.extend(a.parts)
            content = Message(
                parts=parts,
                role=Role.agent,
                messageId=str(uuid.uuid4()),
                taskId=task.id,
                contextId=context_id,
            )
        else:
            content = Message(
                parts=[Part(root=TextPart(text=str(task.status.state)))],
                role=Role.agent,
                messageId=str(uuid.uuid4()),
                taskId=task.id,
                contextId=context_id,
            )
        if content:
            self.add_event(
                Event(
                    id=str(uuid.uuid4()),
                    actor=agent_card.name,
                    content=content,
                    timestamp=datetime.datetime.utcnow().timestamp(),
                )
            )

    def add_event(self, event: Event):
        self._events[event.id] = event

    def _send_response(self, dispatcher, task):
        """Send back response parts as utterances"""
        # Send message parts
        if task.status.message:
            for part in task.status.message.parts:
                if part.root.kind == "text":
                    dispatcher.utter_message(text=part.text)
                elif part.root.kind == 'data':
                    instructions = part.root.data.get('instructions', '')
                    if instructions:
                        logger.debug(
                            f"Uttering data part: {part.root.data.get('instructions', '')}"
                        )
                        dispatcher.utter_message(text=part.root.data.get('instructions', ''))
                    else:
                        logger.warning(
                            f"Data part without instructions: {part.root.data}"
                        )

        # Send artifact text parts
        if task.artifacts:
            for artifact in task.artifacts:
                for part in artifact.parts:
                    if part.root.kind == "text":
                        logger.info(f"Uttering text part: {part.root.text}")
                        dispatcher.utter_message(text=f"{part.root.text}")
                    else:
                        logger.warning(
                            f"Unexpected part type in artifact: {part.root.kind}"
                        )
                    # if part.root.kind == "data" and "instructions" in part.data:
                    #     logger.debug(
                    #         f"Uttering instructions: {part.data['instructions']}"
                    #     )
                    #     dispatcher.utter_message(part.data["instructions"])

    async def run(self, dispatcher, tracker, domain):
        events = []
        """Execute A2A client action"""
        self.dispatcher = dispatcher # Store dispatcher for use in callbacks
        await self.ensure_agents_loaded()
        agent_list = ""
        for agent in self.agents:
            logger.info(f"Agent: {agent}, card: {self.agents[agent].agent_card}")
            # append agent name to agent_list
            agent_list += f"{agent}, "
        events.append(SlotSet("a2a_agents", agent_list.strip(", ")))
        current_message = tracker.latest_message
        session_id = tracker.sender_id

        agent_name = tracker.get_slot("a2a_agent_name")
        a2a_message = tracker.get_slot("a2a_message")
        logger.debug(
            f"=== Agent name: {agent_name}, a2a_message slot: {a2a_message}, current_message: {current_message['text']} ==="
        )
        if not agent_name or agent_name not in self.agents:
            logger.error(f"Invalid A2A agent specified: {agent_name}, agents:")
            for agent in self.agents:
                logger.error(f"  - {agent}: {self.agents[agent].agent_card.name}")
            dispatcher.utter_message(
                text=f"Invalid A2A agent specified: {agent_name}. Available agents: {self.agents}. Try again later"
            )
            return [SlotSet("a2a_status", "error")]

        logger.info(
            f"=== Sending message to agent: {agent_name}, message: {current_message['text']}, session_id: {session_id} ==="
        )

        request: MessageSendParams = MessageSendParams(
            # id=str(uuid.uuid4()),
            # referenceTaskIds=str(uuid.uuid4()),
            message=Message(
                role="user",
                parts=[TextPart(text=current_message["text"])],
                messageId=str(uuid.uuid4()),
                sessionId=session_id,
                # contextId=contextId,
                # taskId=taskId,
            ),
            configuration=MessageSendConfiguration(
                acceptedOutputModes=["text", "text/plain"],
            ),
        )

        try:
            connection = self.agents[agent_name]
            logger.debug(f"=== Sending request: {request}")
            # task = await connection.send_task(request, self.task_callback)
            task = await connection.send_message(request, self.task_callback)
            logger.debug(f"=== Received task: {task}")

            if not task:
                dispatcher.utter_message("Request encountered an error")
                return [SlotSet("a2a_status", "error")]

            # Process response
            status = task.status.state
            logger.debug(f"== Task status: {status} ==")

            if task.status.state == TaskState.completed:
                # self._send_response(dispatcher, task)
                events.append(SlotSet("a2a_status", "completed"))
                return events
            elif task.status.state == TaskState.input_required:
                # self._send_response(dispatcher, task)
                events.append(SlotSet("a2a_status", "input-required"))
                return events
            else:
                dispatcher.utter_message(
                    f"Request encountered an unexpected error: {task.status.message}"
                )
                events.append(SlotSet("a2a_status", "error"))
                return events

        except Exception as e:
            logger.error(f"Agent call failed: {str(e)}, {task.status.message}")
            dispatcher.utter_message(
                text=f"Agent call failed: {str(e)}, {task.status.message}"
            )
            events.append(SlotSet("a2a_status", "error"))
            return events

        return []
