#!/usr/bin/python3
# Script for monitoring availability of F5 pools and reporting status in Nagios and Icinga
#
# Written by Chase Smith
import json, os, sys
from optparse import OptionParser,OptionGroup

version='20200818'
StatusCodes = { 0: "OK" , 1: "WARNING", 2: "CRITICAL", 3: "UNKNOWN"}

def getopts():
  global host, env, user, password, pool, warning, critical, verbose
  usage = "usage: %prog -H host -U user -P password -p pool\n" \
    "example: %prog -H host -U root -P password\n\n" \
    "or, verbosely:\n\n" \
    "usage: %prog --host=host --user=user --pass=password [--verbose --stats]\n"

  parser = OptionParser(usage=usage, version="%prog "+version)
  group1 = OptionGroup(parser, 'Mandatory parameters')
  group2 = OptionGroup(parser, 'Optional parameters')

  group1.add_option("-H", "--host", dest="host", help="report on HOST", metavar="HOST")
  group1.add_option("-e", "--env", dest="env", help="environment", metavar="ENV")
  group1.add_option("-U", "--user", dest="user", help="user to connect as", metavar="USER")
  group1.add_option("-P", "--pass", dest="password", help="password of -U user", metavar="PASS")
  group1.add_option("-p", "--pool", dest="pool", help="pool to check", metavar="POOL")
  group1.add_option("-W", "--warning", dest="ConnectionsWarning", help="warning percent of connections", metavar="ConnectionsWarning")
  group1.add_option("-C", "--critical", dest="ConnectionsCritical", help="critical percent of connections", metavar="ConnectionsCritical")

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

def getExitMessage():
  ExitCode = 0
  ExitMsg = ""
  availabilityMsg = ""
  connectionMsg = ""
  membersMsg = ""

  #check availabilty
  if availabilityState != "available":
    ExitCode = 2
    availabilityMsg += "'{pool}' pool is not available".format(pool=pool)

  #check members
  if activeMembers < totalMembers:
    ExitCode = (1, ExitCode)[ExitCode > 1]
    membersMsg += "'{pool}' active members is less than total members.".format(pool=options.pool)
    if options.verbose:
      membersMsg += "( active:{active}, total:{total} )".format(active=activeMembers, total=totalMembers)

  #check connections
  if currentConnections >= round(maxConnections / 100 * float(options.ConnectionsCritical)):
    ExitCode = 2
    connectionMsg += "'{pool}' current connections are over {ConnectionsCritical}% of pool maximum".format(pool=options.pool, ConnectionsCritical=options.ConnectionsCritical)
  elif currentConnections >= round(maxConnections / 100 * float(options.ConnectionsWarning)):
    ExitCode = (1, ExitCode)[ExitCode > 1]
    connectionMsg += "'{pool}' current connections are over {ConnectionsWarning}% of pool maximum".format(pool=options.pool, ConnectionsWarning=options.ConnectionsWarning)
  else:
    ExitCode = (0, ExitCode)[ExitCode > 0]

  #Set message
  if availabilityMsg:
    ExitMsg += " -- {availabilityMsg}".format(availabilityMsg=availabilityMsg)  
  if membersMsg:
    ExitMsg += " -- {membersMsg}".format(membersMsg=membersMsg)
  if connectionMsg:
    ExitMsg += " -- {connectionMsg}".format(connectionMsg=connectionMsg)
  if not ExitMsg:
    ExitMsg += " -- {pool}".format(pool=options.pool)
  return ExitCode, ExitMsg


options = getopts()
try:
  poolStatsCurl = "curl -k -s -u {user}:{password} -X GET https://{host}/mgmt/tm/ltm/pool/~{env}~{pool}/stats".format(user=options.user, password=options.password, host=options.host, env=options.env, pool=options.pool)
  stats_json = json.loads(os.popen(poolStatsCurl).read())
  stats = stats_json['entries']['https://localhost/mgmt/tm/ltm/pool/~{env}~{pool}/stats'.format(env=options.env, pool=options.pool)]['nestedStats']['entries']
  activeMembers = stats['activeMemberCnt']['value']
  totalMembers = stats['memberCnt']['value']
  availabilityState = stats['status.availabilityState']['description']
  currentConnections = stats['serverside.curConns']['value']
  maxConnections = stats['serverside.maxConns']['value']

except ValueError:
  print("UNKNOWN -- No JSON object could be decoded")
  sys.exit(3)

except:
  print("UNKNOWN -- an error occured")
  sys.exit(3)

def main():
  ExitCode, ExitMsg = getExitMessage()
  print("{}{}".format(StatusCodes[ExitCode], ExitMsg))
  sys.exit(ExitCode)

main()

