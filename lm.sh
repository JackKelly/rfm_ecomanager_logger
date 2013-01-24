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

print_error()
{
    echo -e $1 >/dev/stderr
}

check_return_value ()
{
    if [ $? -ne 0 ]
    then
	print_error "ERROR. lm.sh script cannot finished. Please see above for error details."
	exit $?
    fi
}


check_directory ()
# Arguments: 1) path 2) variable name
{
    if [ -z "$1" ]
    then
	print_error "\n* ERROR: \$$2 directory is not set!\n"
	exit 1
    else
	if [ -d "${directory[$i]}" ]
	then
	    echo "* \$$2 set to $1 which is a valid directory"
	else
	    print_error "\n* ERROR: \$$2 set to $1 WHICH IS NOT A DIRECTORY\n"
	    exit 1
	fi
    fi    
}


check_process()
# Arguments: 1) process name
{
    check_return_value
    pgrep $1
    if [ $? -ne 0 ]
    then
	print_error "\nERROR: $1 failed to start!\n"
	return 1
    fi   
    return 0
}


start_process ()
# Arguments: 1) directory, 2) file within directory, 3) process name
{
    echo "Starting $1$2..."
    cd $1
    nohup $2 &
    check_process $3
    if [ $? -ne 0 ]
    then
	tail nohup.out >/dev/stderr
	echo ""
	exit 1
    fi
    echo "Successfully started $1$2"
}


# create a `directory` array with the actual directories and sanity check
echo "Running sanity checks..."
for (( i=0; i<$length; i++ ))
do
    subst="${name[$i]}_DIR"
    directory[$i]="${!subst}"
    check_directory "${directory[$i]}" "${name[$i]}_DIR"
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
	    check_return_value
	done
	;;

"flash")
	echo "Flashing Nanode with latest code from github"
	check_directory "$RFM_EDF_ECOMANAGER_DIR" "RFM_EDF_ECOMANAGER_DIR"
	echo "First, updating code from github:"
	cd "$RFM_EDF_ECOMANAGER_DIR" && git pull
	check_return_value
	echo "Running flash.sh script:"
	./flash.sh
	check_return_value
	;;

"start")
	start_process "$RFM_ECOMANAGER_LOGGER_DIR" "/rfm_ecomanager_logger/rfm_ecomanager_logger.py" "rfm_ecomanager_logger.py"
	start_process "$BABYSITTER_DIR" "/babysitter/babysitter.py" "babysitter.py"
	;;

esac # end of case


echo -e "\nAll done\n"