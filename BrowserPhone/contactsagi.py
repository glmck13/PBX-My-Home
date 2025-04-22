#!/usr/bin/env python3

import sys, os

#AGIVARS = sys.stdin.read()
CONTACTS = sys.argv[1]

PHONEBOOK = [
	{"name" : "Name", "address" : "user@email.local"}
]

names = set()
addresses = set()

for c in CONTACTS:
	if c.isdigit():
		n = int(c)-1
		if n >= 0 and n < len(PHONEBOOK):
			names.add(PHONEBOOK[n]["name"])
			addresses.add(PHONEBOOK[n]["address"])

if addresses:
	print('SET VARIABLE CONTACTS_RSP "You want to send a message to {}, right?"'.format(', and '.join(names)))
else:
	print('SET VARIABLE CONTACTS_RSP "I didn\'t find any names. Try again."')

print('SET VARIABLE CONTACTS_LIST "{}"'.format(','.join(addresses)))
print('SET VARIABLE RECORDED_FILE /tmp/tts{}'.format(os.getpid()))
