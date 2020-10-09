# check_pg_duration.py

check_pg_duration.py is a Nagios check to alert on postgres queries that exceed a given time or quantity threshold

## Installation

Download the desired script from this page. The check is written in Python3, but is easily converted to Python2 if needed. Install the check in your nagios plugin path, and configure it as you would any other check.

### Postgres Setup

It is recommended to create a new user within postgres for use with nagios. In these steps we will use u_nagios as the user, but yours can be called whatever you decide. First login to the server as postgres and open `psql`, then execute the commands below.

`CREATE ROLE u_nagios;`

`CREATE FUNCTION get_pg_stat_activity() RETURNS SETOF pg_stat_activity AS $$ SELECT * FROM pg_catalog.pg_stat_activity; $$ LANGUAGE sql VOLATILE SECURITY DEFINER;`

`CREATE VIEW pg_stat_activity_unpriv AS SELECT * FROM get_pg_stat_activity();`

`GRANT SELECT ON pg_stat_activity_unpriv TO u_nagios;`

### NRPE
In the home directory of the nrpe user on your system, create a `.pgpass` file with the following format, substituting your own password:

```bash
# hostname:port:database:username:password
*:*:*:u_nagios:password123
```


## Usage

### Parameters
`-u, --username` - `username to connect to database`

`-w, --wtime` - `amount of time for warning in seconds`

`-C, --critical` - `number of queries for critical`

### Sample Usage and Output


`./check_pg_duration.py -w 15 -C 2 -u u_nagios`
~~~text
WARNING - there are 1 long-running queries
  pid: 1234, duration: 0:00:29.491165, state: active
~~~

` ./check_pg_duration.py -w 15 -C 2 -u u_nagios --verbose`
~~~text
CRITICAL - there are 2 long-running queries
  pid: 8821, duration: 0:00:15.870160, state: active
    query: select pg_sleep(20);
  pid: 9725, duration: 0:00:23.464703, state: active
    query: select pg_sleep(30);
~~~
