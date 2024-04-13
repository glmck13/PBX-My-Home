
## MMS Messaging app
<img src="https://github.com/glmck13/PBX-My-Home/blob/main/msgapp/screenshot.png" width=500>

## Installation instructions
The app can be installed on any host running an Apache web server with https configured, since the Flowroute API sends/receives messages using HTTPS.  You can install the app on the PBX server if you'd like, but if so, you'll first have to register a domain name for your site, and obtain an SSL certificate.  There are a variety of ways to accomplish this, but you'll likely have to shell out a few dollars to register a domain name.  Many domain providers also give you the option to purchase a certificate for an additional fee, or you can get a cert for free using [Let's Encrypt](https://letsencrypt.org/) and their [Cerbot utility](https://certbot.eff.org/).

Once your site is https-enabled, the rest of the installation is pretty simple. The instuctions below assume you're installing the app on your PBX server, and need to be executed as root:
+ Install the following additional packages:
```
apt install ksh uuid-runtime gridsite-clients
```
+ Enable CGI processing on your Apache server:
```
a2enmod cgid
```
