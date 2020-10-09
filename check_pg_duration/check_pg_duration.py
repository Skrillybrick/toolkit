#!/usr/bin/python3
#
# Custom Nagios check to alert on queries running longer than desired.
# Written by Chase Smith
#
# This check will alert warning if any queries at all go beyond
# the specified duration using the --wtime flag
# It will alert critical if there are a number of long running
# queries that exceed the threshold set by the --critical flag
#
# Parameters:
#   - username
#   - duration warning
#   - critical number of queries
#
# Sample usages and outputs:
# The below examples set the time threshold to 15 seconds, and the critical number of queries to 2
#----------------------------------------------------------------------------------------------------
# ./check_pg_duration.py -w 15 -C 2 -u u_nagios
#
# WARNING - there are 1 long-running queries
#   pid: 1234, duration: 0:00:29.491165, state: active
#----------------------------------------------------------------------------------------------------
# ./check_pg_duration.py -w 15 -C 2 -u u_nagios --verbose
#
# CRITICAL - there are 2 long-running queries
#   pid: 8821, duration: 0:00:15.870160, state: active
#     query: select pg_sleep(20);
#   pid: 9725, duration: 0:00:23.464703, state: active
#     query: select pg_sleep(30);
import psycopg2
import sys
from optparse import OptionParser,OptionGroup

version='1.1-202010'
StatusCodes = { 0: "OK" ,
                1: "WARNING",
                2: "CRITICAL",
                3: "UNKNOWN" }

#Get options from command line flags
def getopts():
  global user, password, wtime, critical, verbose#, dbname, host
  usage = "usage: %prog -u user -w warning -C critical\n" \
    "or, verbosely:\n\n" \
    "usage: %prog --host=host user=user --warning=warning --critical=critical [ --verbose ]\n"

  parser = OptionParser(usage=usage, version="%prog "+version)
  group1 = OptionGroup(parser, 'Mandatory parameters')
  group2 = OptionGroup(parser, 'Optional parameters')

  group1.add_option("-u", "--username", dest="username", help="username to connect to database", metavar="USERNAME")
  group1.add_option("-w", "--wtime", dest="wtime", help="amount of time for warning", metavar="WTIME")
  group1.add_option("-C", "--critical", dest="critical", help="number of queries for critical", metavar="CRITICAL")

  group2.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, \
      help="show complete query")

  parser.add_option_group(group1)
  parser.add_option_group(group2)

  if len(sys.argv) < 2:
    print "no parameters specified\n"
    parser.print_help()
    sys.exit(-1)
  (options, args) = parser.parse_args()
  return options

#Establish connection to host and database, then execute query on pg_stat_activity_unpriv table; return results in dictionary
def connect(opts=getopts()):
  conn = psycopg2.connect("host={host} dbname={dbname} user={user} password={password}".format(host=opts.host, dbname=opts.dbname, user=opts.username, password=opts.password))
  cursor = conn.cursor()
  cursor.execute("""
    SELECT pid, now() - pg_stat_activity_unpriv.query_start AS duration, query, state 
    FROM pg_stat_activity_unpriv
    WHERE (now() - pg_stat_activity_unpriv.query_start) > interval '{wtime} seconds' AND state != 'idle';
    """.format(wtime=opts.wtime))
  columns = ( 'pid', 'duration', 'query', 'state' )
  results = []
  
  for row in cursor.fetchall():
    results.append(dict(zip(columns, row)))

  cursor.close()
  conn.close()

  return results

#Determine ExitCode, ExitMsg for check; return ExitCode, len(results), ExitMsg to calling function
def getExitMessage(results):
  ExitCode = 0
  ExitMsg = ''
  opts = getopts()
  if len(results) > 0:
    if opts.critical:
      ExitCode = (1, 2)[len(results) >= int(opts.critical)]
    else:
      ExitCode = 1
    for result in results:
      if opts.verbose:
        ExitMsg += "\n  pid: {pid}, duration: {duration}, state: {state}\n    - query: {query}".format(pid=result['pid'], duration=result['duration'], state=result['state'], query=result['query'])
      else:
        ExitMsg += "\n  pid: {pid}, duration: {duration}, state: {state}".format(pid=result['pid'], duration=result['duration'], state=result['state'])
  return ExitCode, len(results), ExitMsg


def main():
  #Call getExitMessage with connect() function as parameter
  ExitCode, Number, ExitMsg = getExitMessage(connect())
  #Print human readable output of check
  print("{} - there are {} long-running queries{}".format(StatusCodes[ExitCode], Number, ExitMsg))
  #Send exit code to system
  sys.exit(ExitCode)


if __name__ == "__main__":
  main()

