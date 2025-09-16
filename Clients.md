## Configure Grandstream ATA
I’ve had good success using the [Grandstream HT801 ATA](https://www.amazon.com//dp/B0DPZSNL8K) (available for about $40 on Amazon) to connect my cordless phone system to my PBX.  The device has an extensive set of configurable parameters, but the settings below are the minimal set of changes needed following a factory reset to establish a SIP connection to your PBX.  

You’ll need the local LAN address of the ATA to configure it with a web browser.  The easiest way to discover the address is to first connect your analog phone to the ATA, then dial *** followed by menu option 02.  The device will audibly report its IP address so you can use that to http into its web interface.

+ FXS Port
  + Primary SIP Server: ***Enter DNS name or IP address of your PBX***
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

Just as with the Grandstream, you first need to connect an analog phone to the OBi to retrieve its IP address and enable the web interface. First dial ***1 to get the IP address of the device. Then dial ***0 to enter the configuration menu, followed by 30# to reach the web server setting. Press 1, then 1# to enable the web server, then 1 to save the settings. Next, goto http://<IP address> on your browser.  The default credentials are: Username: admin, Password: admin.  Navigate through the Setup Wizard on the left and set the parameters as specified below.  Note that in order to make a change to a parameter you first must uncheck the "Default" checkbox.

+ Service Providers
  + ITSP Profile A
    + General
      + DigitMap: ***(*xx|xxxx|9xxxxxxxxxx)***
      + STUNEnable: ***Check the box***
      + STUNServer: ***Enter DNS name or IP address of your PBX***  
      Click “Submit”
    + SIP
      + ProxyServer: ***Enter DNS name or IP address of your PBX***
      + ProxyServerTransport: ***TCP***  
      Click “Submit”

+ Voice Services
  + SP1 Service
    + AuthUserName: ***Enter the extension number you configured on the PBX***
    + AuthPassword: ***Enter the Secret you assigned to the extension***  
    Click “Submit”

+ Physical Interfaces
  + PHONE1 Port
    + DigitMap: ***(*xx|xxxx|9xxxxxxxxxx)***
    + OutboundCallRoute: ***{(Msp1):sp1}***
    + CallReturnDigitMaps: ***Set the field to blank***
    + StarCodeProfile: ***None***  
    Click “Submit”  

Click “Reboot”

## Configure browser phone
<img src=https://github.com/glmck13/PBX-My-Home/blob/main/browser-phone.png width=600px>  

There’s a “phone” folder in the repo that contains a stand-alone phone client that you can launch from within any browser. The client supports both audio and video calls.  Video calls can be a little temperamental, so if you expect to make a lot of video calls, it‘s probably best to install Linphone on your device (the app is free). Instructions for downloading and configuring Linphone are packaged with the browser phone.

The browser phone is served from your PBX, and was copied into /var/www/html/phone during installation.  Be sure to update contacts.csv with any extensions you want listed in the phone's pull-down menu, then run ./contacts.cgi to generate the runtime html files.

To use the phone enter the following URL in your browser: http://*PBX_name_address*/phone?user=*User*&secret=*Secret*, where *User* is listed in your contacts list, and *Secret* is the value you assigned to that user’s extension in the PBX.  If you authenticate successfully, you’ll see a page similar to the one above.

## Configure Linphone

Instructions for configuring Linphone are included with the browser phone.  If you decide to use TLS within Linphone, you may encounter a problem with Linphone's set of Certificate Authorities (CAs).  Apparently Linphone does not keep their rootca.pem file updated with all the latest certs, so it's possible you won't be able to establish a trusted connection with your PBX if the issuer of your cert isn't recognized by Linphone.  Thankfully, however,  I've had good success, using certs issued by Let's Encrypt.
