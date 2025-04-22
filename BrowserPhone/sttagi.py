#!/usr/bin/env python3

import sys, os

#AGIVARS = sys.stdin.read()
INFILE = sys.argv[1]
if len(sys.argv) > 2:
	LANG = sys.argv[2]
else:
	LANG = "en"
FORMAT = INFILE.rsplit('.', 1)[1]
BASE = INFILE[:-len(FORMAT)-1]

os.environ["OPENAI_API_KEY"] = ""
from openai import OpenAI
client = OpenAI()

with open(INFILE, "rb") as f:
    transcript = client.audio.transcriptions.create(model="whisper-1", language=LANG, response_format="text", file=f)

with open(BASE + ".txt", "w") as f:
    f.write(transcript)
