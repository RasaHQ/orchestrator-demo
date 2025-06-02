# Create A2A Agents

Create an A2A server that has two agents with the following agent cards. The A2A protocol supports both synchronous request/response and asynchronous streaming (e.g., via Server-Sent Events for sendSubscribe) and this server should support these.

## Health Insurance Quote Agent

The agent card should be available at:

The agent card should be available at: /insurance/.well-known/agent.json
The async streaming interface should be at: /insurance/tasks/sendSubscribe

{"name":"Insurance Quote Agent","description":"This agent provides health insurance quotes by calling a dedicated API.","url":"http://localhost:10003/","version":"1.0.0","capabilities":{"streaming":true,"pushNotifications":false,"stateTransitionHistory":false},"defaultInputModes":["text","text/plain"],"defaultOutputModes":["text","text/plain"],"skills":[{"id":"get_insurance_quote","name":"Get Insurance Quote","description":"Fetches health insurance quotes for individuals, couples, or families.","tags":["insurance","quotes","health"],"examples":["Can you get me a health insurance quote?","I need a quote for a couple, both residents, born 1990-01-01 and 1992-02-02"]}]}

It should accept the following parameters:
- Policy type: individual, couple, family, single parent family
- Residency: resident, international student, international worker
- Primary policyholder birthdate
- Partner birthdate (if it's a couple or family policy type)

The API will return a list of policy names and the monthly cost. Policy names will be: Basic, Bronze, Silver & Gold. Create a separate function to calculate an arbitrary price.

## Expense Reimbursement Agent

The agent card should be available at: /reimbursement/.well-known/agent.json
The async streaming interface should be at: /reimbursement/tasks/sendSubscribe

        skill = AgentSkill(
            id='process_reimbursement',
            name='Process Reimbursement Tool',
            description='Helps with the reimbursement process for users given the amount and purpose of the reimbursement.',
            tags=['reimbursement'],
            examples=[
                'Can you reimburse me $20 for my lunch with the clients?'
            ],
        )
        agent_card = AgentCard(
            name='Reimbursement Agent',
            description='This agent handles the reimbursement process for the employees given the amount and purpose of the reimbursement.',
            url=f'http://{host}:{port}/',
            version='1.0.0',
            defaultInputModes=['text', 'text/plain'],
            defaultOutputModes=['text', 'text/plain'],
            capabilities=AgentCapabilities(streaming=True),
            skills=[skill],
        )