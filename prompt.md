if the BU_INDICATOR == 'bu_multi_manager'  
  then we need to fetch from the config.ini file all the bu's number (461 is the only one right now)
    then run this query:
select distinct tz_menahel_snif from mizrahi_custom.referant
where mispar_snif =:bu
this query will return the ID's of the relevant branch manager that we will need to pass
(one by one) to the query that we have in the sql_query field with tz_menahel_snif = "relevant_ID"
then fetch the datas and send to the relevant email (relevant branch manager only)


select distinct tz_menahel_snif from mizrahi_custom.referant
where mispar_snif =:bu


also, need to config a report that must be sent anyway even if empty (shows linked accounts):
63