-- Query to get Oracle Database Connection Information
-- Run this query in SQL*Plus, SQL Developer, or any Oracle client

-- Method 1: Get all connection details in one query
SELECT 
    'HOST' AS CONFIG_KEY,
    UPPER(SYS_CONTEXT('USERENV', 'SERVER_HOST')) AS CONFIG_VALUE
FROM DUAL
UNION ALL
SELECT 
    'PORT' AS CONFIG_KEY,
    TO_CHAR(REGEXP_SUBSTR(UTL_INADDR.get_host_address, '[0-9]+$')) AS CONFIG_VALUE
FROM DUAL
UNION ALL
SELECT 
    'SERVICE_NAME' AS CONFIG_KEY,
    SYS_CONTEXT('USERENV', 'SERVICE_NAME') AS CONFIG_VALUE
FROM DUAL
UNION ALL
SELECT 
    'INSTANCE_NAME' AS CONFIG_KEY,
    SYS_CONTEXT('USERENV', 'INSTANCE_NAME') AS CONFIG_VALUE
FROM DUAL;

-- Method 2: Simpler query using v$instance and v$parameter
SELECT 
    'host' AS config_key,
    UPPER(HOST_NAME) AS config_value
FROM v$instance
UNION ALL
SELECT 
    'port' AS config_key,
    TO_CHAR(VALUE) AS config_value
FROM v$parameter
WHERE NAME = 'local_listener'
UNION ALL
SELECT 
    'service_name' AS config_key,
    VALUE AS config_value
FROM v$parameter
WHERE NAME = 'service_names';

-- Method 3: Most reliable - Get service name from v$services
SELECT 
    'host' AS config_key,
    UPPER(HOST_NAME) AS config_value
FROM v$instance
UNION ALL
SELECT 
    'port' AS config_key,
    SUBSTR(REGEXP_SUBSTR(VALUE, '[0-9]+'), 1, 10) AS config_value
FROM v$parameter
WHERE NAME = 'local_listener'
UNION ALL
SELECT 
    'service_name' AS config_key,
    NAME AS config_value
FROM v$services
WHERE NAME NOT LIKE 'SYS%'
  AND NAME NOT LIKE 'XDB%'
ORDER BY config_key;

-- Method 4: Simplest - Just get the service name (most common need)
SELECT NAME AS service_name
FROM v$services
WHERE NAME NOT LIKE 'SYS%'
  AND NAME NOT LIKE 'XDB%'
ORDER BY NAME;

