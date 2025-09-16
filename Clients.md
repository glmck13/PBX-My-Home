## Configure Grandstream ATA
I’ve had good success using the [Grandstream HT801 ATA](https://www.amazon.com//dp/B0DPZSNL8K) (available for about $40 on Amazon) to connect my cordless phone system to my PBX.  The device has an extensive set of configurable parameters, but the settings below are the minimal set of changes needed following a factory reset to establish a SIP connection to your PBX.  

You’ll need the local LAN address of the ATA to configure it with a web browser.  The easiest way to discover the address is to first connect your analog phone to the ATA, then dial *** followed by menu option 02.  The device will audibly report its IP address so you can use that to http into its web interface.

+ FXS Port
  + Primary SIP Server: ***IP_address_of_PBX***
  + NAT Traversal: ***STUN***
  + SIP User ID: ***Enter the extension number you configured on the PBX***
  + Authenticate ID: ***Enter the extension number you configured on the PBX***
  + Authenticate Password: ***Enter the Secret you assigned to the extension***
  + SIP REGISTER Contact Header Uses: ***WAN Address***  

Click “Apply”  

+ Advanced Settings tab:
  + STUN server is: ***IP_address_of_PBX:3478***

Click “Apply”

Click “Reboot”.  After the ATA comes back on line dial *60# on your phone handset. If all goes well you’ll be connected to the "current time" application on your FreePBX server!

### Note
If you want to connect the Grandstream to Flowroute directly, you can follow the instructions above using your supplied Flowroute SIP credentials with one notable exception.  The "SIP User ID" must be set to your 10 digit phone number in order that this will be passed along as the caller ID in outgoing calls.  Flowroute specifically mentions this in their [Generic PBX or phone setup guide](https://support.flowroute.com/293702-Generic-PBX-or-phone-setup-guide).  You may also need to set the "Name" field to your DID as well.  And while you're at it, set the "Dial Plan Prefix" to "1" on the Granstream so you don't have to add this digit on every call.

## Configure OBi30X ATA
After Google canceled its Google Talk service a few years ago, there wasn’t much use for the OBi30X ATAs anymore, so the manufacturer (now HP) designated them as end-of-life.  Nonetheless, the units function just fine for connecting a house phone to your PBX (or directly to another VoIP provider), and you can still purchase cheap [OBi30X ATAs on Amazon](https://www.amazon.com/dp/B07FZYPD8T/).  What’s more, you can also purchase a [WiFi dongle](https://www.amazon.com/dp/B07FZQX1RQ) for the OBi so you can locate the ATA anywhere in your house without having to directly cable it to your home router.

Just as with the Grandstream, you first need to connect an analog phone to the OBi to retrieve its IP address and enable the web interface. First dial ***1 to get the IP address of the device. Then dial ***0 to enter the configuration menu, followed by 30# to reach the web server setting. Press 1, then 1# to enable the web server, then 1 to save the settings.


## Configure browser phone

## Configure Linphone

On the client side:
+ In case you have problems authenticating with the PBX, you may need to update Linphone's rootca.pem file with the cert of the CA that issued your PBX cert.  This file is stored under /usr/share/linphone.  If you're using an AppImage, you'll first need to extract the AppImage and then update the copy of the file stored locally.
