#!/bin/bash

# /etc/freepbx.conf
DBUSER='freepbxuser'
DBPASS=''
mysql -u $DBUSER -p$DBPASS -e "USE asteriskcdrdb; TRUNCATE TABLE cdr"

echo -e "Content-Type: text/plain\n"
echo "CDR table cleared!"
