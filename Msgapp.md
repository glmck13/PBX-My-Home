## SMS/MMS Messaging app
<img src="https://github.com/glmck13/PBX-My-Home/blob/main/msgapp/screenshot.png" width=500>

## Installation instructions
The app can be installed on any host running an Apache web server with https configured, since the Flowroute API sends/receives messages using HTTPS.  You can install the app on the PBX server if you'd like, but if so, you'll first have to register a domain name for your site, and obtain an SSL certificate.  There are a variety of ways to accomplish this, but you'll likely have to shell out a few dollars to register a domain name.  Many domain providers also give you the option to purchase a certificate for an additional fee, or you can get a cert for free using [Let's Encrypt](https://letsencrypt.org/) and their [Cerbot utility](https://certbot.eff.org/).

Once your site is https-enabled, the rest of the installation is pretty simple. The instuctions below assume you're installing the app on your PBX server.  Execute these as root:
+ Install the following additional packages:
```
apt install ksh uuid-runtime gridsite-clients
```
+ Enable CGI processing on your Apache server:
```
a2enmod cgid
sed -i -e "s/^#\([[:space:]]*AddHandler[[:space:]]*cgi-script[[:space:]]*\.cgi\)$/\1/" /etc/apache2/mods-available/mime.conf
sed -i -e "s/^\([[:space:]]*Options Indexes FollowSymLinks\)$/\1 ExecCGI/" /etc/apache2/apache2.conf
```
+ Prevent FreePBX from disabling execute permissions on the app:
```
cat - <<EOF >/etc/asterisk/freepbx_chown.conf
[blacklist]
directory = /var/www/html/cgi
directory = /var/www/html/msgapp
```
+ Grant Flowroute's SMS/MMS messaging server access to your PBX by adding the following statement to your /etc/iptables/rules.v4 file anywhere before the final COMMIT:
```
-A INPUT -s 52.88.246.140 -j ACCEPT
```
+ Install the "msgapp" directory and it contents located in this repository directly under /var/www/html on your server.  Be sure to chmod +x *.cgi *sh *.py.  Afterwards, edit the two getenv files and populate your Flowroute credentials as well as the msgapp URL for your site.

That's it!
