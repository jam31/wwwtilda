#!/usr/bin/env python
#
# Tilde project: cross-platform entry point
# this is a junction; all the end user actions are done from here
# v060813

import sys
import os
import subprocess
import json
import pprint

if sys.version_info < (2, 6):
    print '\n\nI cannot proceed. Your python is too old. At least version 2.6 is required!\n\n'
    sys.exit()

try: import argparse
except ImportError: from deps.argparse import argparse

try:
    from numpy import dot
    from numpy import array
except ImportError:
    print '\n\nI cannot proceed. Please, install numerical python (numpy)!\n\n'
    sys.exit()

try: import sqlite3
except ImportError:
    try: from pysqlite2 import dbapi2 as sqlite3
    except ImportError:
        print '\n\nI cannot proceed. Please, install python sqlite3 module!\n\n'
        sys.exit()

from settings import settings, userdbchoice, repositories, DATA_DIR
from common import html2str
from symmetry import DEFAULT_ACCURACY
from api import API


registered_modules = []
for appname in os.listdir( os.path.realpath(os.path.dirname(__file__) + '/../apps') ):
    if os.path.isfile( os.path.realpath(os.path.dirname(__file__) + '/../apps/' + appname + '/manifest.json') ):
        registered_modules.append(appname)

parser = argparse.ArgumentParser(prog="[tilde_script]", usage="%(prog)s [positional / optional arguments]", epilog="Version: "+API.version, argument_default=argparse.SUPPRESS)

parser.add_argument("path", action="store", help="Scan file(s) / folder(s) / matching-filename(s), divide by space", metavar="PATH(S)/FILE(S)", nargs='*', default=False)
parser.add_argument("-u", dest="daemon", action="store", help="run GUI service (default)", nargs='?', const='shell', default=False, choices=['shell', 'noshell'])
parser.add_argument("-a", dest="add", action="store", help="if PATH(S): add results to repository", type=str, metavar="REPOSITORY", nargs='?', const='DIALOG', default=False)
parser.add_argument("-r", dest="recursive", action="store", help="scan recursively", type=bool, metavar="", nargs='?', const=True, default=False)
parser.add_argument("-t", dest="terse", action="store", help="terse print", type=bool, metavar="", nargs='?', const=True, default=False)
parser.add_argument("-v", dest="verbose", action="store", help="verbose print", type=bool, metavar="", nargs='?', const=True, default=False)
parser.add_argument("-f", dest="freqs", action="store", help="if PATH(S): extract and print phonons", type=bool, metavar="", nargs='?', const=True, default=False)
parser.add_argument("-i", dest="info", action="store", help="if PATH(S): analyze all", type=bool, metavar="", nargs='?', const=True, default=False)
parser.add_argument("-m", dest="module", action="store", help="if PATH(S): invoke a module", nargs='?', const=False, default=False, choices=registered_modules)
parser.add_argument("-s", dest="structures", action="store", help="if PATH(S): show lattice", type=int, metavar="i", nargs='?', const=True, default=False)
parser.add_argument("-c", dest="cif", action="store", help="if FILE: save i-th CIF structure in \"data\" folder", type=int, metavar="i", nargs='?', const=-1, default=False)
parser.add_argument("-y", dest="symprec", action="store", help="symmetry tolerance (default %.01e)" % DEFAULT_ACCURACY, type=float, metavar="N", nargs='?', const=None, default=None)
parser.add_argument("-x", dest="xdebug", action="store", help="debug", type=bool, metavar="", nargs='?', const=True, default=None)
parser.add_argument("-d", dest="datamining", action="store", help="datamining query", type=str, metavar="QUERY", nargs='?', const='SELECT COUNT(*) FROM results', default=None)

args = parser.parse_args()

# GUI:
# run GUI service daemon if no other commands are given

if not args.path and not args.daemon and not args.datamining: #if not len(vars(args)):
    args.daemon = 'shell'
if args.daemon:
    print "\nPlease, wait a bit while Tilde application is starting.....\n"

    # invoke windows GUI frame
    if args.daemon == 'shell' and 'win' in sys.platform and not settings['debug_regime'] and not settings['demo_regime']:
       subprocess.Popen(sys.executable + ' ' + os.path.realpath(os.path.dirname(__file__)) + '/winui.py')

    # replace current process with Tilde daemon process
    try:
        os.execv(sys.executable, [sys.executable, os.path.realpath(os.path.dirname(__file__)) + '/daemon.py'])
    except OSError: # taken from Tornado
        os.spawnv(os.P_NOWAIT, sys.executable, [sys.executable, os.path.realpath(os.path.dirname(__file__)) + '/daemon.py'])

    sys.exit()

if not args.path and not args.datamining:
    parser.print_help()
    sys.exit()

if args.cif:
    from core.common import write_cif


# CLI:
# if there are commands, run command-line text interface
    
db = None
if args.add:
    if args.add == 'DIALOG':
        uc = userdbchoice(repositories)
    else:
        uc = userdbchoice(repositories, choice=args.add)

    if not os.access(os.path.abspath(DATA_DIR + os.sep + uc), os.W_OK):
        raise RuntimeError("Sorry, database file is write-protected!")
        
    db = sqlite3.connect(os.path.abspath(DATA_DIR + os.sep + uc))
    db.row_factory = sqlite3.Row
    db.text_factory = str
    
    print "The database selected:", uc
    
if args.datamining:
    uc = userdbchoice(repositories, create_allowed=False)
    
    db = sqlite3.connect(os.path.abspath(DATA_DIR + os.sep + uc))
    db.row_factory = sqlite3.Row
    db.text_factory = str
    
    print "The database selected:", uc


Tilde = API(db_conn=db, settings=settings)

DIV = "~"*75

if args.path:
    if settings['skip_unfinished']: finalized = 'YES'
    else: finalized = 'NO'
    print "Only finalized:", finalized, "and skip paths if they start/end with any of:", settings['skip_if_path']


if args.datamining:
    N = 10
    output = {}
    cursor = db.cursor()
    #try: cursor.execute( 'SELECT info, energy, apps FROM results WHERE energy IN (SELECT energy FROM results WHERE energy != "" ORDER BY energy LIMIT '+str(N)+')' )
    try: cursor.execute( args.datamining )
    except: print 'Fatal error: ' + "%s" % sys.exc_info()[1]
    else:
        result = cursor.fetchall()        
        for row in result:
            for key in row.keys():
                if not key in output: output[key] = []
                output[key].append( row[key] )
    #output = sorted(output, key=lambda x: x[0])
    
    pprint.pprint( output )
    print DIV    
    sys.exit()


for target in args.path:

    tasks = Tilde.savvyize(target, recursive=args.recursive, stemma=True)

    for task in tasks:
        filename = os.path.basename(task)
        add_msg = ''

        calc, error = Tilde.parse(task)
        if error:
            if args.terse and 'nothing found' in error: continue
            else: print filename, error
            continue

        calc, error = Tilde.classify(calc, args.symprec)
        if error:
            print filename, error
            continue

        output_line = filename + " (E=" + str(calc.energy) + " eV)"
        if calc.info['warns']: add_msg = " (" + " ".join(calc.info['warns']) + ")"

        if args.add:
            checksum, error = Tilde.save(calc)
            if error:
                print filename, error
                continue
            output_line += ' added'

        print output_line + add_msg

        if args.info:
            found_topics = []
            for n, i in enumerate(Tilde.hierarchy):
                if '#' in i['source']:
                    n=0
                    while 1:
                        try: topic = calc.info[ i['source'].replace('#', str(n)) ]
                        except KeyError:
                            if 'negative_tagging' in i and n==0: found_topics.append( [ i['category'], 'none' ] )
                            break
                        else:
                            if n==0: found_topics.append( [ i['category'], topic ] )
                            else: found_topics[-1].append( topic )
                            n+=1
                else:
                    try: found_topics.append( [   i['category'], calc.info[ i['source'] ]   ] )
                    except KeyError:
                        if 'negative_tagging' in i: found_topics.append( [ i['category'], 'none' ] )

            found_topics.append( ['code', calc.info['prog']] )
            if calc.info['duration']: found_topics.append( ['modeling time', calc.info['duration'] + ' hour(s)'] )
            if calc.info['perf']: found_topics.append( ['parsing time', calc.info['perf'] + ' sec(s)'] )

            j, out = 0, ''
            for t in found_topics:
                t = map(html2str, t)
                out += "  " + t[0] + ': ' + ', '.join(t[1:])
                out += "\t" if not j%2 else "\n"
                j+=1
            print out[:-1]
            print DIV

        if args.verbose:
            if calc.convergence:
                print str(calc.convergence)
            if calc.tresholds:
                for i in range(len(calc.tresholds)):
                    print "%1.2e" % calc.tresholds[i][0] + " "*2 + "%1.5f" % calc.tresholds[i][1] + " "*2 + "%1.4f" % calc.tresholds[i][2] + " "*2 + "%1.4f" % calc.tresholds[i][3] + " "*2 + "E=" + "%1.4f" % calc.tresholds[i][4] + " eV" + " "*2 + "("+str(calc.ncycles[i]) + ")"
                print DIV
            
        if args.structures:
            out = ''
            if len(calc.structures) > 1:
                out += str(calc.structures[0]['cell']) + ' -> '
            out += str(calc.structures[-1]['cell'])
            out += " V=" + str(calc.info['dims'])
            print out
            print DIV
        
        if args.cif and len(tasks) == 1:
            try: calc.structures[ args.cif ]
            except IndexError: print "Warning! Structure "+args.cif+" not found!"
            else:
                comment = calc.info['formula'] + " extracted from " + filename + " (structure no." + str(args.cif) + ")"
                cif_file = os.path.realpath(os.path.abspath(DATA_DIR + os.sep + filename)) + '_' + str(args.cif) + '.cif'
                if write_cif(calc.structures[ args.cif ]['cell'], calc.structures[ args.cif ]['atoms'], calc['symops'], cif_file, comment):
                    print cif_file + " ready"
                else:
                    print "Warning! " + cif_file + " cannot be written!"
            print DIV

        if args.module:
            hooks = Tilde.postprocess(calc)
            if args.module not in hooks: print "Module \"" + args.module + "\" is not suitable for this case (outside the scope defined in module manifest)!"
            else:
                print hooks[args.module]['error'] if hooks[args.module]['error'] else hooks[args.module]['data']
            print DIV
            
        if args.xdebug:
            print calc
            print DIV

        if args.freqs:
            if not calc.phonons['modes']:
                print 'No phonons here!'
                continue
            for bzpoint, frqset in calc.phonons['modes'].iteritems():
                print "\tK-POINT:", bzpoint
                compare = 0
                for i in range(len(frqset)):
                    # if compare == frqset[i]: continue
                    print "%d" % frqset[i] + " (" + calc.phonons['irreps'][bzpoint][i] + ")"
                    compare = frqset[i]
            print DIV
