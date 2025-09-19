#!/bin/bash

#
# Update OS
#
apt-get update
apt-get upgrade
apt-get install default-libmysqlclient-dev expect ffmpeg htop ipset lame libasound2-dev libcurl4-openssl-dev libical-dev libicu-dev libjansson-dev libncurses5-dev libneon27-dev libnewt-dev libogg-dev libspandsp-dev libsqlite3-dev libsrtp2-dev libssl-dev libtool-bin libvorbis-dev libxml2-dev linux-headers-`uname -r` mariadb-client mariadb-server mpg123 nodejs npm odbc-mariadb php-pear php-soap php8.2 php8.2-cli php8.2-common php8.2-curl php8.2-gd php8.2-intl php8.2-mbstring php8.2-mysql php8.2-xml python-dev-is-python3 sngrep software-properties-common sox sqlite3 subversion unixodbc unixodbc-dev uuid uuid-dev

#
# Add extras
#
apt-get install ksh coturn iptables-persistent snapd
snap install --classic certbot
ln -s /snap/bin/certbot /usr/bin/certbot
timedatectl set-timezone America/New_York

echo -n "Reboot (y/n)? "; read x
if [ "$x" = "y" ]; then
	reboot
	read x
fi

#
# Install Asterisk
#
cd /usr/src
wget http://downloads.asterisk.org/pub/telephony/asterisk/asterisk-22-current.tar.gz
tar xvf asterisk-22-current.tar.gz
cd asterisk-22*/
contrib/scripts/get_mp3_source.sh
contrib/scripts/install_prereq install
./configure --libdir=/usr/lib64 --with-pjproject-bundled --with-jansson-bundled
make menuselect.makeopts
menuselect/menuselect --enable app_macro menuselect.makeopts
make menuselect
make
make install
make samples
make config
ldconfig

groupadd asterisk
useradd -r -d /var/lib/asterisk -g asterisk asterisk
usermod -aG audio,dialout asterisk
chown -R asterisk:asterisk /etc/asterisk
chown -R asterisk:asterisk /var/{lib,log,spool}/asterisk
chown -R asterisk:asterisk /usr/lib64/asterisk

sed -i 's|#AST_USER|AST_USER|' /etc/default/asterisk
sed -i 's|#AST_GROUP|AST_GROUP|' /etc/default/asterisk
sed -i 's|;runuser|runuser|' /etc/asterisk/asterisk.conf
sed -i 's|;rungroup|rungroup|' /etc/asterisk/asterisk.conf
echo "/usr/lib64" >> /etc/ld.so.conf.d/asterisk.conf
ldconfig

#
# Configure Apache web server
#
sed -i 's/\(^upload_max_filesize = \).*/\120M/' /etc/php/8.2/apache2/php.ini
sed -i 's/\(^memory_limit = \).*/\1256M/' /etc/php/8.2/apache2/php.ini
sed -i 's/^\(User\|Group\).*/\1 asterisk/' /etc/apache2/apache2.conf

sed -i -e "s/^#\([[:space:]]*AddHandler[[:space:]]*cgi-script[[:space:]]*\.cgi\)$/\1/" /etc/apache2/mods-available/mime.conf
sed -i -e "s/^\([[:space:]]*Options Indexes FollowSymLinks\)$/\1 ExecCGI Includes/" /etc/apache2/apache2.conf
sed -i -e "s/^\([[:space:]]*AllowOverride\) None$/\1 All/" /etc/apache2/apache2.conf

a2enmod rewrite cgid include
systemctl restart apache2
rm /var/www/html/index.html

#
# Add browser phone, etc.
#
cd /var/www/html; mkdir cdn cgi
cd; git clone https://github.com/glmck13/PBX-My-Home.git
cp -pr ./PBX-My-Home/phone ~-
cp -pr ./PBX-My-Home/misc/*.cgi ~-/cgi
cp -pr ./PBX-My-Home/misc/*.mp3 ~-/cdn
cd -; chown -R asterisk:asterisk phone cdn cgi
chmod +x */*.cgi

cd /var/www/html
wget https://github.com/filegator/static/raw/master/builds/filegator_latest.zip
unzip filegator_latest.zip && rm filegator_latest.zip
chown -R asterisk:asterisk filegator/
chmod -R 775 filegator/
mv filegator tunes
cd tunes
rmdir repository; ln -s ../cdn repository
sed -i -e "s?'add_to_head' => '',?'add_to_head' => '<center><b>Extract YouTube Audio</b><form action=\"/cgi/youtube.cgi\"><input type=\"text\" name=\"url\" size=50 placeholder=\"Enter URL...\"><input type=\"submit\" value=\"Process\"></form></center>',?" configuration.php
sed -i -e "s/'development'/'production'/" index.php

apt-get install python3-venv gridsite-clients
cd /var/lib/asterisk
cat - <<EOF >helper.sh
#!/bin/bash
python3 -m venv venv
source venv/bin/activate
pip3 install yt-dlp
EOF
chmod +x helper.sh
su - asterisk -c ./helper.sh
rm -f helper.sh

cat - <<EOF >/etc/asterisk/freepbx_chown.conf
[blacklist]
directory = /var/www/html/cgi
directory = /var/www/html/phone
directory = /var/www/html/tunes
directory = /var/lib/asterisk
EOF

cat - <<EOF >/etc/asterisk/extensions_custom.conf
[from-internal-custom]

exten => _4XXX,1,Answer()
same => n,Gosub(macro-user-callerid,s,1())
same => n,Set(VOLUME(TX)=3)
same => n,MP3Player(http://localhost/cgi/mp3.cgi?${EXTEN})
same => n,Hangup()
EOF

chown -R asterisk:asterisk /etc/asterisk

#
# Configure ODBC
#
cat <<EOF > /etc/odbcinst.ini
[MySQL]
Description = ODBC for MySQL (MariaDB)
Driver = /usr/lib/$(arch)-linux-gnu/odbc/libmaodbc.so
FileUsage = 1
EOF

cat <<EOF > /etc/odbc.ini
[MySQL-asteriskcdrdb]
Description = MySQL connection to 'asteriskcdrdb' database
Driver = MySQL
Server = localhost
Database = asteriskcdrdb
Port = 3306
Socket = /var/run/mysqld/mysqld.sock
Option = 3
EOF

#
# Install FreePBX
#
cd /usr/local/src
wget http://mirror.freepbx.org/modules/packages/freepbx/freepbx-17.0-latest-EDGE.tgz
tar zxvf freepbx-17.0-latest-EDGE.tgz
cd /usr/local/src/freepbx/
./start_asterisk start
./install -n

fwconsole ma installall
fwconsole reload
fwconsole restart

cat <<EOF > /etc/systemd/system/freepbx.service
[Unit]
Description=FreePBX VoIP Server
After=mariadb.service
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/sbin/fwconsole start -q
ExecStop=/usr/sbin/fwconsole stop -q
[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable freepbx

############

#
# Update clrcdr script
#
dbpass=$(grep DBPASS /etc/freepbx.conf)
dbpass=${dbpass##* } dbpass=${dbpass%;}
sed -i -e "s/DBPASS=.*/DBPASS=${dbpass}/" /var/www/html/cgi/clrcdr.cgi

#
# Configure firewall
#
#cat - <<EOF >/etc/iptables/rules.v4
#*filter
#:INPUT DROP [0:0]
#-A INPUT -i lo -j ACCEPT
#-A INPUT -p tcp -m tcp --tcp-flags ACK ACK -j ACCEPT
#-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
#-A INPUT -p tcp -m tcp --dport 22 -j ACCEPT
## SSH, HTTP & SIP CLIENTS
## -A INPUT -s XXX.XXX.XXX.XXX -j ACCEPT
## FLOWROUTE
#-A INPUT -s 34.226.36.32/28 -j ACCEPT
#-A INPUT -s 34.210.91.112/28 -j ACCEPT
## Private (LAN) IP Addresses
#-A INPUT -s 10.0.0.0/8 -j ACCEPT
#-A INPUT -s 127.0.0.0/8 -j ACCEPT
#-A INPUT -s 172.16.0.0/12 -j ACCEPT
#-A INPUT -s 192.168.0.0/16 -j ACCEPT
#COMMIT
#EOF

#
# Get cert, turn on HTTPS
#
#systemctl stop apache2
#certbot certonly --standalone
#a2enmod ssl
#a2ensite default-ssl
#vi /etc/apache2/sites-enabled/default-ssl.conf
#systemctl restart apache2
