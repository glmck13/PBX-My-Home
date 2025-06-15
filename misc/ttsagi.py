#!/usr/bin/env python3

import sys, os

#AGIVARS = sys.stdin.read()
INTEXT = sys.argv[1]
OUTFILE = sys.argv[2]
if len(sys.argv) > 3:
	LANG = sys.argv[3]
else:
	LANG = "en"
FORMAT = OUTFILE.rsplit('.', 1)[1]

VOICES = {"en" : "Stephen", "es" : "Lupe", "ai" : "onyx"}

if LANG == "ai":
	os.environ["OPENAI_API_KEY"] = ""
	from openai import OpenAI
	client = OpenAI()
	audio = client.audio.speech.create(model="tts-1", voice=VOICES[LANG], response_format=FORMAT, input=INTEXT)
	audio.stream_to_file(OUTFILE)
else:
	from boto3 import Session
	client = Session().client("polly")
	INTEXT = '<speak><prosody volume="x-loud">{}</prosody></speak>'.format(INTEXT)
	audio = client.synthesize_speech(Text=INTEXT, TextType="ssml", Engine="neural", SampleRate="16000", OutputFormat=FORMAT, VoiceId=VOICES[LANG])
	with open(OUTFILE, "wb") as f:
		f.write(audio["AudioStream"].read())
