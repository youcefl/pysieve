pysieve.py
==========
A Python wrapper over GGNFS sievers

pysieve.py is an easily deployed, self sufficient Python script used
for running multiple instances of a GGNFS siever in parallel producing
a gzipped set of relations.

Getting started
---------------

We start by getting Python installed (we will need Python version >= 3.3),
once our Python environment is OK, we open a terminal in which our
PATH environment variable is set to contain the folder where the GGNFS
siever we want to run resides e.g. 

        > EXPORT PATH=$PATH:/path/to/ggnfs_binaries  // Unix/Linux
        > set PATH=%PATH%;E:\maths\ggnfs             // Windows

Now, suppose we have a polynomial file N.poly we want to sieve on the algebraic
side from 20E6 to 50E6, running 16 instances of gnfs-lasieve4I14e, we just type

        > pysieve.py -v -t 16 -f 20000000 -c 30000000 -d 160000 -s N_020-040M -l lasieve4I14e -a N.poly

and voila, after a few days we get the relations gzipped in file N_020-040M.dat.gz

If we wanted to sieve on the rational side we would use

        > pysieve.py -v -t 16 -f 20000000 -c 30000000 -d 160000 -s N_020-040M -l lasieve4I14e -r N.poly

and if we wanted each subprocess to process ranges of length 20000 instead of 10000 we would use

        > pysieve.py -v -t 16 -f 20000000 -c 30000000 -d 320000 -s N_020-040M -l lasieve4I14e -r N.poly

To get some help use

        > pysieve.py --help

Notice that pysieve.py supports resuming i.e. in case of power failure, you restart
the sieving by typing the same command line (it can be found in the log file), the sieving
will resume where it halted.

