# Control-M Configuration Update Required

## Update process_config.sh

Add the following line to `/opt/actimize/ControlM/process_config.sh`:

```bash
REPORT_GENERATOR_MAIN=/opt/report_generator/main.py
```

## Script Deployment

The standardized shell scripts have been created in `/opt/report_generator/shell/` and should be copied to the Control-M directory structure:

**Target location:** `/opt/actimize/ControlM/report_generator/`

**Scripts to copy:**
- Send_Daily_Reports.sh
- Send_TwiceADay_Reports.sh
- Send_Weekly_Reports.sh
- Send_Monthly_Reports.sh
- Send_Quaterly_Reports.sh
- Send_Yearly_Reports.sh

**Note:** Ensure the scripts have execute permissions after copying:
```bash
chmod +x /opt/actimize/ControlM/report_generator/*.sh
```

## Changes Summary

1. **main.py** - Updated to accept `dd/mm/yyyy` date format instead of `yyyy-mm-dd`
2. **All shell scripts** - Standardized to follow demo.sh template:
   - Source process_config.sh and functions.sh
   - Set up LD_LIBRARY_PATH
   - Use standardized date logging format
   - Use `$REPORT_GENERATOR_MAIN` variable for path management
   - Use `dd/mm/yyyy` date format (`date +%d/%m/%Y`)
   - Proper error handling with exit codes
