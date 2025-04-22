#!/usr/bin/env python3

import sys, smtplib, ssl
from email.message import EmailMessage

#AGIVARS = sys.stdin.read()
INFILE = sys.argv[1]
CALLERID = sys.argv[2]
CONTACTS = sys.argv[3]

SMTP_FROM = ""
SMTP_KEY = ""
SMTP_SERVER = ""
SMTP_PORT = 465

eml = EmailMessage()
eml['Subject'] = CALLERID
eml['From'] = SMTP_FROM
eml['To'] = CONTACTS

with open(INFILE + ".txt") as fp:
	eml.set_content(fp.read().encode("utf-8").decode("unicode_escape"))

with open(INFILE + ".mp3", 'rb') as fp:
	eml.add_attachment(fp.read(), maintype="audio", subtype="mpeg", filename="audio.mp3")

context = ssl.create_default_context()
with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
	server.login(SMTP_FROM, SMTP_KEY)
	server.send_message(eml)
