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
	if did[0:2] == "+1":
		pass
	elif did[0] == "1":
		did = "+" + did
	did = did.split("+1")
	if not did[0]:
		did = did[1:]
	did.sort()
	did = ','.join(did)

	if did:
	    if body:
	    	print(did, "text/plain", repr(body), sep="\t")
	    if is_mms and "included" in mms:
	    	for media in mms["included"]:
	    		media = media["attributes"]
	    		print(did, media["mime_type"], media["url"], sep="\t")
