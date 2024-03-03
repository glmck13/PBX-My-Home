## Spin up cloud server
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

Select the SSH keys and Firewall Group you created earlier, enter a hostname for the server (you can change this later), give the instance a label, and click Deploy Now.

## Install Asterisk and FreePBX
Once your server is running, download a copy of freepbx17.sh from this repository, and scp it to the root account on your server.  The script installs Asterisk 20 and FreePBX 17 on the system .  It’s based on the [instructions posted on Sangoma’s website](https://sangomakb.atlassian.net/wiki/spaces/FP/pages/10682545/How+to+Install+FreePBX+17+on+Debian+12+with+Asterisk+20).  

Before running the script, you first need to update the file with the IP address of your broadband router.  Edit the file and look for the line at the end that reads:
```
 # -A INPUT -s XXX.XXX.XXX.XXX -j ACCEPT
```
Replace “XXX…” with your IP address of your home broadband router, remove the comment character at the front, save the file, then make it executable.  Launch the script.

You’ll run the script twice.  The first time around the script applies Debian updates and installs a collection of prerequisite packages needed by Asterisk and FreePBX.  After this completes it asks if you want to reboot.  Respond (y)es on the first run, wait for the server to come back online, ssh back in, and run freepbx17.sh a second time.  After checking all the prerequisites have been installed, the script asks if you want to reboot again.  Respond (n)o this time, so that the script proceeds with downloading compiling, and installing Asterisk, then downloading and installing FreePBX.  When asked to select modules during the Asterisk build, just accept the defaults.  After Asterisk and FreePBX are up and running, the script configures the iptables firewall in the server.  When asked if you want to save the current IPv4/IPv6 firewall rules, just respond no.  That’s it!  When you get a command prompt, reboot the server, and ssh back in after it comes back online (this confirms you entered your correct IP address in the firewall!)
