#!/usr/bin/env python3

import os, sys
import json
import subprocess

PBXMYHOME = "pbxmyhome"
FWRULES = [
	{"type": "v4", "protocol": "tcp", "subnet" : "0.0.0.0", "size": "0", "port": "22"},
	{"type": "v4", "protocol": "tcp", "subnet" : "0.0.0.0", "size": "0", "port": "80"},
	{"type": "v4", "protocol": "tcp", "subnet" : "0.0.0.0", "size": "0", "port": "443"},
	{"type": "v4", "protocol": "tcp", "subnet" : "0.0.0.0", "size": "0", "port": "3478"},
	{"type": "v4", "protocol": "tcp", "subnet" : "0.0.0.0", "size": "0", "port": "8089"},
	{"type": "v4", "protocol": "tcp", "subnet" : "0.0.0.0", "size": "0", "port": "5060"},
	{"type": "v4", "protocol": "tcp", "subnet" : "0.0.0.0", "size": "0", "port": "5061"},
	{"type": "v4", "protocol": "udp", "subnet" : "0.0.0.0", "size": "0", "port": "3478"},
	{"type": "v4", "protocol": "udp", "subnet" : "0.0.0.0", "size": "0", "port": "10000:20000"},
]

env = os.environ.copy()
if not env.get("VULTR_API_KEY"):
	print("VULTR_API_KEY not set!", file=sys.stderr)
	exit()

#
# Get the SSH public key for this desktop
#
rsp = subprocess.run(["ls", "-1", env["HOME"] + "/.ssh"], env=env, capture_output=True, text=True)
flist = rsp.stdout.split('\n')
public_key = ""
for fn in flist:
	if ".pub" in fn:
		with open(env["HOME"] + "/.ssh/" + fn, "r") as fd:
			public_key = fd.read().strip()
if not public_key:
	print("No SSH public key found!", file=sys.stderr)
	exit()

#
# Upload SSH key
#
rsp = subprocess.run(["vultr-cli", "-o", "json", "ssh-key", "list"], env=env, capture_output=True, text=True)
for x in json.loads(rsp.stdout)["ssh_keys"]:
	if x["name"] == PBXMYHOME:
		ssh_id = x["id"]
		print("Found SSH key: {}".format(ssh_id))
		break
else:
	rsp = subprocess.run(["vultr-cli", "-o", "json", "ssh-key", "create",
		"--name=" + PBXMYHOME, "--key=" + public_key], env=env, capture_output=True, text=True)
	if rsp.stderr:
		print(rsp.stderr, file=sys.stderr)
		exit()
	else:
		ssh_id = json.loads(rsp.stdout)["ssh_key"]["id"]
		print("Created SSH key: {}".format(ssh_id))

#
# Create firewall group
#
rsp = subprocess.run(["vultr-cli", "-o", "json", "firewall", "group", "list"], env=env, capture_output=True, text=True)
for x in json.loads(rsp.stdout)["firewall_groups"]:
	if x["description"] == PBXMYHOME:
		fw_id = x["id"]
		print("Found firewall group: {}".format(fw_id))
		break
else:
	rsp = subprocess.run(["vultr-cli", "-o", "json", "firewall", "group", "create", "--description=" + PBXMYHOME], env=env, capture_output=True, text=True)
	if rsp.stderr:
		print(rsp.stderr, file=sys.stderr)
		exit()
	else:
		fw_id = json.loads(rsp.stdout)["firewall_group"]["id"]
		print("Created firewall group: {}".format(fw_id))
		for x in FWRULES:
			rsp = subprocess.run(["vultr-cli", "firewall", "rule", "create", fw_id,
				"--ip-type=" + x["type"], "--protocol=" + x["protocol"], "--subnet=" + x["subnet"], "--size=" + x["size"], "--port=" + x["port"]],
				env=env, capture_output=True, text=True)
			if rsp.stderr:
				print(rsp.stderr, file=sys.stderr)
				exit()
			else:
				print(rsp.stdout)

#
# Create instance
#
rsp = subprocess.run(["vultr-cli", "-o", "json", "instance", "list"], env=env, capture_output=True, text=True)
for x in json.loads(rsp.stdout)["instances"]:
	if x["label"] == PBXMYHOME:
		vps_id = x["id"]
		print("Found VPS: {}".format(vps_id))
		break
else:
	rsp = subprocess.run(["vultr-cli", "instance", "create",
		"--plan=vc2-1c-1gb", "--os=2136", "--region=atl", "--auto-backup=false", "--ddos=false",
		"--firewall-group=" + fw_id, "--ssh-keys=" + ssh_id, "--label=" + PBXMYHOME], env=env, capture_output=True, text=True)
	if rsp.stderr:
		print(rsp.stderr, file=sys.stderr)
		exit()
	else:
		print(rsp.stdout)
