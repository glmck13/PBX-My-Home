fallocate -l 1G /swapfile 
chmod 600 /swapfile 
mkswap /swapfile 
swapon /swapfile 
cp /etc/fstab /etc/fstab.bak 
echo '/swapfile none swap defaults 0 0' | tee -a /etc/fstab
