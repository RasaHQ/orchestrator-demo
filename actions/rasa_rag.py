from typing import Any, Dict, List, Text

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

from actions.api.kapa import KapaSearchAPI

import os
import structlog
from actions.api.template_renderer import TemplateRenderer
from litellm import completion
import asyncio  # Import asyncio to handle async calls

# Configure structlog
logger = structlog.get_logger()

class RasaRAG(Action):
    def name(self) -> str:
        project_id = os.environ.get("KAPA_RASA_PROJECT_ID", "")
        token = os.environ.get("KAPA_RASA_TOKEN", "")
        num_results = os.environ.get("KAPA_RASA_NUM_RESULTS", 5)
        self.model_name = os.environ.get("KAPA_LLM", "gpt-4o")
        self.kapa_api = KapaSearchAPI(
            project_id=project_id, token=token, num_results=num_results
        )
        template_file = os.environ.get("RAG_TEMPLATE", "prompts/rag_completion.jinja2")
        self.renderer = TemplateRenderer(template_file)
        return "action_rasa_rag"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[str, Any]
    ) -> List[Dict[Text, Any]]:
        events = []
        events.append(SlotSet("return_value", "success"))
        latest_message = tracker.latest_message["text"]

        try:
            # Await the async call directly
            result = await self.kapa_api.search(query_string=latest_message)
        except Exception as e:
            logger.error(
                "Error in KapaSearchAPI",
                error=str(e),
                query=latest_message,
            )
            events.append(SlotSet("return_value", "failed"))
            return events

        try:
            # Merge jinja2 template with results
            prompt = self.renderer.render(results=result, user_message=latest_message)
            logger.debug("rasa_rag.prompt", prompt=prompt)

            response = completion(
                model=self.model_name,
                messages=[{"content": prompt, "role": "user"}],
            )
            content = response.choices[0].message.content
            dispatcher.utter_message(text=content)
        except Exception as e:
            logger.error(
                "Error in litellm completion",
                error=str(e),
                query=latest_message,
            )
            events.append(SlotSet("return_value", "failed"))

        return events