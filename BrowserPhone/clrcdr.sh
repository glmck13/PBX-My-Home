DBUSER=freepbxuser
DBPASS=''
mysql -u $DBUSER -p$DBPASS -e "USE asteriskcdrdb; TRUNCATE TABLE cdr"
