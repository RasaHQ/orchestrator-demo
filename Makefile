SHELL := /bin/bash

rasa-train:
	@rasa train --domain domain/ 

rasa-test:
	@rasa test e2e e2e_tests

rasa-run:
	@rasa run --enable-api --cors "*"

rasa-run-debug:
	@rasa run --enable-api --cors "*" --debug 

rasa-run-actions:
	@rasa run actions

rasa-run-actions-debug:
	@rasa run actions --debug