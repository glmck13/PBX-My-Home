#!/bin/ksh

ext=${1:?Enter starting extension}
count=${2:?Enter number of extensions}
offset=${3:?Enter offset}

cat - <<-"EOF"
[from-internal-custom]

exten => _8X.,1,Goto(from-pstn-custom,${EXTEN},1)
exten => 444,1,Goto(from-pstn-custom,${EXTEN},1)
exten => 411,1,Goto(from-pstn-custom,${EXTEN},1)
exten => 999,1,Goto(from-pstn-custom,${EXTEN},1)
exten => 555,1,Goto(from-pstn-custom,${EXTEN},1)
exten => 333,1,Goto(from-pstn-custom,${EXTEN},1)
exten => 222,1,Goto(from-pstn-custom,${EXTEN},1)
exten => 111,1,Goto(from-pstn-custom,${EXTEN},1)

exten => 6000,1,Noop(Call from ${CALLERID(DNID)} to ${EXTEN})
same => n,Gosub(macro-user-callerid,s,1())
same => n,AGI(agi://pimate.local/polly.sh)
same => n,GotoIf($["${CALLERID(DNID)}" = "FLOWROUTE"]?ivr)
same => n,Dial(PJSIP/6100&PJSIP/6200)
same => n,Hangup()
;same => n,AGI(ttsagi.py,"Enter extension followed by the pound key.",/var/lib/asterisk/sounds/common/extension.mp3)
same => n(ivr),Read(MYCHOICE,common/extension,,t(*#))
same => n,Goto(from-pstn-custom,${MYCHOICE},1)

EOF

while [ "$count" -gt 0 ]
do
cat - <<EOF
exten => ${ext},1,Noop(Call to \${EXTEN})
same => n,Dial(PJSIP/\${EXTEN})
same => n,Hangup()

EOF

let ext=$ext+$offset
let count=$count-1

done

cat - <<-"EOF"
[from-pstn-custom]

exten => 411,1,Answer()
same => n,Gosub(macro-user-callerid,s,1())
same => n,MP3Player(http://piville.home/local/dmr.cgi)
same => n,Hangup()

exten => 999,1,Noop(Call to ${EXTEN})
same => n,Gosub(macro-user-callerid,s,1())
same => n,Dial(PJSIP/GSCAROLINA)
same => n,Hangup()

exten => 555,1,Noop(Call to ${EXTEN})
same => n,Gosub(macro-user-callerid,s,1())
same => n,Dial(PJSIP/OBIBOSTON)
same => n,Hangup()

exten => 333,1,Noop(Call to ${EXTEN})
same => n,Gosub(macro-user-callerid,s,1())
same => n,Dial(PJSIP/6100&PJSIP/6200)
same => n,Hangup()

exten => 111,1,Noop(Call to ${EXTEN})
same => n,Gosub(macro-user-callerid,s,1())
same => n,Dial(PJSIP/OBIMDOC)
same => n,Hangup()

exten => 222,1,Answer()
same => n,Gosub(macro-user-callerid,s,1())
same => n,Set(VOLUME(TX)=2)
;same => n,AGI(ttsagi.py,"Hi, I'm G's voice assistant, and I can help you send a text message.",/var/lib/asterisk/sounds/sms/answer.mp3)
;same => n,AGI(ttsagi.py,"After the beep, press numbers for everyone you want to send your message to. Press 1 for Mom<break time=\"500ms\"/>, 2 for Dad<break time=\"500ms\"/>, 3 for Dee Dee<break time=\"500ms\"/>, 4 for G<break time=\"500ms\"/>, 5 for Aunt KK<break time=\"500ms\"/>, and 6 for Uncle Daniel. Press star when you're done.",/var/lib/asterisk/sounds/sms/who.mp3)
;same => n,AGI(ttsagi.py,"Give me a second to process that...",/var/lib/asterisk/sounds/sms/pause.mp3)
;same => n,AGI(ttsagi.py,"Now tell me your message. Start speaking after the beep. Press any key when you're finished.",/var/lib/asterisk/sounds/sms/what.mp3)
;same => n,AGI(ttsagi.py,"You said:",/var/lib/asterisk/sounds/sms/replay.mp3)
;same => n,AGI(ttsagi.py,"If that's correct, press 1 to continue, or 2 to try again.",/var/lib/asterisk/sounds/sms/chkwho.mp3)
;same => n,AGI(ttsagi.py,"If your message sounds OK, press 1 to send it. Otherwise, press 2 to record it again, or 3 to cancel.",/var/lib/asterisk/sounds/sms/chkwhat.mp3)
;same => n,AGI(ttsagi.py,"Message canceled!",/var/lib/asterisk/sounds/sms/canceled.mp3)
;same => n,AGI(ttsagi.py,"Message sent!",/var/lib/asterisk/sounds/sms/sent.mp3)
;same => n,AGI(ttsagi.py,"Goodbye!",/var/lib/asterisk/sounds/sms/bye.mp3)
;
same => n(msghello),Playback(sms/answer)
;
same => n(msgwho),Playback(sms/who)
same => n,Read(CONTACTS,beep,,t(*#))
same => n,GotoIf($["${READSTATUS}" != "OK"]?msgbye)
same => n,Playback(sms/pause)
same => n,AGI(contactsagi.py,${CONTACTS})
same => n,AGI(ttsagi.py,"${CONTACTS_RSP}",${RECORDED_FILE}.mp3)
;
same => n(msgloop1),Playback(${RECORDED_FILE})
same => n,GotoIf($[${LEN(${CONTACTS_LIST})} = 0}]?msgwho)
same => n,Playback(sms/chkwho)
same => n,Read(MYCHOICE,beep,1)
same => n,GotoIf($["${READSTATUS}" != "OK"]?msgbye)
same => n,GotoIf($["${MYCHOICE}" = "1"]?msgwhat)
same => n,GotoIf($["${MYCHOICE}" = "2"]?msgwho)
same => n,Goto(msgloop1)
;
same => n(msgwhat),Playback(sms/what)
same => n,Record(/tmp/msg%d:wav,3,,y)
same => n,Playback(sms/pause)
same => n,AGI(sttagi.py,${RECORDED_FILE}.wav)
;
same => n(msgloop2),Playback(sms/replay)
same => n,Playback(${RECORDED_FILE})
same => n,Playback(sms/chkwhat)
same => n,Read(MYCHOICE,beep,1)
same => n,GotoIf($["${READSTATUS}" != "OK"]?msgbye)
same => n,GotoIf($["${MYCHOICE}" = "1"]?msgsend)
same => n,GotoIf($["${MYCHOICE}" = "2"]?msgwhat)
same => n,GotoIf($["${MYCHOICE}" = "3"]?msgcancel)
same => n,Goto(msgloop2)
;
same => n(msgcancel),Playback(sms/canceled)
same => n,Goto(msgbye)
;
same => n(msgsend),System(ffmpeg -i ${RECORDED_FILE}.wav ${RECORDED_FILE}.mp3)
same => n,Set(id=${CALLERID(all)})
same => n,AGI(smsagi.py,${RECORDED_FILE},${id},${CONTACTS_LIST})
same => n,Playback(sms/sent)
same => n,Goto(msgbye)
;
same => n(msgbye),Playback(sms/bye)
same => n,Hangup()

exten => _8X.,1,Answer()
same => n,Gosub(macro-user-callerid,s,1())
same => n,Set(VOLUME(TX)=3)
same => n,MP3Player(http://piville.home/local/pbx.cgi?exten=${EXTEN})
same => n,Hangup()

exten => 444,1,Answer()
same => n,Gosub(macro-user-callerid,s,1())
same => n,Set(VOLUME(TX)=2)
same => n,Playback(xlate/hello-en&xlate/hello-es)
same => n(xlateloop),Read(MYCHOICE,xlate/press1-en&xlate/press2-es,1)
same => n,GotoIf($["${READSTATUS}" = "TIMEOUT"]?xlateloop)
same => n,GotoIf($["${READSTATUS}" != "OK"]?xlatebye)
same => n,If($["${MYCHOICE}" = "1"])
same => n,Set(lang=en-es)
same => n,ExitIf()
same => n,ElseIf($["${MYCHOICE}" = "2"])
same => n,Set(lang=es-en)
same => n,Else()
same => n,Goto(xlateloop)
same => n,EndIf()
same => n,Playback(xlate/start-${lang:0:2})
same => n,Record(/tmp/xlate%d:wav,3,,y)
same => n,Playback(xlate/working-${lang:0:2})
same => n,AGI(xlateagi.py,${RECORDED_FILE}.wav,${lang}.mp3,${lang})
same => n,Playback(${RECORDED_FILE}-${lang})
same => n,Goto(xlateloop)
same => n(xlatebye),Playback(xlate/bye)
same => n,Hangup()
EOF
