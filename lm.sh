#!/usr/bin/env bash

# Pre-requisits:
# Environment variables must be set for all programs 
#   listed in the `name` array with _DIR appended
#   eg RFM_ECOMANAGER_LOGGER_DIR

echo ""

name[0]="RFM_ECOMANAGER_LOGGER"
name[1]="POWERSTATS"
name[2]="BABYSITTER"

length=${#name[@]} # length of array `name`

# create a `directory` array with the actual directoryies
for (( i=0; i<$length; i++ ))
do
    subst="${name[$i]}_DIR"
    directory[$i]="${!subst}"
done

# sanity checks
echo "Running sanity checks..."
for (( i=0; i<$length; i++ ))
do
    if [ -z "$directory[$i]" ]
    then
	echo "* ERROR: ${name[$i]} directory is not set!"
	exit 1
    else
	if [ -d "${directory[$i]}" ]
	then
	    echo "* ${name[$i]}_DIR set to ${directory[$i]} which is a valid directory"
	else
	    echo "* ERROR: ${name[$i]}_DIR set to ${directory[$i]} WHICH IS NOT A DIRECTORY"
	    exit 1
	fi
    fi
done
echo -e "...all sanity checks passed!\n"

case "$1" in # switch on the first command

"update")
	echo "Updating code from github"
	for (( i=0; i<$length; i++ ))
	do
	    echo ""
	    echo "Updating ${name[$i]}"
	    cd ${directory[$i]} && git pull
	    if [ $? -ne 0 ]
	    then
		echo "ERROR. lm.sh script cannot finished. Please see above for error details."
		exit 1
	    fi
	done
	;;

esac # end of case

echo -e "\nAll done\n"