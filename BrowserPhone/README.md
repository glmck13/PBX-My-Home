## Using the browser as a WebRTC client
There’s an excellent [WebRTC SIP client for the browser written by Conrad de Wit posted on GitHub](https://github.com/InnovateAsterisk/Browser-Phone).  That turned out to be the easy part to get a phone integrated into my page.  The more difficult task was trying to figure out how to configure my Asterisk/FreePBX to process WebRTC calls.

## Configuring FreePBX & Asterisk
The Asterisk help documentation got me most of the way there, but unfortunately omitted some key settings.  After combining tidbits from the following sites, I managed to get things working:
+ [Freepbx Failed to create fingerprint from the digest, Aug 2022](https://community.freepbx.org/t/freepbx-failed-to-create-fingerprint-from-the-digest/85205)
+ [WebRTC configuration by VoIPmonitor, Aug 7, 2020](https://www.voipmonitor.org/doc/WebRTC)
+ [Setting up Asterisk for webrtc, 2022, Rajan Paneru](https://gist.github.com/paneru-rajan/01f73e3ec79c2b7a647824e76b901de8)

The two shell scripts generate the necessary PJSIP endpoints and extensions for the WebRTC clients.  These settings can simply be populated in the respective “custom.conf” files in the /etc/asterisk directory. Along the way I also had to recompile Asterisk to add the OPUS codec. And since the PBX is sitting in my basement behind a broadband connection, I also needed the services of a STUN/TURN server.  I decided to just turn up one of my own, following these instructions:
+ [WebRTC TURN server: Everything you need to know, Oct 17, 2022, S. Karthikeyan](https://www.100ms.live/blog/webrtc-turn-server)

At first I thought I'd accept outside calls from native SIP clients (like Linphone) in addition to WebRTC clients, but when I opened up UDP port 5060 in my Asterisk firewall, I found I was getting SIP storms from the Internet.  As a result I decided to just stick with WebRTC clients, and only allow calls from trusted IP address ranges. 
