# WeTube
Browser-based video sharing service with integrated WebRTC phone  

<img width=800 src=https://github.com/glmck13/KidStuff/blob/main/wetube/wetube.png>  

## Background
I wanted to create a simple web-based tool that would allow us to communicate with our granddaughter - something that would allow us to share videos and even talk in real time.  The result was a very simple browser-based app that makes good use of the MediaRecorder capability built into today’s browsers.
## Using the browser as a video recorder
The following links helped me figure out how to make native video recordings from the browser:
+ [Recording Audio from the User, Dec 5, 2022, Paul Kinlan](https://web.dev/media-recording-audio/)
+ [MediaRecorder API, Nov 23, 2020, Youenn Fablet](https://webkit.org/blog/11353/mediarecorder-api/)  

Once I recorded the video, I had to upload it to my server.  For help with that task, I looked here:
+ [How can JavaScript upload a blob? Feb 6, 2023, Amit Diwan](https://www.tutorialspoint.com/how-can-javascript-upload-a-blob)  

On the server side I use ffmpeg to convert the uploaded videos to MP4 format, since this plays natively using HTML5 <video> tags.

## Using the browser as a WebRTC client
There’s an excellent [WebRTC SIP client for the browser written by Conrad de Wit posted on GitHub](https://github.com/InnovateAsterisk/Browser-Phone).  That turned out to be the easy part to get a phone integrated into my page.  The more difficult task was trying to figure out how to configure my Asterisk/FreePBX to process WebRTC calls.

## Configuring FreePBX & Asterisk
The Asterisk help documentation got me most of the way there, but unfortunately omitted some key settings.  After combining tidbits from the following sites, I managed to get things working:
+ [WebRTC tutorial using SIPML5, Rusty Newton, Jul 3, 2018](https://wiki.asterisk.org/wiki/pages/viewpage.action?pageId=40818097)
+ [Freepbx Failed to create fingerprint from the digest, Aug 2022](https://community.freepbx.org/t/freepbx-failed-to-create-fingerprint-from-the-digest/85205)
+ [WebRTC configuration by VoIPmonitor, Aug 7, 2020](https://www.voipmonitor.org/doc/WebRTC)
+ [Setting up Asterisk for webrtc, 2022, Rajan Paneru](https://gist.github.com/paneru-rajan/01f73e3ec79c2b7a647824e76b901de8)

The two shell scripts in the freepbx directory generate the necessary PJSIP endpoints and extensions for the WebRTC clients.  These settings can simply be populated in the respective “custom.conf” files in the /etc/asterisk directory. Along the way I also had to recompile Asterisk to add the OPUS codec.  Thankfully [RonR's installation tool](https://www.dslreports.com/forum/r30661088-PBX-FreePBX-for-the-Raspberry-Pi) included an install_opus script under the /root directory for doing just that. And since the PBX is sitting in my basement behind a broadband connection, I also needed the services of a STUN/TURN server.  I decided to just turn up one of my own, following these instructions:
+ [WebRTC TURN server: Everything you need to know, Oct 17, 2022, S. Karthikeyan](https://www.100ms.live/blog/webrtc-turn-server)

At first I thought I'd accept outside calls from native SIP clients (like Linphone) in addition to WebRTC clients, but when I opened up UDP port 5060 in my Asterisk firewall, I found I was getting SIP storms from the Internet.  As a result I decided to just stick with WebRTC clients, and only allow calls from trusted IP address ranges. 
