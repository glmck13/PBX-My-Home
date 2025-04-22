# PBX-My-Pi
Configure home PSTN gateway with Grandstream ATA and FreePBX
<img src=https://github.com/glmck13/HomePBX/blob/main/drawing.png width=600px>  
## Background
For the past several years I’ve been running Asterisk on a Raspberry Pi 3B equipped with an FXO board from [SwitchPi](https://switchpi.com/).  The system would listen to incoming calls, and then speak the incoming caller ID aloud with the aid of [Polly, the text-to-speech service in AWS](https://aws.amazon.com/polly/).  Problem is, the drivers for the SwitchPi board were compiled for a specific version of Raspbian, which made it impossible to upgrade either the OS or Asterisk.  So I figured it was a time for a change! A little Googling landed me on the [HT813 ATA from Grandstream](https://www.grandstream.com/hubfs/Product_Documentation/HT813_User_Guide.pdf), so I set out to build a more robust PSTN gateway for my house by marrying that with the latest version of [FreePBX & Asterisk from Sangoma](https://www.freepbx.org/).
## FreePBX build instructions
I started with an old Raspberry Pi 3B I had lying around, and installed the latest version of [Raspberry Pi OS using the imager tool](https://www.raspberrypi.com/software/). I then assigned a fixed IPv4 address to my Pi (this is done via the dhcpcd menu!) and plugged it into one of the available Ethernet ports on my home router.  I named the system “freepbx.home”.  Next I installed the latest releases of FreePBX and Asterisk following [RonR’s script posted on DSLReports](https://www.dslreports.com/forum/r30661088-PBX-FreePBX-for-the-Raspberry-Pi).  The process required a sequence of reboots of the Raspberry Pi, but it executed flawlessly!
## Grandstream config
Next step was to configure the Grandstream.  I plugged the WAN port of the ATA into an Ethernet jack on my home router (the ATA behaves as a client over this port),  set a static IPv4 address for the device, and disabled IPv6.  I named the device “grandstream.home”.   I then needed to configure a “trunk”, as FreePBX calls it, between the ATA and PBX. I named the trunk “PSTN”.  Here’s what I set on the Grandstream end:
### BASIC SETTINGS:
+ Unconditional Call Forward to VOIP: User ID: PSTN, Sip Server: freepbx.home, Sip Destination Port: 5060
### FXS PORT
+ Primary SIP Server: **freepbx.home**
+ SIP User ID: **6200** (*this is the Asterisk extension # for the FXS port*)
+ Authenticate ID: **6200**
+ Authenticate Password: (*enter a numeric password; must be same on FreePBX end*)
+ SIP Registration: **Yes**
+ Outgoing call without Registration: **Yes**
### FXO PORT
+ Primary SIP Server: **freepbx.home**
+ SIP User ID: **PSTN** (*this is the Asterisk trunk name*)
+ Authenticate ID: **PSTN**
+ Authenticate Password: (*enter a numeric password; must be same on FreePBX end*)
+ SIP Registration: **Yes**
+ Outgoing call without Registration: **Yes**
+ Number of Rings: **2** (*set as low as possible, but must allow sufficient time for caller ID to be passed in over PSTN line*)
+ PSTN Ring Thru FXS: **No** (*this allows the FXS & FXO ports to operate independently*)
+ Stage Method (1/2): **1**
## FreePBX Config
### Settings > Asterisk SIP Settings > General Settings
NAT Settings
+ External Address: Click on **Detect Network Settings** (*needed so RTP works thru NAT*)
+ Local Networks: **192.168.1.0/24**

### Settings > Advanced Settings > Dialplan and Operational
+ Asterisk Dial Options: **Tt** (*enables call transfer capabilities*)
+ Disallow transfer features for inbound callers: **No**

### Settings > Admin > Feature Codes
Core
+ In-Call Asterisk Attended Transfer: **Enabled**
+ In-Call Asterisk Attended Transfer Aborting: **Enabled**
+ In-Call Asterisk Attended Transfer Completing: **Enabled**
+ In-Call Asterisk Attended Transfer Completing as a three-way bridge: **Enabled**
+ In-Call Asterisk Attended Transfer Swapping between the transferee and destination: **Enabled**

### Connectivity > Trunks > Add Trunk
General
+ Trunk Name: **PSTN**
+ Oubound CallerrID: (*PSTN phone #*)
+ CID Options: **Force trunk CID**
+ Maximum Channels: **1**
+ Asterisk Trunk Dial Options: (*left this alone; my system has this set to ‘R’ so ringing is provided early on outgoing calls*)
   
pjsip Settings, General
+ Username: (*left this alone; my system has this set to trunk name*)
+ Auth username: (*ditto*)
+ Secret: (*same as setting on HT813*)
+ Authentication: **Both**
+ Registration: **Receive** (*these last two settings are necessary so the Grandstream FXO and FXS port registration activities don’t interfere with each other*)
+ Context: **from-trunk-pjsip-PSTN**
  
pjsip Settings, Advanced
+ Match Inbound Authentication: **Auth Username** (needed so that inbound calls authorize properly, even though the Grandstream has registered the PSTN trunk)  

### Connectivity > Outbound Routes > Add Outbound Route
Route Settings
+ Route Name: **OutboundPSTN**
+ Route CID: (*PSTN phone #*)
+ Override extension: **Yes**
+ Trunk Sequence for Matched Routes: **PSTN**
   
Dial Patterns
+ prepend: blank
+ prefix: **9** (*i.e. dial ‘9’ for an outside call*)
+ match pattern: **XXXXXXXXXX** (*10 digit calling*)

### Connectivity > Inbound Routes > Add Inbound Route
+ Description: **InboundPSTN**
+ Set destination: **Extensions**, **6100** (*my extension*)
## Call announcements
My FreePBX Pi is colocated with my router down in the basement, so it's not optimal for sending out incoming call announcements.  As a result I set up another Pi equipped with a small speaker named "pimate".  This 2nd Pi connects to the house LAN via Wifi, so I can place it anywhere.  I make use of Asterisk's FastCGI interface to send a message from the freepbx to pimate.  I inserted the call inside the macro-dialout-one-predial-hook context, and placed this inside /etc/asterisk/extensions_override_freepbx.conf so it would be inserted into my Asterisk dialplan.  I use ncat on pimate (the NMAP version) to listen for the FastCGI TCP message, after which I extract the callerid.  I then make a call to Polly to generate the desired text-to-speech, then play it with the sox utility.  The attached ringtones.sh script does what you need.  I launch it at reboot from my user crontab: @reboot $HOME/bin/ringtones.sh >/tmp/ringtones.log 2>&1 &
## VoIP client
I installed [linphone](https://www.linphone.org/) on both my Linux and Windows desktops, and registered with extension sip:6100@freepbx.home on my freepbx.  Incoming calls ring on both my house phone and the linphone clients.  The sound quality is excellent!  To initiate an outbound call from my computer, I just prefix the 10-digit number with a '9' (since this is how I configured the dial patters in the PBX).
## References
I cobbled togther the above config from a variety of different sources on the web.  As it turned out, each of the sources turned out to have some inaccurate or missing info, so it took some trial and error before I got everything working. Here are a few of the links that turned out to be most directionally correct:
1. [Convert Your Analog Phone Line To Digital With Grandstream HT813](https://vitalpbx.com/blog/convert-your-analog-phone-line-to-digital/)
2. [FreePBX and Grandstream HT813](https://community.freepbx.org/t/freepbx-and-grandstream-ht813/87346/8)
3. [Configuring a Grandstream HT503 Device to act as an FXO Gateway](https://wiki.freepbx.org/pages/viewpage.action?pageId=33293313)
