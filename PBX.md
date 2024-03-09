## Subscribe to cloud provider
Although I’m a big fan of AWS LightSail, I recently found out about Vultr, a cloud provider recommended by [Crosstalk Solutions](https://www.crosstalksolutions.com/recommendations/). Vutlr's pricing is comparable to AWS, and they're not charging for use of an IPv4 address, so their monthly rate comes in a few dollars cheaper than AWS for now. :-) You can sign up for a [Vultr account here](https://www.vultr.com/register/).

## Spin up server
We’ll be installing [Asterisk](https://www.asterisk.org/) and [FreePBX](https://www.freepbx.org/) on a vanilla version of Debian 12.  Before spinning up the server, follow Vultr's instructions for creating [SSH keys](https://docs.vultr.com/how-do-i-generate-ssh-keys) and [firewall rules](https://docs.vultr.com/vultr-firewall).  Here are the rules for the firewall (for now we’re going to stick with IPv4, since the various IPv6 SIP implementations still seem somewhat buggy):  
+ accept	SSH	22	0.0.0.0/0	
+ accept	TCP (HTTP)	80	0.0.0.0/0	
+ accept	TCP	3478	0.0.0.0/0	
+ accept	UDP	3478	0.0.0.0/0	
+ accept	UDP	5060	0.0.0.0/0	
+ accept	UDP	10000 – 20000	0.0.0.0/0	
+ drop	any	0 - 65535	0.0.0.0/0	(default)

Don’t worry about exposing the ports to every IP address; we’re going to add IP address restrictions on the server using iptables.

The server needs at least 1GB of RAM to work OK, but otherwise 1 CPU and 20GB of storage should be fine. The following server specs should be adequate, and the server costs only $5/month:
+ Cloud compute - Shared CPU
+ Location: Any US data center
+ Image: Debian 12 x64
+ Plan: Regular cloud compute, 1 vCPU, 1 GB RAM, 25GB SSD, 1 TB bandwidth
+ Auto Backups: Decline

Select the SSH keys and Firewall Group you created earlier, enter a hostname for the server (you can change this later), give the instance a label, and click Deploy Now.

## Install Asterisk and FreePBX
Once your server is running, download and scp the freepbx17.sh script from this repository onto the root account on your server.  The script is based on the [instructions posted on Sangoma’s website](https://sangomakb.atlassian.net/wiki/spaces/FP/pages/10682545/How+to+Install+FreePBX+17+on+Debian+12+with+Asterisk+20) for downloading and installing the latest versions of Asterisk and FreePBX 17 on Debian.  Before running the script, make sure to update the file with the IP address of the broadband router in your home.  Edit the file and look for the line at the end that reads:
```
 # -A INPUT -s XXX.XXX.XXX.XXX -j ACCEPT
```
Replace “XXX…” with the IP address of your router, remove the comment character at the front, save the file, then make it executable.  Launch the script.

You’ll run the script twice.  The first time through the script applies Debian updates and installs a collection of prerequisite packages needed by Asterisk and FreePBX. Respond no when asked if you want to save the current IPv4/IPv6 firewall rules.  After installing this first set of packages, the script prompts you to reboot.  Respond (y)es on the first run, wait for the server to come back online, ssh back in, and run freepbx17.sh a second time.  When prompted to reboot, respond (n)o this time, and the script will download, compile, and install Asterisk, then download and install FreePBX.  When asked to select modules during the Asterisk build, just accept the defaults.  When the script completes, reboot the server then ssh back in to confirm your firewall rules are correct.  You can now proceed to set up FreePBX.  

## Configure FreePBX
Access the FreePBX console from your browser, complete the initial startup screens, then proceed with the configuration steps below. Hold off clicking on the red “Apply Config” button at the top until you’re finished.

### Add Trunk
Connectivity &rarr; Trunks &rarr; Add Trunk &rarr; Add SIP (chan_pjsip) Trunk

+ General tab:
  + Trunk Name: ***FLOWROUTE***
  + Outbound CallerID: ***Your 10-digit VoIP number without the leading country code***
  + Maximum Channels: ***Leave blank; allows for multiple calls using the same VoIP line***

+ Dialed Number Manipulation Rules tab:
  + prepend: ***Tech Prefix for your DID in Flowroute, followed by a single asterisk, and a ‘1’ for the US country code, e.g. 10668144\*1  You can find the Tech Prefix by looking under Interconnection &rarr; IP Authentication in your Flowroute account.***
  + prefix: ***‘9’ to get an outside line***
  + match pattern: ***XXXXXXXXXX for 10 digit calling***

+ pjsip Settings tab:
  + Username: ***Tech Prefix for your DID in Flowroute***
  + Auth username: ***Tech Prefix for your DID in Flowroute***
  + Secret: ***Password specified in Flowroute under Interconnection &rarr; Registration***
  + Authentication: ***Outbound***
  + Registration: ***Send***
  + SIP Server: ***“Point of Presence FQDN” for your DID and chosen “Edge Strategy” as defined in Flowroute under Interconnection &rarr; Registration, e.g. us-east-va.sip.flowroute.com***
  + SIP Server Port: ***5060***

Click “Submit”

### Add Outbound Route
Connectivity &rarr; Outbound Routes &rarr; Add Outbound Route

+ Route Settings tab:
  + Route Name: ***OutboundFLOWROUTE***
  + Route CID: ***Your 10-digit VoIP number without the leading country code***
  + Trunk Sequence for Matched Routes: ***Select FLOWROUTE trunk***

+ Dial Patterns tab:
  + prepend: ***Tech Prefix for your DID in Flowroute, followed by a single asterisk, and a ‘1’ for the US country code, e.g. 10668144\*1***
  + prefix: ***‘9’ to get an outside line***
  + match pattern: ***XXXXXXXXXX for 10 digit calling***

Click “Submit”

### Add Inbound Route
Connectivity &rarr; Inbound Routes &rarr; Add Inbound Route

+ General tab:
  + DID Number: ***_9XXXXXXXXXX***
  + Set Destination: ***Select FLOWROUTE trunk***

Click “Submit”

### Add Extension
Connectivity &rarr; Extensions &rarr; Add Extension &rarr; Add New SIP [chan_pjsip] Extension
+ General tab:
  + User Extension: ***Assign your own 3-digit/4-digit extension***
  + Display Name: ***Same as the extension number***
  + Secret: ***Assign a password for the extension that will be used by your ATA/SIP client to login***

Click “Submit”

### Add Inbound Route
Connectivity &rarr; Inbound Routes &rarr; Add Inbound Route

+ General tab:
  + Set Destination: ***Select extension 1000 to route all incoming calls from your VoIP number to this extension by default***

Click “Submit”

### Enable video calls
Settings &rarr; Asterisk SIP Settings &rarr; General SIP Settings
+ Video Codecs
  + Video Support: ***Enabled***

Click “Submit”

You can now click "Apply Config" to activate these changes in Asterisk.
