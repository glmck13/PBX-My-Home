#!/usr/bin/env python3

import sys, os
import json

mms = json.loads(sys.stdin.read())
what = mms["data"]["type"]

if what == "message":
	data = mms["data"]["attributes"]
	is_mms = data["is_mms"]
	body = data["body"]

	did = data.get("from", "")
	if did[0:2] == "+1":
		did = did[2:]
	elif did[0] == "1":
		did = did[1:]

	dest = data.get("to", "+1")
	if dest[0:2] == "+1":
		pass
	elif dest[0] == "1":
		dest = "+" + dest
	dest = dest.split("+1")
	if not dest[0]:
		dest = dest[1:]
	dest.sort()
	dest = ','.join(dest)

	if did:
	    if body:
	    	print(did, dest, "body/plain", repr(body), sep="\t")
	    if is_mms and "included" in mms:
	    	for media in mms["included"]:
	    		media = media["attributes"]
	    		print(did, dest, media["mime_type"], media["url"], sep="\t")
