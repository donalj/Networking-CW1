cat canada.txt | while read line; do
	echo "Performing traceroute to $line"
	traceroute  $line | tail -n+2 | awk '{ print $2 "," $3 }'|sed -e "s/(//" -e "s/)//"> "Canada/traceroutes/$line.txt"
	echo "Traceroute saved to $line.txt"
	echo ""
done
