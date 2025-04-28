import json
import pytest
from pathlib import Path
import sys

from rasa_sdk.executor import CollectingDispatcher, Tracker
from rasa_sdk.events import SlotSet, ActionExecuted, SessionStarted

sys.path.append(str(Path(__file__).parent.parent))
from actions.a2a import ActionA2A
here = Path(__file__).parent.resolve()

EXP_REIMBURSEMENT_TRACKER = Tracker.from_dict(json.load(open(here / "./exp_reimbursement.json")))

@pytest.fixture
def dispatcher():
    return CollectingDispatcher()


@pytest.fixture
def domain():
    return dict()

async def test_action_a2a_exp_reimbursement(dispatcher, domain):
    tracker = EXP_REIMBURSEMENT_TRACKER
    action = ActionA2A()
    events = await action.run(dispatcher, tracker, domain)
    expected_events = [
        SlotSet("a2a_status", "input-required"),
    ]
    # expected_response = "utter_cc_pay_cancelled"
    assert events == expected_events
    assert "amount" in dispatcher.messages[0]['text']
