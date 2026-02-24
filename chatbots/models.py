#!/usr/bin/env python3

import os
from google import genai

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

print(f"{'Model Name':<40} | {'Supports Live API?'}")
print("-" * 65)

for model in client.models.list():
    is_live_capable = 'bidiGenerateContent' in model.supported_actions
    if is_live_capable:
        print(f"{model.name:<40} | YES")
