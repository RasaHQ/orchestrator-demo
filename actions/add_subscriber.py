from typing import Any, Dict, List, Text
import logging

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

from actions.db import add_contact, get_contacts, Contact

logger = logging.getLogger(__name__)

class AddContact(Action):
    def name(self) -> str:
        return "action_add_subscriber"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[str, Any]
    ) -> List[Dict[Text, Any]]:
        email = tracker.get_slot("email")

        logger.debug(f"subscribing email: {email}")

        # TODO: Add the email to the newsletter database

        return []
