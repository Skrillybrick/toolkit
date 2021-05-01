#!/usr/bin/python
""" Script for monitoring availability of F5 pools and reporting status in Nagios and Icinga """

__author__ = "Chase Smith"
__version__ = "2.0.0"

import base64
import os
import re
import requests
import sys
import urllib3
from optparse import OptionParser, OptionGroup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

StatusCodes = {0: "OK",
               1: "WARNING",
               2: "CRITICAL",
               3: "UNKNOWN"}

def getopts():
    """Get command-line arguments and assign to values that will be used in the check."""
    global host, env, user, password, pool, warning, critical, verbose
    usage = "usage: %prog -H host -e env -U user -P password -p pool\n" \
            "or, verbosely:\n\n" \
            "usage: %prog --host=host --user=user --pass=password --pool=pool [ --verbose --members ]\n"

    parser = OptionParser(usage=usage, version="%prog {__version__}".format(__version__=__version__))
    group1 = OptionGroup(parser, "Mandatory parameters")
    group2 = OptionGroup(parser, "Optional parameters")

    group1.add_option("-H", "--host", dest="host", help="report on HOST", metavar="HOST")
    group1.add_option("-e", "--env", dest="env", help="environment", metavar="ENV")
    group1.add_option("-U", "--user", dest="user", help="user to connect as", metavar="USER")
    group1.add_option("-P", "--pass", dest="password", help="password of -U user", metavar="PASS")
    group1.add_option("-p", "--pool", dest="pool", help="pool to check", metavar="POOL")
    group1.add_option("-W", "--warning", dest="ConnectionsWarning", help="warning percent of connections",
                      metavar="ConnectionsWarning")
    group1.add_option("-C", "--critical", dest="ConnectionsCritical", help="critical percent of connections",
                      metavar="ConnectionsCritical")

    group2.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="print extended output to stdout")
    group2.add_option("-m", "--members", action="store_true", dest="members", default=False,
                      help="show members statistics")

    parser.add_option_group(group1)
    parser.add_option_group(group2)

    if len(sys.argv) < 2:
        print("no parameters specified\n")
        parser.print_help()
        sys.exit(-1)
    (options, args) = parser.parse_args()
    return options


def get_exit_message(active_members, total_members, availability_state, current_connections, max_connections, opts):
    """Get exit message and exit code"""
    exit_code = 0
    exit_msg = ""
    availability_msg = ""
    connection_msg = ""
    members_msg = ""

    # Check availabilty
    if availability_state != "available":
        exit_code = 2
        availability_msg += "'{pool}' pool is not available".format(pool=pool)

    # Check members
    if active_members < total_members:
        exit_code = (1, exit_code)[exit_code > 1]
        members_msg += "'{pool}' active members is less than total members.".format(pool=opts.pool)
    if opts.verbose:
        members_msg += "( active:{active}, total:{total} )".format(active=active_members, total=total_members)

    # Check connections
    if current_connections >= round(max_connections / 100 * float(opts.ConnectionsCritical)):
        exit_code = 2
        connection_msg += "'{pool}' current connections are over {ConnectionsCritical}% of pool maximum".format(
            pool=opts.pool, ConnectionsCritical=opts.ConnectionsCritical)
    elif current_connections >= round(max_connections / 100 * float(opts.ConnectionsWarning)):
        exit_code = (1, exit_code)[exit_code > 1]
        connection_msg += "'{pool}' current connections are over {ConnectionsWarning}% of pool maximum".format(
            pool=opts.pool, ConnectionsWarning=opts.ConnectionsWarning)
    else:
        exit_code = (0, exit_code)[exit_code > 0]
    if opts.verbose:
        connection_msg += " ({connections} / {max})".format(connections=current_connections, max=max_connections)

    # Set message
    if availability_msg:
        exit_msg += " -- {availabilityMsg}".format(availabilityMsg=availability_msg)
    if members_msg:
        exit_msg += " -- {membersMsg}".format(membersMsg=members_msg)
    if connection_msg:
        exit_msg += " -- {connectionMsg}".format(connectionMsg=connection_msg)
    if not exit_msg:
        exit_msg += " -- {pool}".format(pool=opts.pool)
    return exit_code, exit_msg


def main():
    opts = getopts()
    userpass = "{user}:{password}".format(user=user, password=password).encode('ascii')
    auth = base64.b64encode(userpass).decode('ascii')
    header = "Authorization: Basic {auth}".format(auth=auth)
    try:
        pool_stats = requests.get("https://{host}/mgmt/tm/ltm/pool/~{env}~{pool}/stats".format(
            host=opts.host, env=opts.env, pool=opts.pool), header=header, verify=False)
        stats = pool_stats.json()["entries"]["https://localhost/mgmt/tm/ltm/pool/~{env}~{pool}/stats".format(
            env=opts.env, pool=opts.pool)]["nestedStats"]["entries"]
        active_members = stats["activeMemberCnt"]["value"]
        total_members = stats["memberCnt"]["value"]
        availability_state = stats["status.availability_state"]["description"]
        current_connections = stats["serverside.curConns"]["value"]
        max_connections = stats["serverside.maxConns"]["value"]

    except ValueError:
        print("UNKNOWN -- No JSON object could be decoded")
        sys.exit(3)

    except Exception:
        print("UNKNOWN -- an error occurred")
        sys.exit(3)

    exit_code, exit_msg = get_exit_message(active_members, total_members, availability_state,
                                           current_connections, max_connections, opts)

    if opts.members:
        members = requests.get("https://{host}/mgmt/tm/ltm/pool/~{env}~{pool}/members/stats".format(
            host=opts.host, env=opts.env, pool=opts.pool), header=header, verify=False)
        for k, v in members.json()["entries"].items():
            exit_msg += "\n\t {} - {} ".format(re.sub("/Prod/", "", v["nestedStats"]["entries"]["nodeName"]["description"]),
                                               v["nestedStats"]["entries"]["serverside.curConns"]["value"])
    print(StatusCodes[exit_code], exit_msg)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

