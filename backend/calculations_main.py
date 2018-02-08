'''
Master file to control the initial building of the DB and running calculation modules on attributes.

run() takes several arguments that trigger various processes as visible in the code below. These will be documented outside of the web app.
Users (certain users only, jsut me for now) will be able to execute these scripts from within the app.
I should also have a version of this file that can be ran manually if anyone needs to do that.


'''

import make_input, graph_make, lexical_filter, coexistence, values, autocluster, mancluster
import argparse, sys


def run_options():
	print('You need to provide a run mode for this script')
	print('-a --all this will use the pointer to get information from the BioSamples DB, run the lexical filter to generate attribute pairs then perform all calculations on these pairs')
	print('-i --inputOnly this will use the pointer to get information from the BioSamples DB and build all input data and graphs prior to calculation')
	print('-c --coexistence calculate coexistance )')
	print('-v --values calculate values )')
	print('-t --autocluster calculate autocluster )')
	sys.exit()

def input_build(pointer):

	make_input.run(pointer)
	graph_make.run()
	lexical_filter.run()

def calculations(recalc=None):

	if recalc is 'r':
		coexistence.run('r')
		values.run('r')
		autocluster.run('r')
	elif recalc is None:
		coexistence.run('n')
		values.run('n')
		autocluster.run('n')
	else:
		print('InternalError: recalc should either be r or None')
		sys.exit()




# remove the main start in favor of def run() for tests.

# if __name__ == '__main__':

# 	# args for testing
# 	pointer = 'http://scooby.ebi.ac.uk:8081/biosamples/beta/samples'
# 	run_mode = None
# 	recalc = None




def run(pointer='http://scooby.ebi.ac.uk:8081/biosamples/beta/samples', run_mode=None, recalc=None):

	# NB -r -- recalculate add this if you want to recalculate the info. Otherwise the scripts will skip previously calculated nodes.

	if run_mode is None:
		run_info()

	elif run_mode not in ['a', 'i', 'c', 'v', 't']:
		print('Run mode must be a, i, c, v or t')
		print('Also pass recalc = "r" if ')
		run_info()

	elif run_mode == 'a':
		input_build(pointer)
		calculations(recalc)

	elif run_mode == 'i':
		input_build(pointer)

	elif run_mode == 'c':
		if recalc is 'r':
			coexistence.run('r')
		elif recalc is None:
			coexistence.run('n')
		else:
			print('InternalError: recalc should either be r or None')
			sys.exit()

	elif run_mode == 'v':
		if recalc is 'r':
			values.run('r')
		elif recalc is None:
			values.run('n')
		else:
			print('InternalError: recalc should either be r or None')
			sys.exit()

	elif run_mode == 't':
		if recalc is 'r':
			autocluster.run('r')
		elif recalc is None:
			autocluster.run('n')
		else:
			print('InternalError: recalc should either be r or None')
			sys.exit()
		



	
