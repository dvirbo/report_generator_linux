#!/bin/bash

date '+%m/%d/%y %H:%M:%S Start running processes..'

. /opt/actimize/ControlM/process_config.sh
. /opt/actimize/ControlM/functions.sh

export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$AIS_UTILITIES_FOLDER

#######################################################################################################################################################################

date '+%m/%d/%y %H:%M:%S Start - Send_Daily_Reports'

# Check if date parameter is provided for last_bd
if [ -z "$1" ]; then
    date '+%m/%d/%y %H:%M:%S Error: Date parameter is required for last_bd interval'
    exit 1
fi

DATE_PARAM="$1"
CURRENT_DATE=$(date -d "yesterday" +%d/%m/%Y)

# Run last_bd reports with provided date parameter
date '+%m/%d/%y %H:%M:%S Running last_bd reports with date: '"$DATE_PARAM"
python3 $REPORT_GENERATOR_MAIN last_bd "$DATE_PARAM"
last_bd_exit_code=$?

if [ $last_bd_exit_code != 0 ]; then 
    date '+%m/%d/%y %H:%M:%S Error in last_bd reports run'
fi

# Run daily reports with current system date
date '+%m/%d/%y %H:%M:%S Running daily reports with date: '"$CURRENT_DATE"
python3 $REPORT_GENERATOR_MAIN daily "$CURRENT_DATE"
daily_exit_code=$?

if [ $daily_exit_code != 0 ]; then 
    date '+%m/%d/%y %H:%M:%S Error in daily reports run'
    exit 1
fi

#######################################################################################################################################################################
