#!/bin/ksh

typeset -a CID=("Name-1" "Name-2" "Name-3" "...")

endpoint=${1:?Enter starting endpoint}
count=${2:?Enter number of endpoints}
offset=${3:?Enter offset}
pin=${4:?Enter pin}

let n=0
while [ $n -lt "$count" ]
do
cat - <<EOF
[${endpoint}]
type=aor
max_contacts=1
remove_existing=yes

[${endpoint}-auth]
type=auth
auth_type=userpass
username=${endpoint}
password=${pin}

[${endpoint}]
type=endpoint
aors=${endpoint}
auth=${endpoint}-auth
webrtc=yes
use_avpf=yes
transport=0.0.0.0-wss
media_encryption=dtls
dtls_cert_file=/etc/asterisk/keys/asterisk.crt
dtls_private_key=/etc/asterisk/keys/asterisk.key
dtls_verify=fingerprint
dtls_setup=actpass
dtls_rekey=0
ice_support=yes
media_use_received_transport=no
rtcp_mux=yes
allow=all
context=from-internal
callerid=${CID[$n]} <${endpoint}>
outbound_auth=${endpoint}-auth
language=en

EOF

let endpoint=${endpoint}+$offset
let n=$n+1

done
