import logging
import json
from datetime import datetime
from typing import Any, Dict, List, Text, Optional

# import requests
import asyncio
import aiohttp
import json
import pprint

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import (
    SlotSet,
    EventType,
    SessionStarted,
    ActionExecuted,
)

from actions import config

logger = logging.getLogger(__name__)

class ActionSessionStart(Action):
    def name(self) -> Text:
        return "action_session_start"

    @staticmethod
    def fetch_slots(tracker: Tracker) -> List[EventType]:
        """Return slots to carry over."""
        slots = []
        return slots

    @staticmethod
    def set_which_bot(tracker: Tracker) -> List[EventType]:
        """Set which_bot."""
        
        which_bot = "external"
        
        # If we use the slack channel, then it is the internal bot
        # TODO
        print("TODO: check on the channel when you want to run internal kapa bot...")
        
        
        return [SlotSet("which_bot", value=which_bot)]
    
    async def run(
      self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        # the session should begin with a `session_started` event
        events = [SessionStarted()]

        # any slots that should be carried over should come after the
        # `session_started` event
        events.extend(self.fetch_slots(tracker))
        events.extend(self.set_which_bot(tracker))

        # an `action_listen` should be added at the end as a user message follows
        events.append(ActionExecuted("action_listen"))

        return events