# -*- coding: utf-8 -*-
"""
You can create a file called `.env` in the root of the repo, containing your local env vars.
It will be automatically loaded when starting the action server.
"""
from dotenv import load_dotenv

# Load environment variables
# needs to happen before anything else (to properly instantiate constants)
load_dotenv(verbose=True, override=True)

import os

kapa_api_token_internal = os.environ.get("KAPA_API_TOKEN_INTERNAL", "")
kapa_api_token_external_docsbot = os.environ.get("KAPA_API_TOKEN_EXTERNAL_DOCSBOT", "")
kapa_api_token_external_mainbot = os.environ.get("KAPA_API_TOKEN_EXTERNAL_MAINBOT", "")
