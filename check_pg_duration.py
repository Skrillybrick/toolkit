#!/usr/bin/python3
#
# Custom Nagios/Icinga check to alert on queries running longer than desired.
# Written by Chase Smith
#
# Parameters:
#   - host
#   - dbname
#   - username
#   - password
#   - duration warning
#   - critical number of queries

import psycopg2
import sys
from optparse import OptionParser,OptionGroup

version='1.0-202009'
StatusCodes = { 0: "OK" , 
                1: "WARNING", 
                2: "CRITICAL", 
                3: "UNKNOWN" }


def getopts():
  global host, dbname, user, password, wtime, critical, verbose
  usage = "usage: %prog -H host -d dbname -u user -p password -p pool\n" \
    "or, verbosely:\n\n" \
    "usage: %prog --host=host --dbname=dbname user=user --pass=password --warning=warning --critical=critical [ --verbose ]\n"

  parser = OptionParser(usage=usage, version="%prog "+version)
  group1 = OptionGroup(parser, 'Mandatory parameters')
  group2 = OptionGroup(parser, 'Optional parameters')

  group1.add_option("-u", "--username", dest="username", help="username to connect to database", metavar="USERNAME")
  group1.add_option("-p", "--password", dest="password", help="password to connect to database", metavar="PASSWORD")
  group1.add_option("-H", "--host", dest="host", help="hostname location of database", metavar="HOST")
  group1.add_option("-d", "--dbname", dest="dbname", help="database name", metavar="DBNAME")
  group1.add_option("-w", "--wtime" dest="wtime", help="amount of time for warning", metavar="WTIME")
  group1.add_option("-C", "--critical", dest="critical", help="number of queries for critical", metavar="CRITICAL")

  group2.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, \
      help="print extended output to stdout")

  parser.add_option_group(group1)
  parser.add_option_group(group2)

  if len(sys.argv) < 2:
    print("no parameters specified\n")
    parser.print_help()
    sys.exit(-1)
  (options, args) = parser.parse_args()
  return options


def connect(opts=getopts()):
  conn = psycopg2.connect("host={host} dbname={dbname} user={user} password={password}".format(host=opts.host, dbname=opts.dbname, user=opts.username, password=opts.password))
  cursor = conn.cursor()
  cursor.execute("""
    SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state 
    FROM pg_stat_activity 
    WHERE (now() - pg_stat_activity.query_start) > interval '{wtime} seconds' AND state != 'idle';
    """.format(wtime=opts.wtime))
  columns = ( 'pid', 'duration', 'query', 'state' )
  results = []
  
  for row in cursor.fetchall():
    results.append(dict(zip(columns, row)))

  cursor.close()
  conn.close()

  return results


def getExitMessage(results):
  ExitCode = 0
  ExitMsg = ''
  opts = getopts()
  if len(results) > 0:
    ExitCode = (1, 2)[len(results) >= int(opts.critical)]
    for result in results:
      if opts.verbose:
        ExitMsg += "\n  pid: {pid}, duration: {duration}, state: {state}\n    - query: {query}".format(pid=result['pid'], duration=result['duration'], state=result['state'], query=result['query'])
      else:
        ExitMsg += "\n  pid: {pid}, duration: {duration}, state: {state}".format(pid=result['pid'], duration=result['duration'], state=result['state'])
  return ExitCode, len(results), ExitMsg


def main():
  ExitCode, Number, ExitMsg = getExitMessage(connect())
  print("{} - there are {} long-running queries{}".format(StatusCodes[ExitCode], Number, ExitMsg))
  sys.exit(ExitCode)


main()

