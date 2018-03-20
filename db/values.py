"""
Value-Distance

Separate facet value types (numeric (>95%), alpha (>95%) or mixed)
Does analysis depending on the type. Either bag of words or chi2 etc.
This script should aim to produce as much data as nessesary. It is
not designed to be optimised to run on all samples (a licence for
it to explore and go slow).

Future Work
- add type f1 and type f2
- add the actual numbers showing how close they are.

"""


# Imports
import requests, json, csv, re, numpy, sys, ast, jellyfish, math
import pandas as pd
import scipy.stats as stats
from dateutil.parser import parse
from itertools import combinations, product
from matplotlib import pyplot as plt
import jellyfish._jellyfish as py_jellyfish
from tqdm import tqdm
import datetime
import argparse
from py2neo import Node, Relationship, Graph, Path, authenticate


# takes the values input file and convers it to dict of dict format
# also strips the _facet bit

def get_timestamp():
	""" 
	Get timestamp of current date and time. 
	"""
	timestamp = '{:%Y-%m-%d_%H-%M-%S}'.format(datetime.datetime.now())
	return timestamp

def type_hasher(values_list1, values_list2):

	"""
	Uses try to define a facets value type as a pair
	it calculates proportion of data types for each facet

	returns type buckets for humans to have a quick look.

	returns type_hash as:

	'numeric match' if 90% of both facet values are numbers (int, float or exponentials)
	'strings match' if 90% of both facet  values are strings (so excludes numbers)
	'date match' if 90% of both facet values are date type (I pull in a tool for this check and it checks many types)
	'mixed match string', 'mixed match numeric', 'mixed match date' and combinations
	thereof are returned if those relative ratios are within 10% and the ratio is greater than 0.25
	this prevents 0.00 and 0.00 matching etc

	"""
	if len(values_list1) > 0 and len(values_list2) > 0:

		# test facet 1

		type_int_f1 = 0
		type_str_f1 = 0
		type_date_f1 = 0
		values_list1_num = []
		for value in values_list1:
			try:	
				values_list1_num.append(float(value))
				type_int_f1 = type_int_f1 + 1
			except (ValueError, AttributeError):
				try:
					value = value.replace(',', '.')
					values_list1_num.append(float(value))
					type_int_f1 = type_int_f1 + 1
				except (ValueError, AttributeError):
				# attempts to create a date from value
					try:
						parse(value)
						type_date_f1 = type_date_f1 + 1
					except (ValueError, AttributeError, OverflowError):
						# add in regex for starts with no? to pick up measurements with units?
						type_str_f1 = type_str_f1 + 1
						pass

		int_ratio1 = type_int_f1/(type_int_f1 + type_str_f1 + type_date_f1)
		str_ratio1 = type_str_f1/(type_int_f1 + type_str_f1 + type_date_f1)
		date_ratio1 = type_date_f1/(type_int_f1 + type_str_f1 + type_date_f1)


		# print('int_ratio1: ',int_ratio1)
		# print('str_ratio1: ',str_ratio1)

		type_int1 = int_ratio1 > 0.9
		type_str1 = str_ratio1 > 0.9
		type_date1 = date_ratio1 > 0.9



		# test facet 2

		type_int_f2 = 0
		type_str_f2 = 0
		type_date_f2 = 0
		values_list2_num = []
		for value in values_list2:
			try:	
				values_list2_num.append(float(value))
				type_int_f2 = type_int_f2 + 1
			except (ValueError, AttributeError):
				try:
					value = value.replace(',', '.')
					values_list2_num.append(float(value))
					type_int_f2 = type_int_f2 + 1
				except:
					try:
						parse(value)
						type_date_f2 = type_date_f2 + 1
					except (ValueError, AttributeError, OverflowError):
						type_str_f2 = type_str_f2 + 1
						pass

		int_ratio2 = type_int_f2/(type_int_f2 + type_str_f2 + type_date_f2)
		str_ratio2 = type_str_f2/(type_int_f2 + type_str_f2 + type_date_f2)
		date_ratio2 = type_date_f2/(type_int_f2 + type_str_f2 + type_date_f2)

		no_unique_values1 = (type_int_f1 + type_str_f1 + type_date_f1)
		no_unique_values2 = (type_int_f2 + type_str_f2 + type_date_f2)



		# are they the same? arbitary limits:

		# both over 90% similar?
		type_int2 = int_ratio2 > 0.9
		type_str2 = str_ratio2 > 0.9
		type_date2 = date_ratio2 > 0.9

		# ratios same within 10% error?
		str_ratio1_lo = str_ratio1 * 0.95
		str_ratio1_hi = str_ratio1 * 1.05

		int_ratio1_lo = int_ratio1 * 0.95
		int_ratio1_hi = int_ratio1 * 1.05

		date_ratio1_lo = date_ratio1 * 0.95
		date_ratio1_hi = date_ratio1 * 1.05

		type_hash_mixed = []
		if str_ratio1 > 0.25 and str_ratio2 > 0.25 and str_ratio1_lo < str_ratio2 < str_ratio1_hi:
			type_hash_mixed.append('mixed match string')
		if int_ratio1 > 0.25 and int_ratio2 > 0.25 and int_ratio1_lo < int_ratio2 < int_ratio1_hi: 
			type_hash_mixed.append('mixed match numeric')
		if date_ratio1 > 0.25 and date_ratio2 > 0.25 and date_ratio1_lo < date_ratio2 < date_ratio1_hi: 
			type_hash_mixed.append('mixed match date')


		if type_int1 and type_int2:
			type_hash = 'numeric match'
		elif type_str1 and type_str2:
			# they are both str value types not many int
			type_hash = 'strings match'
		elif type_date1 and type_date2:
			type_hash = 'date match'
		elif type_hash_mixed:

			if 'mixed match string' and 'mixed match numeric' and 'mixed match date' in type_hash_mixed:
				type_hash = 'mixed string, numeric and date match'

			elif 'mixed match string' and 'mixed match numeric' in type_hash_mixed:
				type_hash = 'mixed string and numeric match'
			elif 'mixed match string' and 'mixed match date' in type_hash_mixed:
				type_hash = 'mixed string and date match'
			elif 'mixed match numeric' and 'mixed match date' in type_hash_mixed:
				type_hash = 'mixed numeric and date match'

			elif 'mixed match string' in type_hash_mixed:
				type_hash = 'mixed match string'
			elif 'mixed match numeric' in type_hash_mixed:
				type_hash = 'mixed match numeric'
			elif 'mixed match date' in type_hash_mixed:
				type_hash = 'mixed match date'

		else:
			type_hash = 'no match'

		return (type_hash, type_int_f1, type_str_f1, type_date_f1, type_int_f2, \
		type_str_f2, type_date_f2, int_ratio1, str_ratio1, date_ratio1, \
		int_ratio2, str_ratio2, date_ratio2, no_unique_values1, no_unique_values2,\
		values_list1_num, values_list2_num)

	else:
		type_hash = 'values missing from input file'

	

	


	# values_list1.isdigit()

def exact_value_scoring(values_list1, values_list2, values1, values2):

	"""
	pass this two lists of values from a pair of facets and it will
	give a score for exact value matches
	"""
	if len(values_list1) > 0 and len(values_list2) > 0:
		total_attributes = len(values_list1) + len(values_list2)
		matching_attributes = len(set(values_list1) & set(values_list2))

		match_freq = 0

		# print(values_list1)
		# print(values_list2)
		for k in values_list1:
			if k in values_list2:
				freq = values1.get(k) + values2.get(k)
				match_freq = match_freq + freq

		total_freq = sum(values1.values()) + sum(values2.values())

		score = ((matching_attributes * 2) / (total_attributes)) * (match_freq / total_freq)
		return score
	else:
		score = 0
		return score

def fuzzy_value_scoring(values_list1, values_list2):

	"""
	string pairwise matcher
	NB only best matches are taken this is not all by all
	gets fuzzy pair match based on jarowinkler
	returns dict with mean, stc and 0.9 qualtile
	for jarowinkler, damerau levenshtein and hamming distances

	If the number of values is too long (>1000) the most frequently
	used values are taken as best representatives. This is to make
	computation doable.


	"""
	if len(values_list1) > 0 and len(values_list2) > 0:

		if len(values_list1) > 1000 or len(values_list2) > 1000:
			if len(values_list1) > 1000:
				x = value_info.get(facet1)
				value_df = pd.DataFrame(columns=['frequency']).from_dict(x, orient = 'index').reset_index().rename(columns={"index": "value", 0: "frequency"}).sort_values(['frequency'], ascending=False).head(n=1000)
				values_list1 = value_df['value'].tolist()
			if len(values_list2) > 1000:
				x = value_info.get(facet2)
				value_df = pd.DataFrame(columns=['frequency']).from_dict(x, orient = 'index').reset_index().rename(columns={"index": "value", 0: "frequency"}).sort_values(['frequency'], ascending=False).head(n=1000)
				values_list2 = value_df['value'].tolist()


		if len(values_list1) > len(values_list2):
			short_list = values_list2
			long_list = values_list1
		else:
			short_list = values_list1
			long_list = values_list2
	

		# calculate the best fuzzy matches
		best_match_list = []
		for value1 in short_list:
			jaro_distance_list = []
			for value2 in long_list:

				try:
					damerau_levenshtein_distance = jellyfish.damerau_levenshtein_distance(value1, value2)
				except ValueError:
					damerau_levenshtein_distance = py_jellyfish.damerau_levenshtein_distance(value1, value2)

				jaro_winkler = jellyfish.jaro_winkler(value1, value2)
				hamming_distance = jellyfish.hamming_distance(value1, value2)

				jaro_tuple = (value1, value2, jaro_winkler, damerau_levenshtein_distance, hamming_distance)
				jaro_distance_list.append(jaro_tuple)		
			best_match = max(jaro_distance_list,key=lambda x:x[2])
			best_match_list.append(best_match)
		df = pd.DataFrame(best_match_list, columns = ['facet1', 'facet2', 'jaro_distance', 'damerau_levenshtein_distance', 'hamming_distance'])
		
		jaro_distance_quant = df['jaro_distance'].quantile(0.9)
		jaro_distance_mean = df['jaro_distance'].mean()
		jaro_distance_std = df['jaro_distance'].std()
		damerau_levenshtein_distance_quant = df['damerau_levenshtein_distance'].quantile(0.9)
		damerau_levenshtein_distance_mean = df['damerau_levenshtein_distance'].mean()
		damerau_levenshtein_distance_std = df['damerau_levenshtein_distance'].std()
		hamming_distance_quant = df['hamming_distance'].quantile(0.9)
		hamming_distance_mean = df['hamming_distance'].mean()
		hamming_distance_std = df['hamming_distance'].std()

		results = {'jaro_distance_quant':jaro_distance_quant,
		'jaro_distance_mean':jaro_distance_mean,
		'jaro_distance_std':jaro_distance_std,
		'damerau_levenshtein_distance_quant':damerau_levenshtein_distance_quant,
		'damerau_levenshtein_distance_mean':damerau_levenshtein_distance_mean,
		'damerau_levenshtein_distance_std':damerau_levenshtein_distance_std,
		'hamming_distance_quant':hamming_distance_quant,
		'hamming_distance_mean':hamming_distance_mean,
		'hamming_distance_std':hamming_distance_std}
		# so a good match will be a high mean, low std. The quantile is prob better than mean.
		
		return results
	else:

		# 'N.A.' returned if one or both of the facets dont have any values.


		results = {'jaro_distance_quant':'N.A.', \
		'jaro_distance_mean':'N.A.', \
		'jaro_distance_std':'N.A.', \
		'damerau_levenshtein_distance_quant':'N.A.', \
		'damerau_levenshtein_distance_mean':'N.A.', \
		'damerau_levenshtein_distance_std':'N.A.', \
		'hamming_distance_quant':'N.A.', \
		'hamming_distance_mean':'N.A.', \
		'hamming_distance_std':'N.A.'}

		return results

def magnitude_diff(type_hash, values_list1_num, values_list2_num):

	if type_hash == 'numeric match':

		temp_val1 = [ x for x in values_list1_num if not math.isnan(x)]
		temp_val2 = [x for x in values_list2_num if not math.isnan(x)]

		mean1 = sum(temp_val1)/len(temp_val1)+0.000000001 # the plus prevents zero log errors
		mean2 = sum(temp_val2)/len(temp_val2)+0.000000001 # the plus prevents zero log errors


		mag1 = int(math.floor(math.log10(abs(mean1))))
		mag2 = int(math.floor(math.log10(abs(mean2))))
	else:
		print('Magnitude Error: something went wrong')
		sys.exit()

	if mag1 == mag2:
		magnitude_difference = 'Roughly Equivalent'
	else:
		if (mean1 == abs(mean1)) and (mean2 == abs(mean2)): # they are both positive
			magnitude_difference = abs(mag1 - mag2)
		elif (mean1 < abs(mean1)) and (mean2 == abs(mean2)): # aka mean1 is negative
			magnitude_difference = abs(mag1 + mag2)
		elif mean2 < abs(mean2) and (mean1 == abs(mean1)):  # aka mean2 is negative
			magnitude_difference = abs(mag1 + mag2)
		elif (mean1 < abs(mean1)) and mean2 < abs(mean2): # they are both negative
			magnitude_difference = abs(mag1 - mag2)



	return magnitude_difference

def do_calcs(facet1, facet2, missing_count, already_computed_count, newly_computed_count):

	# get value info out of the dict (held in mem)
	try:

		values1 = value_info.get(facet1)
		values2 = value_info.get(facet2)

		pair_name = n["p"].properties['name']
		
		values_list1 = values1.keys()
		values_list2 = values2.keys()

	except AttributeError:
		values_list1 = []
		values_list2 = []


	if len(values_list1) > 0 and len(values_list2) > 0: # check if the attributes have value information in input
		skip = False
	else:
		skip = True
		if len(values_list1) and len(values_list1) == 0:
			print('MISSING INFORMATION IN INPUT')
			print('------------------------------')
			print(pair_name, 'skipped')
			print(str(facet1), 'and', str(facet2), 'has no value information in values.csv')
			outF.write('MISSING INFORMATION IN INPUT\n------------------------------\n')
			outF.write(pair_name+'skipped\n')
			outF.write(str(facet1)+' and '+str(facet2)+' have no value information in values.csv\n\n')
		elif len(values_list1) == 0:
			print('MISSING INFORMATION IN INPUT')
			print('------------------------------')
			print(pair_name, 'skipped')
			print(str(facet1), 'has no value information in values.csv')
			outF.write('MISSING INFORMATION IN INPUT\n------------------------------\n')
			outF.write(pair_name+'skipped\n')
			outF.write(str(facet1)+' has no value information in values.csv\n\n')
		elif len(values_list2) == 0:
			print('MISSING INFORMATION IN INPUT')
			print('------------------------------')
			print(pair_name, 'skipped')
			print(str(facet2), 'has no value information in values.csv')
			outF.write('MISSING INFORMATION IN INPUT\n------------------------------\n')
			outF.write(pair_name+'skipped\n')
			outF.write(str(facet2)+' has no value information in values.csv\n\n')
		else:
			print('something went wrong..')
			sys.exit()

	
	if not skip: # do the calculations


		exact_score = exact_value_scoring(values_list1, values_list2, values1, values2)
		type_hash_results = type_hasher(values_list1, values_list2)


		type_hash = type_hash_results[0] 			# the pair's type match (numeric, string or date)
		type_int_f1 = type_hash_results[1]			# no. of numeric matches in attribute 1
		type_str_f1 = type_hash_results[2]			# no. of string matches in attribute 1
		type_date_f1 = type_hash_results[3]			# no. of date matches in attribute 1
		type_int_f2 = type_hash_results[4]			# no. of numeric matches in attribute 2
		type_str_f2 = type_hash_results[5]			# no. of string matches in attribute 2
		type_date_f2 = type_hash_results[6]			# no. of date matches in attribute 2
		int_ratio1 = type_hash_results[7]			# ratio of numeric matches in attribute 1
		str_ratio1 = type_hash_results[8]			# ratio of string matches in attribute 1
		date_ratio1 = type_hash_results[9]			# ratio of date matches in attribute 1
		int_ratio2 = type_hash_results[10]			# ratio of numeric matches in attribute 2
		str_ratio2 = type_hash_results[11]			# ratio of string matches in attribute 2
		date_ratio2 = type_hash_results[12]			# ratio of date matches in attribute 2
		no_unique_values1 = type_hash_results[13]	# number of unique values in attribute 1
		no_unique_values2 = type_hash_results[14]	# number of unique values in attribute 2
		top_value1 = max(values1, key=lambda key: values1[key])
		top_value2 = max(values2, key=lambda key: values2[key])


		if type(type_hash) is str:
			type_match = type_hash
		else:
			print('something going wrong with type_hash')
			print(type(type_hash))
			sys.exit()

		print(type_match)
		print(type_hash)

		if type_match == 'numeric match':
			values_list1_num = type_hash_results[15]
			values_list2_num = type_hash_results[16]
			magnitude_difference = magnitude_diff(type_hash, values_list1_num, values_list2_num)
			fuzzy_scores = 'N.A.'
			jaro_score = 'N.A.'
			
		elif type_match == 'date match':
			magnitude_difference = 'N.A.'
			fuzzy_scores = 'N.A.'
			jaro_score = 'N.A.'
			
		else:
			print(len(values_list1))
			print(len(values_list2))
			magnitude_difference = 'N.A.'
			fuzzy_scores = fuzzy_value_scoring(values_list1, values_list2)
			jaro_score = fuzzy_scores.get('jaro_distance_quant')
			
					

		# put the calculations back into graph db

		n['p']['exact_score'] = exact_score
		n['p']['type_match'] = type_match
		n['p']['magnitude_difference'] = magnitude_difference
		n['p']['jaro_score'] = jaro_score
		n['p']['type_int_f1'] = type_int_f1 			# no. of numeric matches in attribute 1
		n['p']['type_str_f1'] = type_str_f1 			# no. of string matches in attribute 1
		n['p']['type_date_f1'] = type_date_f1 			# no. of date matches in attribute 1
		n['p']['type_int_f2'] = type_int_f2				# no. of numeric matches in attribute 2
		n['p']['type_str_f2'] = type_str_f2				# no. of string matches in attribute 2
		n['p']['type_date_f2'] = type_date_f2			# no. of date matches in attribute 2
		n['p']['int_ratio1'] = int_ratio1				# ratio of numeric matches in attribute 1
		n['p']['str_ratio1'] = str_ratio1				# ratio of string matches in attribute 1
		n['p']['date_ratio1'] = date_ratio1				# ratio of date matches in attribute 1
		n['p']['int_ratio2'] = int_ratio2				# ratio of numeric matches in attribute 2
		n['p']['str_ratio2'] = str_ratio2				# ratio of string matches in attribute 2
		n['p']['date_ratio2'] = date_ratio2				# ratio of date matches in attribute 2
		n['p']['no_unique_values1'] = no_unique_values1	# number of unique values in attribute 1
		n['p']['no_unique_values2'] = no_unique_values2	# number of unique values in attribute 2
		n['p']['top_value1'] = top_value1				# most frequently occuring value in attribute 1
		n['p']['top_value2'] = top_value2				# most frequently occuring value in attribute 2
		n['p']['values_update_timestamp'] = get_timestamp()
		graph.push(n['p'])
		newly_computed_count += 1


		print()
		print()
		print('NEWLY CALCULATED')
		print('--------------------------------------------')
		print('Attribute 1: '+ facet1)
		print('Attribute 2: '+ facet2)
		print('--------------------------------------------')	
		print('Exact Score:', exact_score)
		print('Type Match:', type_match)
		print('Magnitude Difference:', magnitude_difference)
		print('Jaro Score:', jaro_score)
		print()
		print('No. of missing pairs so far: ', missing_count)
		print('Pairs previously computed so far: ', already_computed_count)
		print('Pairs newly computed so far: ', newly_computed_count)

	else: # if skip is True
		missing_count += 1

	return(missing_count, already_computed_count, newly_computed_count)

def have_calcs_been_done_already(missing_count, already_computed_count, newly_computed_count):

	exact_score = n["p"].properties['exact_score']
	type_match = n["p"].properties['type_match']
	magnitude_difference = n["p"].properties['magnitude_difference']
	jaro_score = n["p"].properties['jaro_score']
	type_int_f1 = n["p"].properties['type_int_f1']
	type_str_f1 = n["p"].properties['type_str_f1']
	type_date_f1 = n["p"].properties['type_date_f1']
	type_int_f2 = n["p"].properties['type_int_f2']
	type_str_f2 = n["p"].properties['type_str_f2']
	type_date_f2 = n["p"].properties['type_date_f2']
	int_ratio1 = n["p"].properties['int_ratio1']
	str_ratio1 = n["p"].properties['str_ratio1']
	date_ratio1 = n["p"].properties['date_ratio1']
	int_ratio2 = n["p"].properties['int_ratio2']
	str_ratio2 = n["p"].properties['str_ratio2']
	date_ratio2 = n["p"].properties['date_ratio2']
	no_unique_values1 = n["p"].properties['no_unique_values1']
	no_unique_values2 = n["p"].properties['no_unique_values2']
	top_value1 = n["p"].properties['top_value1']
	top_value2 = n["p"].properties['top_value2']
	values_update_timestamp = n["p"].properties['values_update_timestamp']

	already_computed_count += 1


	print()
	print()
	print('PREVIOUSLY CALCULATED')
	print('--------------------------------------------')
	print('Attribute 1: '+ facet1)
	print('Attribute 2: '+ facet2)
	print('--------------------------------------------')	
	print('Exact Score:', exact_score)
	print('Type Match:', type_match)
	print('Magnitude Difference:', magnitude_difference)
	print('Jaro Score:', jaro_score)
	print()
	print('No. of missing pairs so far: ', missing_count)
	print('Pairs previously computed so far: ', already_computed_count)
	print('Pairs newly computed so far: ', newly_computed_count)

	return already_computed_count


if __name__ == "__main__":
# def run():

	# args
	parser = argparse.ArgumentParser(description='Calculates various distances between two attributes based on value information.')
	parser.add_argument('--recalculate', '-r', action='store_true', help='recalculates and rewrites all stats for all pairs')
	run_mode = parser.parse_args()
	recalculate_arg = (run_mode.recalculate)

	# initialise database graph
	graph = Graph('http://localhost:7474/db/data', user='neo4j', password='neo5j')

	# get value data globally

	input_file = 'data/values.json'
	with open(input_file) as f:
		value_info = json.load(f)

	# open log file
	start_timestamp = get_timestamp()
	logname = str('log/' + start_timestamp + '_values.log')
	with open(logname, 'w') as outF:
		outF.write('LOG FILE for values.py\n\n' + 'Start time: ' + start_timestamp + '\n')

		missing_count = 0
		already_computed_count = 0
		newly_computed_count = 0


		pairs_total = graph.data("MATCH (p:Pair) RETURN count(*) AS total") # just for tqdm
		pairs_total_asNum = pairs_total[0]['total']

		if not recalculate_arg: # argument passed at command line to recalculate all nodes

			for n in tqdm(graph.run("MATCH (p:Pair) RETURN p ORDER BY p.pseudo_confidence DESC"),total = pairs_total_asNum, unit = 'pairs'):
			# for n in tqdm(graph.run("MATCH (p:Pair) RETURN p ORDER BY p.pseudo_confidence"),total = pairs_total_asNum, unit = 'pairs'): # del and switch back after test

				facet1 = n["p"]["good_attribute"]
				facet2 = n["p"]["bad_attribute"]				

				# check if calculations have already been done
				try:
					already_computed_count = have_calcs_been_done_already(missing_count, already_computed_count, newly_computed_count)

				except (AttributeError, KeyError): # aka if the scores haven't been calculated

					counters = do_calcs(facet1, facet2, missing_count, already_computed_count, newly_computed_count)

					missing_count = counters[0]
					already_computed_count = counters[1]
					newly_computed_count = counters[2]



		else: # recalculate all nodes

			for n in tqdm(graph.run("MATCH (p:Pair) RETURN p ORDER BY p.pseudo_confidence DESC"),total = pairs_total_asNum, unit = 'pairs'):
				
				facet1 = n["p"]["bad_attribute"]
				facet2 = n["p"]["good_attribute"]

				counters = do_calcs(facet1, facet2, missing_count, already_computed_count, newly_computed_count)

				missing_count = counters[0]
				already_computed_count = counters[1]
				newly_computed_count = counters[2]

















