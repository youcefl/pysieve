# ****************************************************************************
# Copyright (c) 2013 Youcef Lemsafer
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# ****************************************************************************
# Creation date: 2013.11.11
# Created by: Youcef Lemsafer
# Authors: Youcef Lemsafer
# What it is: pysieve.py version 0.5.0
# A Python driver for my sieving work cause factoring big numbers is a lot
# of fun.
# ****************************************************************************
import argparse
import threading
import subprocess
import shutil
import os
import sys
import logging
import time
import datetime


# ****************************************************************************
# Output some informations
# ****************************************************************************
VERSION = '0.5.0'
NAME = 'pysieve.py'
print( NAME + ' version ' + VERSION )
print( 'Created by Youcef Lemsafer (Nov 2013).' )

# ****************************************************************************
# ****************************************************************************
# Set up logging
logger = logging.getLogger('pysieve')
logger.setLevel(logging.DEBUG)

# ****************************************************************************
# Command line definition
# ****************************************************************************
cmd_line_parser = argparse.ArgumentParser()
cmd_line_parser.add_argument( '-v', '--verbose', required = False
                            , action = 'store_true', default = False )
cmd_line_parser.add_argument( '-f', help = 'starting value of Q', type = int
                                , required = True)
cmd_line_parser.add_argument( '-c', help = 'length of the range to sieve'
                                    , type = int, required = True)
cmd_line_parser.add_argument( '-t', '--threads'
                                    , help = 'maximum number of threads'
                                    , type = int, required = True)
group = cmd_line_parser.add_mutually_exclusive_group(required = True)
group.add_argument( '-a', '--algebraic', help = 'instructs that the sieving'
                            + ' is to be done on the algebraic side'
                            , action='store_true' )
group.add_argument( '-r', '--rational', help = 'instructs that the sieving'
                            + ' is to be done on the rational side'
                            , action='store_true' )
cmd_line_parser.add_argument( '-s', '--unique-name', help =
                      'unique name used for output file name and temporary'
                    + ' file names', required = True)
cmd_line_parser.add_argument( '-l', '--lattice-siever'
                    , help = 'lattice siever to use (e.g. lasieve4I14e)'
                    , required = True
                    )
cmd_line_parser.add_argument( '-d', '--saving-delta'
                , help = 'size of range to processed before a saving occurs.'
                , type = int
                , default = 10000
                )
cmd_line_parser.add_argument( 'poly', help = '.poly file' )
arguments = cmd_line_parser.parse_args()


# ****************************************************************************
# prints a message and exits
# ****************************************************************************
def die(msg):
    logger.critical( msg )
    sys.exit(-1)


# ****************************************************************************
# Class holding parameters for a sieving subprocess
# ****************************************************************************
class SievingParameters:
    def __init__(self, siever_exe, unique_name, q_start, q_length
                        , sieve_type, poly, id):
        self.executable = siever_exe
        self.unique_name = unique_name
        self.q_start = q_start
        self.q_length = q_length
        self.sieve_type = sieve_type
        self.poly = poly
        self.poly_file = unique_name + '.poly.t' + str(id)
        self.id = id
        self.output_name = unique_name + '_' + str(q_start) \
                                + '_' + str(q_length) + '.out'
        self.return_code = -1


# ****************************************************************************
# ****************************************************************************
def run_siever(sieving_parameters):
    sp = sieving_parameters
    shutil.copyfile(sp.poly, sp.poly_file)
    cmd = sp.executable + ' -k -v -o ' + sp.output_name \
            + ' -n' + str(sp.id) + ' -f ' + str(sp.q_start) \
            + ' -c ' + str(sp.q_length) \
            + ' -' + sp.sieve_type \
            + ' -R ' + sp.poly_file
    # IDLE_PRIORITY_CLASS = 0x00000040
    proc = subprocess.Popen(cmd, creationflags = 0x40)
    logger.debug( '[pid:' + str(proc.pid).rjust(5) + '] ' + cmd )
    proc.wait()
    sp.return_code = proc.returncode
    logger.debug( 'Process [pid:' + str(proc.pid).rjust(5) + '] exited with'
            + ' code ' + str(sp.return_code) )


# ****************************************************************************
# Class holding a sieving thread
# ****************************************************************************
class Siever:
    def __init__(self, parameters):
        self.parameters = parameters
        self.thread = threading.Thread(
                                target = run_siever
                              , args=(parameters,)
                              )

    def start(self):
        self.thread.start()

    def wait(self):
        self.thread.join()

    def return_code(self):
        return self.return_code


# ****************************************************************************
# Appends the output files produced by the given sievers to the output file
# ****************************************************************************
def append_files(sievers, output_file_name):
    relations_count = 0
    with open( output_file_name, 'ab' ) as output_file:
        for s in sievers:
            logger.debug( 'Appending file ' + s.parameters.output_name
                    + ' to file ' + output_file_name )
            with open( s.parameters.output_name, 'rb' ) as relations_file:
                for line in relations_file:
                    output_file.write(line)
                    relations_count += 1
    return relations_count


# ****************************************************************************
# Deletes the files produced by a set of sievers
# ****************************************************************************
def delete_files(sievers):
    for s in sievers:
        try:
            # failure to remove file should not cause problem, just report it
            os.remove(s.parameters.output_name)
        except OSError:
            logger.warning( 'Failed to delete file `'
                            + s.parameters.output_name + '\'.'
                            )


# ****************************************************************************
# Returns true if the name corresponds to an existing accessible file
# otherwise returns false
# ****************************************************************************
def is_existing_file(name):
    try:
        with open(name) as file:
            return True
    except IOError:
        return False


# ****************************************************************************
# Sieves range [q_a, q_b)
# ****************************************************************************
def sieve(q_a, q_b, max_threads, siever_exe):
    logger.info(
        'Lattice sieving {0:s} q from {1:d} to {2:d} using {3:d} thread(s).'
            .format( 'algebraic' if arguments.algebraic else 'rational'
                   , q_a, q_b, max_threads
                   )
                )
    sievers = []
    delta = (q_b - q_a) // max_threads
    q_x = q_a
    id = 0
    sieve_type = 'a' if arguments.algebraic else 'r'
    while(q_x < q_b):
        q_y = q_x + delta
        if(q_y + delta >= q_b):
            q_y = q_y + (q_b - q_a) % delta
        params = SievingParameters( siever_exe, arguments.unique_name
                                  , q_x, q_y - q_x, sieve_type
                                  , arguments.poly, id
                                  )
        sievers.append(Siever(params))
        id += 1
        q_x = q_y

    for s in sievers:
        s.start()
    for s in sievers:
        s.wait()

    relations_count = append_files(sievers, arguments.unique_name + '.rels')
    logger.info( 'Found ' + str(relations_count) + ' relations.' )

    # Once a set of relation files have been appended to the output file
    # we get rid of them
    delete_files(sievers)
    # Write resume file
    resume_file_name = arguments.unique_name + '.resume'
    old_resume_file_name = resume_file_name + '.old'
    if is_existing_file(resume_file_name):
        os.replace(resume_file_name, old_resume_file_name)
    with open(resume_file_name, 'w') as resume_file:
        resume_file.write(str(q_b))

    return relations_count

# ****************************************************************************
# Reads q value from resume file
# ****************************************************************************
def get_q_from_file(file_name):
    if not is_existing_file(file_name):
        return 0
    with open(file_name, 'r') as f:
        return int(f.readline())

# ****************************************************************************
# Converts a number of seconds into a string formatted as follows:
# %dd %dh %dm %ds
# ****************************************************************************
def seconds_to_dhms(seconds):
    s = int(seconds)
    return '{0:d}d {1:d}h {2:d}m {3:d}s'.format(
                       s // 86400, (s % 86400) // 3600, (s % 3600) // 60
                     , s % 60
                     )


# ****************************************************************************
# Sieves from q0 to q0 + length
# This is the main sieve function
# ****************************************************************************
def main_sieve(q0, length, siever_exe):
    q_end = q0 + length
    # Read resume file to see whether we have to directly jump to a larger
    # value of q0
    q_r = get_q_from_file(arguments.unique_name + '.resume')
    if( q_r >= q0 + length ):
        logger.info('No more work to do, a previous run sieved to q='
                        + str(q_r))
        return
    elif( q_r != 0 ):
        logger.info('Resuming at q=' + str(q_r) + '.')
        q0 = q_r

    start_time = time.monotonic()
    overall_rel = 0
    s = arguments.saving_delta
    q_x = q0
    while(q_x < q_end):
        q_y = q_x + s
        if(q_y + s >= q_end):
            q_y = q_y + length % s
        overall_rel += sieve( q_x, q_y
                            , arguments.threads
                            , siever_exe
                            )
        logger.info( 'Overall relations found: ' + str(overall_rel) )
        elapsed_time = time.monotonic() - start_time
        logger.info( 'Elapsed time: ' + str(int(elapsed_time)) + 's ('
                    + str(round(elapsed_time / 86400, 3)) + ' day(s)).' )
        if( q_y < q_end ):
            eta = int(((q_end - q_y) / (q_y - q0)) * elapsed_time)
            logger.info( 'ETA: ' + seconds_to_dhms(eta) )
        q_x = q_y


# ****************************************************************************
# Returns the command line used for running this script
# ****************************************************************************
def get_command_line():
    command_line = ''
    i = 0
    for arg in sys.argv:
        if (i != 0):
            command_line += ' ' + arg
        i += 1
    return NAME + command_line


# ****************************************************************************
# Run
# ****************************************************************************
# Set up log handlers according to verbosity
log_level = logging.DEBUG if arguments.verbose else logging.INFO
console_handler = logging.StreamHandler()
console_handler.setLevel(log_level)
console_handler.setFormatter(logging.Formatter('|-> %(message)s'))
file_handler = logging.FileHandler(arguments.unique_name + '.log')
file_handler.setFormatter(logging.Formatter(
                            '|-> %(asctime)-15s | %(message)s'))
# Always use DEBUG level when logging to file
file_handler.setLevel(logging.DEBUG)
logger.addHandler(console_handler)
logger.addHandler(file_handler)


# Check lattice siever presence in PATH
latsieve = 'gnfs-' + arguments.lattice_siever
if not shutil.which(latsieve):
    die( 'Lattice siever ' + latsieve + ' could not be'
         + ' found, did you forget to update PATH?' )
# Some logging
logger.debug( '' )
logger.debug( '' )
logger.debug( NAME + ' version ' + VERSION )
logger.debug( '' )
logger.debug( 'command line:' )
logger.debug( '  ' + get_command_line() )
logger.debug( '' )
# Do run...
main_sieve(arguments.f, arguments.c, latsieve)


