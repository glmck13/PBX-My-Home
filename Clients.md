## Configure ATA

## Configure softphone on Windows/Linux
I’ve had excellent success using the [Linphone SIP client from Belledonne Communications](https://www.linphone.org/).  It supports both audio and video calling, and has lots of features, but we’ll just configure the basics for now.  

After installing the software on your desktop, access the “Account Assistant” and click “Use a SIP Account”:
+ Username: ***Enter an extension number you created on FreePBX***
+ SIP Domain: ***Enter the IP address of your cloud server ***
+ Password:  **Enter the Secret you created for the extension on FreePBX***
+ Transport: ***UDP***

Click “USE”.  

Go back to the Linphone home screen, enter *60 in the “Search contact, start a call or a chat…” field, and hit enter.  If all goes well you’ll be connected to the time application on your FreePBX server!
