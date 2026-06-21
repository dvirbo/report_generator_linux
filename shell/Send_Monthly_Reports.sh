#!/bin/bash

date '+%m/%d/%y %H:%M:%S Start running processes..'

. /opt/actimize/ControlM/process_config.sh
. /opt/actimize/ControlM/functions.sh

export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$AIS_UTILITIES_FOLDER

#######################################################################################################################################################################

date '+%m/%d/%y %H:%M:%S Starpython3 $REPORT_GENERATOR_MAIN monthly "$t - Send_Monthly_Reports'
(date +%d/%m/%Y)"

if [ $? != 0 ]; then 
    date '+%m/%d/%y %H:%M:%S Error in Send_Monthly_Reports run'
    exit 1
fi

#######################################################################################################################################################################
