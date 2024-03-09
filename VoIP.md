## Subscribe to VoIP provider
Crosstalk Solutions recommends [VoIP.ms]( https://voip.ms/residential), but I’ve had good success so far with Flowroute, and their pricing is even less.  You can sign up for a [Flowroute account here](https://manage.flowroute.com/signup/).  

Depending on your circumstances, you either need to: a) purchase a phone number, a.k.a. a "DID", or b) port your current number over to the VoIP provider. 

## Option A: Purchase a DID
If you’ve never had a home phone, you’ll need to start by selecting and purchasing a phone number.  The process is very easy.  Simply [follow this how-to](https://support.flowroute.com/393220-Purchase-a-phone-number-DID) from Flowroute’s knowledge base.

## Option B: Port your existing phone number
If you already have a home phone, you’ll need to port your number from your current provider over to Flowroute.  Yes, this option is more complicated, and can take upwards of a week or more for processing.  Again, just [follow the how-to](https://support.flowroute.com/752594-Port-Your-Telephone-Number-to-Flowroute) from Flowroute’s knowledge base.  You must provide proof that you currently assert ownership over your phone number, which usually consists of uploading a recent billing statement from your current provider.  Your current provider may also supply you a PIN than you can enter in your port order to facilitate processing.  It’s likely your current provider has some information posted on web that describes how to transfer your number, so you’ll want to check with them first before submitting a port order to Flowroute.  When you submit the order, **do not select Enable CNAM Lookup**, which retrieve caller ID info for inbound calls.  This adds an additional $0.0039 charge to the call, which is almost as expensive as the call itself!  

After you submit your order, you’ll receive updates along the way about how things are progressing.  If all goes well, and your order is approved, you’ll receive a date and time when your phone server will be cut over.  You will want to make sure your PBX set up and ready to go before then!

## Create route from Flowroute to your PBX
You can only complete this step after creating your PBX virtual server, since you'll need its IPv4 address.  After your PBX is up and running, [follow this how-to](https://support.flowroute.com/278843-Create-an-Inbound-Route-with-your-Preferred-PoP) to defile a route. Here are the values to enter:
+ Route Type: **URI**
+ Route: **sip:FLOWROUTE@PBX_address**, where **PBX_address** is the IPv4 address assigned to your server
+ Edge Strategy: **<pick one close to home!>**, e.g. ***US-East-VA***

Once the route is created, return to the DID menu, check the box next to your phone number, select “Set Route” from “Choose a DID Action”, and pick the route you just entered.  And while your on the page, click the E911 menu option at the top and fill out the physical address you want to assign to your phone.
