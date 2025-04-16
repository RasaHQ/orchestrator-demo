# Enterprise Search Example Prompt

Given the following information, please provide an answer based on the provided documents and the context of the recent conversation.
If the answer is not known or cannot be determined from the provided documents or context, please state that you do not know to the user.

### Relevant Documents
Use the following documents to answer the question:

1. {'answer': '# Product Development > Rasa Studio  > Untitled > Untitled > Config In Studio Scenarios > Should be able to export config.yml and endpoints.yml as part of Rasa CLI download\n\n**Properties**\n\nAssignee: @Masha Klimkin, @Marko Rankovic \n\nComments: ✅\xa0- Marko\n\nAutomation Status:\n# Product Development > Rasa Studio  > Untitled > Untitled > Config In Studio Scenarios > Should be able to import config.yml and endpoints.yml to Studio as part of Rasa CLI upload\n\n**Properties**\n\nAssignee: @Marko Rankovic, @Masha Klimkin \n\nComments: ✅\xa0- Marko\n\nAutomation Status: \n\n\nCLI Command `rasa studio upload`\n\nUse `rasa studio upload —help` to look at additional CLI arguments and test them\n# Product Development > Rasa Studio  > Untitled > Untitled > Config In Studio Scenarios > User should be able to update the default config.yml\n\n**Properties**\n\nAssignee: @Marko Rankovic \n\nComments: ✅\xa0- Marko |  - only developer should be able to see and update assistant settings\n\nAutomation Status: Automated\n# Multiple Variants [very WIP]\n\nvariants:\n    wa-usa-en:\n        nlu: [&#x27;data/usa/en/nlu.yml&#x27;]  # array of single files\n        rules: [&#x27;data/rules.yml&#x27;] # array of single files\n        stories: [&#x27;data/stories.yml&#x27;] # array of single files\n        config: &#x27;config.yml&#x27;  # config is always a single file\n        domain: [&#x27;domain.yml&#x27;] # array of file(s) or folder(s)\n        models: &#x27;models/&#x27;  # single file or folder - here single folder means latest model for main-bot used - model name will be generated from bot name\n        actions: &#x27;actions/&#x27; # single folder\n        # test_data is used for test stories, but our customers can put anything under this folder (cf. NIB)\n        test_data: [&#x27;tests/&#x27;] # array of folder(s)\n        train_test_split: &#x27;train_test_split/&#x27; # single folder\n        results: &#x27;results/&#x27; # single folder provided to --out arg\n    wa-usa-es:\n        nlu: [&#x27;data/usa/es/nlu*.yml&#x27;] # array of single files\n        rules: [&#x27;data/rules.yml&#x27;] # array of single files\n        config: &#x27;config-es.yml&#x27;\n        domain: [&#x27;domain.yml&#x27;]\n        models: &#x27;models-more-skills/constant-name-for-bot.tar.gz&#x27; # single model trained and loaded\n        test_data: [&#x27;tests/&#x27;, &#x27;tests-more-skills/&#x27;]\n        credentials: &#x27;credentials-more-skills.yml&#x27; # overrides global one\n        endpoints: &#x27;endpoints-more-skills.yml&#x27;\n\n the following is moved from `config.yml`\n https://rasa.com/docs/rasa/training-data-importers\nimporters:\n    - name: &quot;module.CustomImporter&quot;\n      parameter1: &quot;value&quot;\n      parameter2: &quot;value2&quot;\n    - name: &quot;RasaFileImporter&quot;\n```\n# Multiple Variants [very WIP]\n\nvariants:\n    wa-usa-en:\n        nlu: [&#x27;data/usa/en/nlu.yml&#x27;]  # array of single files\n        rules: [&#x27;data/rules.yml&#x27;] # array of single files\n        stories: [&#x27;data/stories.yml&#x27;] # array of single files\n        config: &#x27;config.yml&#x27;  # config is always a single file\n        domain: [&#x27;domain.yml&#x27;] # array of file(s) or folder(s)\n        models: &#x27;models/&#x27;  # single file or folder - here single folder means latest model for main-bot used - model name will be generated from bot name\n        actions: &#x27;actions/&#x27; # single folder\n        # test_data is used for test stories, but our customers can put anything under this folder (cf. NIB)\n        test_data: [&#x27;tests/&#x27;] # array of folder(s)\n        train_test_split: &#x27;train_test_split/&#x27; # single folder\n        results: &#x27;results/&#x27; # single folder provided to --out arg\n    wa-usa-es:\n        nlu: [&#x27;data/usa/es/nlu*.yml&#x27;] # array of single files\n        rules: [&#x27;data/rules.yml&#x27;] # array of single files\n        config: &#x27;config-es.yml&#x27;\n        domain: [&#x27;domain.yml&#x27;]\n        models: &#x27;models-more-skills/constant-name-for-bot.tar.gz&#x27; # single model trained and loaded\n        test_data: [&#x27;tests/&#x27;, &#x27;tests-more-skills/&#x27;]\n        credentials: &#x27;credentials-more-skills.yml&#x27; # overrides global one\n        endpoints: &#x27;endpoints-more-skills.yml&#x27;\n\n the following is moved from `config.yml`\n https://rasa.com/docs/rasa/training-data-importers\nimporters:\n    - name: &quot;module.CustomImporter&quot;\n      parameter1: &quot;value&quot;\n      parameter2: &quot;value2&quot;\n    - name: &quot;RasaFileImporter&quot;\n```\n# Overview\n## Solution 1 (only import/export)\n\n- We keep all config in the config file and endpoint.yml file, there will be no UI for configuration (only for reading)\n\n- We store all the config in our database so that we can export config.yml and endpoint.yml during export\n\n- Support import of config.yml and endpoint.yml \n\n- Display the config file and endpoint in the UI\n\n- If user creates new assistant in Studio, they see the default config.\n\n**Pros**\n\n- minimal effort from UI perspective\n\n- there’s a reliable audit tracking and RBAC in Git for changes in config and endpoint so less risk seen\n\n**Cons**\n\n- non tech users and technical users can’t work in the same platform ⇒ added steps, prolong duration between change and result observed\n\n- testing can only be done outside of Studio ⇒ we’re driving people away from Studio and doesn’t provide a way for them to come back\n# Product Development > Tribes & Squads > Untitled > Active ProdDev Projects > [Q3 WIP] Skills > Studio Structure Today (Download)\n\n**Properties**\n\n\n\n```yaml\n|____endpoints.yml\n|____config.yml\n|____domain.yml\n|____data\n| |____flows.yml\n| |____nlu.yml\n\n```\n# Overview\n## Solution 2 (with UI)\n\n- We&#x27;ll surface the Config as 2 editable .yml text fields (config.yml and endpoints.yml) in the Advanced Settings section of the Manage Assistant. \n\n\t- **New Assistant Creation: **When a new assistant is created in Rasa, the default configuration is automatically populated in the corresponding field.\n\n\t- **Existing Assistant****: **For users with existing assistants created before this feature implementation, the default configuration will be provided in the field. Users can customize this default configuration by copying, pasting, or rewriting it directly.\n\n\t- **Imported Assistant: **If a user imports an assistant into Rasa, the configuration field is pre-filled not with the default but with the imported configuration.\n\n- We store config file and endpoint files in our database as texts so that we can export config.yml and endpoint.yml during export\n\n**Pros**\n\n- Not much UI effort: we add a field into Create/Manage Assistant window + validation\n\n- Users will be able to edit config in Studio UI\n\n**Cons**\n\n- Only technical users will be able to understand and edit config, as it’s in raw .yml\n\n- Added work on validation: We’ll either need to think how to validate Config in Studio or somehow validate it with Pro. With Upload server and no editing in Studio, validation would always be on Pro side.\n\n- Added work on audit trail: what will users see in logs? Just that someone has edited Config or which particular field was edited\n\n\n\n\n☝ In both solutions, we’ll need to consider removing the editable field of action server URL and the dropdown for LLM model from the Manage Assistant window. Otherwise, we might create conflicts between Studio UI and config/endpoint files.\n\n📌 **Winner: Solution 2**', 'source_url': 'https://www.notion.so/Should-be-able-to-export-config-yml-and-endpoints-yml-as-part-of-Rasa-CLI-download-cd13780f9a8f4322a0b3957f699dc2e9', 'title': 'Product Development > Rasa Studio  > Untitled > Untitled > Config In Studio Scenarios > Should be able to export config.yml and endpoints.yml as part of Rasa CLI download|Product Development > Rasa Studio  > Untitled > Untitled > Config In Studio Scenarios > Should be able to export config.yml and endpoints.yml as part of Rasa CLI download', 'source_type': 'Notion'}
# Product Development > Rasa Studio  > Untitled > Untitled > Config In Studio Scenarios > Should be able to export config.yml and endpoints.yml as part of Rasa CLI download

**Properties**

Assignee: @Masha Klimkin, @Marko Rankovic 

Comments: ✅ - Marko

Automation Status:
# Product Development > Rasa Studio  > Untitled > Untitled > Config In Studio Scenarios > Should be able to import config.yml and endpoints.yml to Studio as part of Rasa CLI upload

**Properties**

Assignee: @Marko Rankovic, @Masha Klimkin 

Comments: ✅ - Marko

Automation Status: 


CLI Command `rasa studio upload`

Use `rasa studio upload —help` to look at additional CLI arguments and test them
# Product Development > Rasa Studio  > Untitled > Untitled > Config In Studio Scenarios > User should be able to update the default config.yml

**Properties**

Assignee: @Marko Rankovic 

Comments: ✅ - Marko |  - only developer should be able to see and update assistant settings

Automation Status: Automated
# Multiple Variants [very WIP]

variants:
    wa-usa-en:
        nlu: [&#x27;data/usa/en/nlu.yml&#x27;]  # array of single files
        rules: [&#x27;data/rules.yml&#x27;] # array of single files
        stories: [&#x27;data/stories.yml&#x27;] # array of single files
        config: &#x27;config.yml&#x27;  # config is always a single file
        domain: [&#x27;domain.yml&#x27;] # array of file(s) or folder(s)
        models: &#x27;models/&#x27;  # single file or folder - here single folder means latest model for main-bot used - model name will be generated from bot name
        actions: &#x27;actions/&#x27; # single folder
        # test_data is used for test stories, but our customers can put anything under this folder (cf. NIB)
        test_data: [&#x27;tests/&#x27;] # array of folder(s)
        train_test_split: &#x27;train_test_split/&#x27; # single folder
        results: &#x27;results/&#x27; # single folder provided to --out arg
    wa-usa-es:
        nlu: [&#x27;data/usa/es/nlu*.yml&#x27;] # array of single files
        rules: [&#x27;data/rules.yml&#x27;] # array of single files
        config: &#x27;config-es.yml&#x27;
        domain: [&#x27;domain.yml&#x27;]
        models: &#x27;models-more-skills/constant-name-for-bot.tar.gz&#x27; # single model trained and loaded
        test_data: [&#x27;tests/&#x27;, &#x27;tests-more-skills/&#x27;]
        credentials: &#x27;credentials-more-skills.yml&#x27; # overrides global one
        endpoints: &#x27;endpoints-more-skills.yml&#x27;

 the following is moved from `config.yml`
 https://rasa.com/docs/rasa/training-data-importers
importers:
    - name: &quot;module.CustomImporter&quot;
      parameter1: &quot;value&quot;
      parameter2: &quot;value2&quot;
    - name: &quot;RasaFileImporter&quot;
```
# Multiple Variants [very WIP]

variants:
    wa-usa-en:
        nlu: [&#x27;data/usa/en/nlu.yml&#x27;]  # array of single files
        rules: [&#x27;data/rules.yml&#x27;] # array of single files
        stories: [&#x27;data/stories.yml&#x27;] # array of single files
        config: &#x27;config.yml&#x27;  # config is always a single file
        domain: [&#x27;domain.yml&#x27;] # array of file(s) or folder(s)
        models: &#x27;models/&#x27;  # single file or folder - here single folder means latest model for main-bot used - model name will be generated from bot name
        actions: &#x27;actions/&#x27; # single folder
        # test_data is used for test stories, but our customers can put anything under this folder (cf. NIB)
        test_data: [&#x27;tests/&#x27;] # array of folder(s)
        train_test_split: &#x27;train_test_split/&#x27; # single folder
        results: &#x27;results/&#x27; # single folder provided to --out arg
    wa-usa-es:
        nlu: [&#x27;data/usa/es/nlu*.yml&#x27;] # array of single files
        rules: [&#x27;data/rules.yml&#x27;] # array of single files
        config: &#x27;config-es.yml&#x27;
        domain: [&#x27;domain.yml&#x27;]
        models: &#x27;models-more-skills/constant-name-for-bot.tar.gz&#x27; # single model trained and loaded
        test_data: [&#x27;tests/&#x27;, &#x27;tests-more-skills/&#x27;]
        credentials: &#x27;credentials-more-skills.yml&#x27; # overrides global one
        endpoints: &#x27;endpoints-more-skills.yml&#x27;

 the following is moved from `config.yml`
 https://rasa.com/docs/rasa/training-data-importers
importers:
    - name: &quot;module.CustomImporter&quot;
      parameter1: &quot;value&quot;
      parameter2: &quot;value2&quot;
    - name: &quot;RasaFileImporter&quot;
```
# Overview
## Solution 1 (only import/export)

- We keep all config in the config file and endpoint.yml file, there will be no UI for configuration (only for reading)

- We store all the config in our database so that we can export config.yml and endpoint.yml during export

- Support import of config.yml and endpoint.yml 

- Display the config file and endpoint in the UI

- If user creates new assistant in Studio, they see the default config.

**Pros**

- minimal effort from UI perspective

- there’s a reliable audit tracking and RBAC in Git for changes in config and endpoint so less risk seen

**Cons**

- non tech users and technical users can’t work in the same platform ⇒ added steps, prolong duration between change and result observed

- testing can only be done outside of Studio ⇒ we’re driving people away from Studio and doesn’t provide a way for them to come back
# Product Development > Tribes & Squads > Untitled > Active ProdDev Projects > [Q3 WIP] Skills > Studio Structure Today (Download)

**Properties**



```yaml
|____endpoints.yml
|____config.yml
|____domain.yml
|____data
| |____flows.yml
| |____nlu.yml

```
# Overview
## Solution 2 (with UI)

- We&#x27;ll surface the Config as 2 editable .yml text fields (config.yml and endpoints.yml) in the Advanced Settings section of the Manage Assistant. 

        - **New Assistant Creation: **When a new assistant is created in Rasa, the default configuration is automatically populated in the corresponding field.

        - **Existing Assistant****: **For users with existing assistants created before this feature implementation, the default configuration will be provided in the field. Users can customize this default configuration by copying, pasting, or rewriting it directly.

        - **Imported Assistant: **If a user imports an assistant into Rasa, the configuration field is pre-filled not with the default but with the imported configuration.

- We store config file and endpoint files in our database as texts so that we can export config.yml and endpoint.yml during export

**Pros**

- Not much UI effort: we add a field into Create/Manage Assistant window + validation

- Users will be able to edit config in Studio UI

**Cons**

- Only technical users will be able to understand and edit config, as it’s in raw .yml

- Added work on validation: We’ll either need to think how to validate Config in Studio or somehow validate it with Pro. With Upload server and no editing in Studio, validation would always be on Pro side.

- Added work on audit trail: what will users see in logs? Just that someone has edited Config or which particular field was edited




☝ In both solutions, we’ll need to consider removing the editable field of action server URL and the dropdown for LLM model from the Manage Assistant window. Otherwise, we might create conflicts between Studio UI and config/endpoint files.

📌 **Winner: Solution 2**



### Slots or Variables
Here are the variables of the currently active conversation which may be used to answer the question:
- name: language, value: en, type: strict_categorical
- name: silence_timeout, value: 6.0, type: float
- name: consecutive_silence_timeouts, value: 0.0, type: float
- name: which_bot, value: external, type: categorical



### Current Conversation
Transcript of the current conversation, use it to determine the context of the question:
USER: what is the config.yml

Based on the above, please formulate an answer to the question or request in the user's last message. 
It is important that you ensure the answer is grounded in the provided documents and conversation context. 
Avoid speculating or making assumptions beyond the given information and keep your answers short, 2 to 3 sentences at most.