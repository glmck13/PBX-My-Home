#!/usr/bin/env python3

import sys, os
from boto3 import Session
from openai import OpenAI

#AGIVARS = sys.stdin.read()
INFILE = sys.argv[1]
SUFFIX = sys.argv[2]
XLATE = sys.argv[3].split('-')
FORMAT = SUFFIX.rsplit('.', 1)[1]
BASE = INFILE.rsplit('.', 1)[0]
INLANG = XLATE[0]
OUTLANG = XLATE[1]
VOICES = {"en" : "Stephen", "es" : "Lupe"}

os.environ["OPENAI_API_KEY"] = ""

client = OpenAI()
with open(INFILE, "rb") as f:
    transcript = client.audio.transcriptions.create(model="whisper-1", language=INLANG, response_format="text", file=f)
with open(BASE + "-" + INLANG + ".txt", "w") as f:
	f.write(transcript)

client = Session().client("translate")
result = client.translate_text(Text=transcript, SourceLanguageCode=INLANG, TargetLanguageCode=OUTLANG)
translation = result.get('TranslatedText')
with open(BASE + "-" + OUTLANG + ".txt", "w") as f:
	f.write(translation)

client = Session().client("polly")
translation = '<speak><prosody volume="x-loud" rate="slow">{}</prosody></speak>'.format(translation)
result = client.synthesize_speech(Text=translation, TextType="ssml", Engine="neural", SampleRate="16000", OutputFormat=FORMAT, VoiceId=VOICES[OUTLANG])
with open(BASE + "-" + SUFFIX, "wb") as f:
	f.write(result["AudioStream"].read())
