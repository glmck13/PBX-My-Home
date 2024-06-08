import os

MSGAPP_MYURL = "{}://{}/cdn".format(os.getenv("REQUEST_SCHEME", "https"), os.getenv("SERVER_NAME", "localhost"))
MSGAPP_MYCDN = "{}/cdn".format(os.getenv("DOCUMENT_ROOT", "/tmp"))
MSGAPP_BACKEND = "SXMO"
MSGAPP_SENDAPI = "http://mysite.local:8000/cgi-bin/sxmo_sendapi.py"
MSGAPP_DID = "+13015551212"
MSGAPP_A2PID = ""
MSGAPP_A2PHONE = ""
MSGAPP_KEY = "dummy"
MSGAPP_SECRET = "dummy"
TOKEN_ALLOW = []
