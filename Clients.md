## Configure ATA
I’ve had good success using the [Grandstream HT801 ATA](https://www.amazon.com//dp/B06XW1BQHC) (available for about $40 on Amazon) to connect my cordless phone system to my PBX.  The device has an extensive set of configurable parameters, but the settings below are the minimal set of changes needed following a factory reset to establish a SIP connection to your PBX.  

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

## Configure softphone on Windows/Linux
I’ve had excellent success using the [Linphone SIP client from Belledonne Communications](https://www.linphone.org/).  It supports both audio and video calling, and has lots of features, but we’ll just configure the basics for now.  

After installing the software on your desktop, access the “Account Assistant” and click “Use a SIP Account”:
+ Username: ***Enter an extension number you created on FreePBX***
+ SIP Domain: ***Enter the IP address of your cloud server***
+ Password:  **Enter the Secret you created for the extension on FreePBX***
+ Transport: ***UDP***

Click “USE”.  

Go back to the Linphone home screen, enter *60 in the search field, and hit enter.  If all goes well you’ll be connected to the "current time" application on your FreePBX server!
