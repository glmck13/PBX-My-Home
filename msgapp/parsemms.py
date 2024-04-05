#!/usr/bin/env python3

import sys, os
import json

mms = json.loads(sys.stdin.read())
what = mms["data"]["type"]

if what == "message":
	data = mms["data"]["attributes"]
	is_mms = data["is_mms"]
	body = data["body"]

	did = data["from"]
	if did[0] == "1":
		did = did[1:]
	elif did[0:2] == "+1":
		did = did[2:]

	if did:
	    if body:
	    	print(did, "text/plain", body, sep="\t")
	    if is_mms:
	    	for media in mms["included"]:
	    		media = media["attributes"]
	    		print(did, media["mime_type"], media["url"], sep="\t")
