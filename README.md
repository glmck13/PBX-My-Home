# PBX-My-Home
Don't get rid of your house phone... Supercharge it with a PBX!  

# Installation
Installation consists of 3 basic steps:
1. Setting up the cloud PBX server
2. Subscribing to the VoIP provider, and either porting your existing phone number or purchasing a new one
3. Configuring your home SIP clients: ATAs and softphones

# Cloud PBX
We’ll be installing FreePBX on a vanilla version of Debian 12.  The server needs at least 1GB of RAM to work OK, but otherwise 1 CPU and 20GB of storage should be fine.  Although I’m a big fan of AWS LightSail, I recently found out about [Vultr](https://my.vultr.com/), a cloud provider recommended by [Crosstalk solutions](https://www.crosstalksolutions.com/recommendations/).  

Before spinning up the server, follow the instructions for creating [SSH keys](https://docs.vultr.com/how-do-i-generate-ssh-keys) and [firewall rules](https://docs.vultr.com/vultr-firewall).  Here are the rules for the firewall (for now we’re going to stick with IPv4, since the various IPv6 SIP implementations still seem somewhat buggy):  
+ accept	SSH	22	0.0.0.0/0	
+ accept	TCP (HTTP)	80	0.0.0.0/0	
+ accept	TCP	3478	0.0.0.0/0	
+ accept	UDP	3478	0.0.0.0/0	
+ accept	UDP	5060	0.0.0.0/0	
+ accept	TCP	5349	0.0.0.0/0	
+ accept	UDP	10000 – 20000	0.0.0.0/0	
+ drop	any	0 - 65535	0.0.0.0/0	(default)

Don’t worry about exposing the ports to every IP address; we’re going to add IP address restrictions on the server using iptables.

The following server specs should be adequate, and the server costs only $5/month:
+ Cloud compute - Shared CPU
+ Location: Any US data center
+ Image: Debian 12 x64
+ Plan: Regular cloud compute, 1 vCPU, 1 GB RAM, 25GB SSD, 1 TB bandwidth
+ Auto Backups: Decline
