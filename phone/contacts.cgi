#!/bin/ksh

echo -e "Content-Type: text/plain\n"

cat contacts.csv

(
echo '<select id="contacts" class="stack" onchange="destination.value=this.value;">'
while IFS="," read dest type ext
do
	[[ "$type" == @(Type) ]] && continue
	s=""; [[ "$ext" == \*60 ]] && s="selected"
	echo "<option value=\"$ext\" $s>$type: $dest</option>"
done <contacts.csv
echo '</select>'
echo '<input class="stack" type="text" id="destination" value="*60">'
) >contacts-browser.html

(
echo '<table>'
echo '<caption align="top" style="font-weight: bold; font-size: 150%;""></caption>'
echo '<tr><th>Destination</th><th>Extension</th></tr>'
while IFS="," read dest type ext
do
	[[ "$type" == @(Type) ]] && continue
	echo "<tr><td>$type: $dest</td><td>$ext</td></tr>"
done <contacts.csv
echo '</table>'
) >contacts-linphone.html
