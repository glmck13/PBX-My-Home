#!/usr/bin/env python3

import sys, os
import requests
from urllib.parse import parse_qs
from getenv import *

QUERY_STRING = os.getenv("QUERY_STRING", "")
if not QUERY_STRING and os.getenv("REQUEST_METHOD", "") != "GET":
    QUERY_STRING = sys.stdin.read().strip()

Fields = parse_qs(QUERY_STRING)
Token = Fields.get("token", [""])[0]
Contacts = Fields.get("contacts", [""])[0]
Text = Fields.get("text", [""])[0]

print("Content-Type: text/plain\n")

if Token not in TOKEN_ALLOW:
	exit()

msg = {}
msg["from"] = FLOWROUTE_DID
msg["body"] = Text
headers = {}
headers["Content-Type"] = "application/vnd.api+json"
for phone in Contacts.split(','):
	if len(phone) == 11:
		pass
	if len(phone) == 10:
		phone = '1' + phone
	else:
		continue
	msg["to"] = phone
	rsp = requests.post(FLOWROUTE_URL, auth=(FLOWROUTE_KEY, FLOWROUTE_SECRET), headers=headers, json=msg).json()
	print(rsp)
