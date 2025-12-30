-- SIMPLEST QUERY - Get Oracle Connection Info
-- Copy the results to your config.ini file

-- Get Host Name
SELECT 'host = ' || UPPER(HOST_NAME) AS config_line
FROM v$instance;

-- Get Port (from listener)
SELECT 'port = ' || SUBSTR(REGEXP_SUBSTR(VALUE, '[0-9]+'), 1, 10) AS config_line
FROM v$parameter
WHERE NAME = 'local_listener';

-- Get Service Name
SELECT 'service_name = ' || NAME AS config_line
FROM v$services
WHERE NAME NOT LIKE 'SYS%'
  AND NAME NOT LIKE 'XDB%'
  AND ROWNUM = 1
ORDER BY NAME;

