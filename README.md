# Orchestrator Demo

This is a Rasa Orchestrator Demo bot to highlight the ability to use Rasa to orchestrate a conversation that involves multiple RAG's, agents ([A2A](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)) and tools ([MCP](https://www.anthropic.com/news/model-context-protocol)).

The current demo implements two RAG's using Kapa and two A2A agents. The RAG's cover a Rasa questions and Kubernetes questions. This is implemented via a [Rasa questions flow](./data/flows/rasa.yml) and [custom action](./actions/rasa_rag.py) and a Kubernetes [flow](./data/flows/kubernetes.yml) and [custom action](./actions/kubernetes_rag.py). The two A2A agents are a Google agent kit expense reimbursement agent and a Langgraph currency exchange agent.

Example questions:

- What is the rasa config.yml
- What is the kubectl command to show running pods
- I need reimbursement for my hotel room
- How many INR is one euro

## Agent Integration

The agent integration is a work in progress. There's an [expense reimbursement flow](./data/flows/reimbursement.yml) that calls a custom action that implements the A2A client and a [curreny exchange flow](./data/flows/currency_exchange.yml). The expense reimbursement agent has a [bug](https://github.com/google/A2A/issues/332) which causes it to frequently return a status of `completed` when the agent still needs input.

It should be easy to demo an MCP example via A2A. There's a discussion about an MCP version [here](https://github.com/google/A2A/issues/281) including an example [here](https://github.com/djsamseng/blpapi-a2a/blob/main/src/blpapi_a2a/blp_a2a_agent.py)

Example interaction:

```mermaid
sequenceDiagram
    User->>Rasa: I need reimbursement for my plane ticket
    Rasa-->>ActionServer: action_a2a
    ActionServer-->>A2AServer: I need reimbursement for my plane ticket
    A2AServer-->>ActionServer: {"message": "Could you please provide the date, amount, and business...", "state":"input-required"}
    ActionServer-->>Rasa: utter_message, slot_a2a_state=input-required
    Rasa-->>User: Could you please provide the date, amount, and business...
    User->>Rasa: It was Jan 1, $20, customer mtg
    Rasa-->>ActionServer: action_a2a
    ActionServer-->>A2AServer: It was Jan 1, $20, customer mtg
    A2AServer-->>ActionServer: {"message": "OK. I have reimbursed you for request ID...", "state":"completed"}
    ActionServer-->>Rasa: utter_message, slot_a2a_state=completed
    Rasa-->>User: OK. I have reimbursed you for request ID...
```

## A2A Integration

Google [announced](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/) the Agent2Agent protocol as a standardized method for agent interoperability. There is both [documentation](https://google.github.io/A2A/#/documentation) and a sample [repo](https://github.com/google/a2a-samples). A python quickstart can be found [here](https://google.github.io/A2A/#/tutorials/python/1_introduction). And a curated list of example A2A agents can be found [here](https://github.com/pab1it0/awesome-a2a).

We'll use a configuration file named `a2a.yml` which the action server will read to connect to all of the available A2A agents. For our demo agent, the configuration is:

```yml
remote_agents:
  - name: "Reimbursement Agent"
    url: http://localhost:10002
  - name: "Currency Agent"
    url: http://localhost:10000
```

### Run Sample Agents

This example uses two agents:

- Google ADK example expense reimbursement [agent](https://github.com/google/A2A/blob/main/samples/python/agents/google_adk/README.md)
- Langgraph currency exchange [agent](https://github.com/google/A2A/blob/main/samples/python/agents/langgraph/README.md)

To run the example agents, do the following from within the A2A repo in two terminals:

```sh
cd samples/python/agents/google_adk
echo "GOOGLE_API_KEY=your_api_key_here" > .env
uv run .
cd samples/python/agents/langgraph
echo "GOOGLE_API_KEY=your_api_key_here" > .env
uv run .
```

The agents should now be available at `http://localhost:10002` and `http://localhost:10000`.

## Kapa Notes

Kapa supports two API endpoints:

- `search`: Returns the top-n results from the Kapa vector store (no generative response from Kapa). The url for this endpoint is `https://api.kapa.ai/query/v1`.
- `chat`: Returns a generative response from the Kapa RAG

## Setup

The following enviroment variables need to be set to access the Kapa RAG's for Rasa and Kubernetes:

```sh
export KAPA_RASA_PROJECT_ID=
export KAPA_RASA_TOKEN=
export KAPA_RASA_NUM_RESULTS=5
export KAPA_K8S_PROJECT_ID=
export KAPA_K8S_TOKEN=
export KAPA_K8S_NUM_RESULTS=5
export KAPA_GEN_LLM="gpt-4o"
export RAG_TEMPLATE="prompts/rag_completion.jinja2"
```

### kapa.ai API TOKEN

In root folder of project, create a .env file:

```sh
# Environment Variables to define for the action server.
# file: .env
KAPA_PROJECT_ID="<You Can Find The Token in 1Passwd>"
KAPA_TOKEN="<You Can Find The Token in 1Passwd>"
```

### Train & run

```sh
pip install uv
uv pip install -r requirements.txt

rasa train --domain domain

rasa run actions --debug
rasa inspect
```

### Example A2A Agent Protocol

```log
======= Agent Card ========
{"name":"Currency Agent","description":"Helps with exchange rates for currencies","url":"http://localhost:10000/","version":"1.0.0","capabilities":{"streaming":true,"pushNotifications":true,"stateTransitionHistory":false},"defaultInputModes":["text","text/plain"],"defaultOutputModes":["text","text/plain"],"skills":[{"id":"convert_currency","name":"Currency Exchange Rates Tool","description":"Helps with exchange values between various currencies","tags":["currency conversion","currency exchange"],"examples":["What is exchange rate between USD and GBP?"]}]}
=========  starting a new task ======== 

What do you want to send to the agent? (:q or quit to exit): convert $175 AUD
========= streaming ======== 
stream event => {"jsonrpc":"2.0","id":"50f1cbde4d01483ca6c36ee6fe8629e9","result":{"id":"6534510a186243718f040d2454331587","status":{"state":"input-required","message":{"role":"agent","parts":[{"type":"text","text":"What currency would you like to convert AUD to? Also, do you have a specific date for the conversion you would like to use? If not, I can use the latest available exchange rate."}]},"timestamp":"2025-04-29T08:12:01.239330"},"final":true}}

What do you want to send to the agent? (:q or quit to exit): USD
========= streaming ======== 
stream event => {"jsonrpc":"2.0","id":"2efce7cc12ad41f8a8d8748c88897398","result":{"id":"6534510a186243718f040d2454331587","status":{"state":"working","message":{"role":"agent","parts":[{"type":"text","text":"Looking up the exchange rates..."}]},"timestamp":"2025-04-29T08:12:16.196794"},"final":false}}
stream event => {"jsonrpc":"2.0","id":"2efce7cc12ad41f8a8d8748c88897398","result":{"id":"6534510a186243718f040d2454331587","status":{"state":"working","message":{"role":"agent","parts":[{"type":"text","text":"Processing the exchange rates.."}]},"timestamp":"2025-04-29T08:12:17.034752"},"final":false}}
stream event => {"jsonrpc":"2.0","id":"2efce7cc12ad41f8a8d8748c88897398","result":{"id":"6534510a186243718f040d2454331587","status":{"state":"input-required","message":{"role":"agent","parts":[{"type":"text","text":"I can confirm that the current exchange rate from AUD to USD is 0.64059. Would you like me to calculate the estimated value of $175 AUD in USD using this exchange rate?"}]},"timestamp":"2025-04-29T08:12:18.940013"},"final":true}}
```

## ToDo

- Load agents on start of action server
- Support agent discovery via [MCP agent registry](https://github.com/google-a2a/a2a-samples/tree/main/samples%2Fpython%2Fagents%2Fa2a_mcp)
  - Extend a2a.yml to configure MCP agent registry and list of agents to be available via custom action
- Implement an MCP example via A2A
  - Changes
    - agent should query `/` to get `agent_card_url`
    - query `agent_card_url` to get the agent card and skill
    - skills endpoint: `/a2a/tasks/send`
  - Background
    - [python_a2a](https://github.com/themanojdesai/python-a2a)
    - [mcp examples](https://github.com/themanojdesai/python-a2a/tree/a7a15505ff7745513ebd20a8d13da7f0db68fed5/examples/mcp)
      - [basic agent with multiple skills](https://github.com/themanojdesai/python-a2a/blob/a7a15505ff7745513ebd20a8d13da7f0db68fed5/examples/mcp/mcp_agent.py)
- Improve Kapa integration
  - Include conversation history in RAG prompt so you can ask a follow-up question
  - Load docs in a json array that is processed by the jinja template
- Implement example as A2A
  - [Google example](https://github.com/google/A2A/blob/main/samples/python/agents/google_adk/README.md)
  - [orchestrator agent](https://github.com/google/A2A/blob/main/samples/python/hosts/multiagent/host_agent.py)
- Create a flow that handles "Rasa questions that require generative responses"
  - "Create a flow to deposit money in one of my bank accounts"

## Completed

- Update to latest `a2a-sdk`
- Add list available agents flow
