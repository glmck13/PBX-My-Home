#!/usr/bin/env python3

import sys, os
import json
import requests
import mimetypes
import subprocess
import urllib3
urllib3.disable_warnings()

print("Content-Type: text/plain\n", flush=True)

#print(os.environ, file=sys.stderr)

req = json.loads(sys.stdin.read(int(os.environ.get("CONTENT_LENGTH", "0"))))
print(req, file=sys.stderr)
req = req["data"]["attributes"]

is_mms = req["is_mms"]
distro = req["to"]
media_urls = req["media_urls"]
media_files = []

if len(distro) > 0 and len(media_urls) > 0:

	for url in media_urls:
		rsp = requests.get(url, verify=False)
		fname = "{}/{}".format(os.environ.get("SXMO_TMPDIR", "/tmp"), url.split('/')[-1])
		media_files.append(fname)
		with open(fname, "wb") as fid:
			fid.write(rsp.content)

	if is_mms or len(distro) > 1:
		cmd = ["mmsctl", "-S"]
		for r in distro:
			cmd.extend(["-r", r])
		for u in media_files:
			if u.split('.')[-1] == "txt":
				cmd.extend(["-a", u, "-c", "text/plain"])
			else:
				cmd.extend(["-a", u, "-c", mimetypes.guess_type(u)[0]])
	else:
		cmd = ["sxmo_sendsms.sh", distro[0], media_files[0]]

	print(' '.join(cmd))
	result = subprocess.run(cmd, capture_output=True, text=True)
	print(result.stdout, result.stderr)

	cmd = ["rm", "-f"]
	cmd.extend(media_files)
	subprocess.run(cmd)
