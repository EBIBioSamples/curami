'''
generates input data for pipeline
producing four files attributes, samples, values and coexistences
see ./docs/documentation.md for details

This version:

Creates coexistances.csv directly avoiding doing this via a json file.
This is better because the converter was build with regex and was less robust.

Does not use Solr at any point.



'''
import os
import re
import csv
import sys
import math
import json
import time
import glob
import timeit
import string
import requests
import itertools
import pandas as pd
from tqdm import tqdm
from operator import add
from functools import wraps
from collections import Counter
from collections import Mapping
from pprint import pprint as pp
from multiprocessing import Process
import test


def fn_timer(function):
	@wraps(function)
	def function_timer(*args, **kwargs):
		# dir(function)
		t0 = time.time()
		result_ = function(*args, **kwargs)
		t1 = time.time()
		print ("Total time running %s: %s seconds" %
				(function.__name__, str(t1-t0))
				)
		# outF.write('Total time running: ' + function.__name__ + ' ' + str(t1-t0) + '\n' + '\n')
		return result_
	return function_timer

# @fn_timer
def api_samples(parms):
	# BioSample API request module

	startpage = parms["start"]
	endpage = parms["end"]
	name = parms["name"]
	page_size = parms["size"]
	valname = str('values_' + name + '.json')

	# print(name, " : ", startpage, endpage)
	# return # remove after testing

	counter_page = startpage # not sure if this is needed

	all_attributes = {}

	with open(valname, 'w', encoding="utf-8") as fp, open(name + '.csv', 'w') as f:


		for counter_page in tqdm(range(startpage, endpage), desc=str("Process " + name), unit='page'):
			# if counter_page % 100 == 0:
			# 	print("Process " + name + " reached " + str(counter_page))


			# Initialize keys_list variable
			keys_list = []
			query_params = {
				"page": counter_page,
				"size": page_size,
			}

			# Request the API for the samples
			response = requests.get(pointer, params=query_params)
			if response.status_code is not 200:
				# If the status code of the response is not 200 (OK), something is wrong with the API
				# Return the process
				print('Something wrong happening. Error code '
					+ str(response.status_code)
					+ ' At '
					+ str(time.asctime(time.gmtime(time.time())))
					)
				return

			# scraping json on the page

			samples_in_page = response.json()['_embedded']['samples']
		

			# For each sample, get characteristics types and save them in the key_list variable
			for sample in samples_in_page:
				accession_no = sample['accession'] # added by MG to grab sampleIDs
				sample_characteristics = sample['characteristics']
				sample_keys = list(sample_characteristics.keys())
				sample_keys = [accession_no] + sample_keys
				keys_list.append(sample_keys)

				# also extract the value information

				for attribute in sample_characteristics:
					val = sample_characteristics[attribute][0]['text']
					if attribute not in all_attributes.keys():
						all_attributes[attribute] = {val:1}
						# print(all_attributes)

					elif attribute in all_attributes.keys():
						val_dict = all_attributes.get(attribute)
						if val not in val_dict.keys():
							val_dict[val] = 1
							all_attributes[attribute] = val_dict
						elif val in val_dict.keys():
							val_dict[val] += 1
							all_attributes[attribute] = val_dict


			# Write the characteristics list into the file
			writer = csv.writer(f)
			writer.writerows(keys_list)


		json.dump(all_attributes, fp)

# @fn_timer
def multithread_crawler(pointer):
	# Crawler script- get me a list of keys for every sample.

	# Splitting up the BioSamples Pages into equal chunks for multithreading
	numberOfParalelJobs = 8
	pageSize = 500
	query_params = {
		"size": pageSize,
	}
	rel = requests.get(pointer, params=query_params)
	if rel.status_code is not 200:
		print('Something wrong happening in Multithread Crawler. Error code '
					+ str(rel.status_code)
					+ ' At '
					+ str(time.asctime(time.gmtime(time.time())))
					)
		sys.exit()
		
	reply = rel.json()
	totalPageNumer = reply['page']['totalPages']

	startpoint = 0
	init = []
	for i in range(1, numberOfParalelJobs + 1):
		params = dict()
		params['run'] = i
		params['size'] = pageSize
		params['name'] = "Thread{}_results".format(str(i))
		params['start'] = startpoint

		endpoint = math.ceil(totalPageNumer / float(numberOfParalelJobs)) * i
		if endpoint < int(totalPageNumer):
			params['end'] = int(endpoint)
		else:
			params['end'] = totalPageNumer

		init.append(params)
		startpoint = int(endpoint) + 1

	print(init)
	processlist = []
	for entry in init:
		p = Process(target=api_samples, args=[entry])
		p.start()
		processlist.append(p)

	# print("All process started")

	# Going through the process list, waiting for everything to finish
	for procs in processlist:
		procs.join()

	print("All finished")

	# combine results into samples file.
	
	filenames = []
	for f in glob.glob('Thread*_results.csv'):
		filenames.append(f)

	with open('./data/samples.csv', 'w') as outfile:
		for fname in filenames:
			with open(fname) as infile:
				for line in infile:
					outfile.write(line)

	# sys.exit()

def stripID():
	# makes .temp files that strips the first column. This will remove sample id before passing to concurrence counter.

	filenames = []
	for f in glob.glob('Thread*_results.csv'):
		filenames.append(f)
	

	for fname in filenames:
		tempname = str(fname + '.temp')
		with open(fname, 'r') as infile:
			reader = csv.reader(infile)
			reader_list = list(reader)
			writer = csv.writer(open(tempname,'w'))
			for sample in reader_list:
				sample_ = sample[1:]
				writer.writerow(sample_)

	# removes 'Thread*_results.csv' files
	for f in glob.glob('Thread*_results.csv'):
		os.remove(f)

	for f in glob.glob('Thread*_results.csv.temp'):
		z = f[:-5]
		os.rename(f, z)

@fn_timer
def create_cooccurrence_matrix(params):

	in_filename = params['filename_in']
	out_filename = params['filename_out']

	types_letter = list(string.ascii_lowercase) # was initially outside of function?
	types_letter.insert(0, "#") # was initially outside of function?
	# tcd = {letter: {} for letter in types_letter} # probably not necessary
	
	tcd = {}

	with open(in_filename, 'r') as f:
		samples_type_list = f.readlines()

	line_counter = 0
	total_lines = len(samples_type_list)
	for type_list in tqdm(samples_type_list, unit='line', desc=str('Counting coexistences for' + in_filename), total=total_lines):
		# if line_counter % 50000 == 0:
		# 	print('Line {} of {}'.format(line_counter, total_lines))
		types = [type_name.strip() for type_name in type_list.split(',') if type_name]
		types.sort()
		types_permutations = itertools.combinations(types, 2)
		for perm in types_permutations:
			(A, B) = perm
			# first_letter = str(A[0]).lower()
			# if first_letter not in string.ascii_lowercase:
			#     first_letter = "#"
			if A not in tcd:
				tcd[A] = {}

			if B not in tcd[A]:
				tcd[A][B] = 0

			tcd[A][B] += 1
		line_counter += 1

	with open(out_filename, 'w') as fout:
		json.dump(tcd, fout)

@fn_timer
def trigger_matrix():
	'''
	takes inputs from threads (after ID stripping) and does line by line counting.
	Makes a dictionary for each thread. This is passed to combine_threads.
	'''
	params = dict()

	base_filename_in = 'Thread\d_results.csv'
	base_filename_out = 'cooccurrence_matrix{}.json'

	input_files = [f for f in os.listdir('./') if re.match(base_filename_in, f)]
	for i in range(len(input_files)):
		input_file = input_files[i]
		print('Working on {}'.format(input_file))
		params['filename_in'] = input_file
		params['filename_out'] = base_filename_out.format(i+1)

		start_time = timeit.default_timer()
		create_cooccurrence_matrix(params)
		print(timeit.default_timer() - start_time)

	# removes 'Thread*_results.csv.temp' files
	# for f in glob.glob('Thread*_results.csv'):
	# 	os.remove(f)

def combine_threads():

	# takes multiple json files and combines the counts into a csv (alphabetically sorted, summed totals and duplicates dropped)

	basename = 'cooccurrence_matrix\d+\.json'
	output_name = './data/coexistences.csv'


	files_folder = './'
	files = [f for f in os.listdir(files_folder) if re.match(basename, f)]
	
	d = []
	for f in files:

		with open(f, 'r') as fin:
			partial_matrix = json.load(fin)

			for attribute1 in partial_matrix.keys():
				inner_dict = partial_matrix.get(attribute1)
				for attribute2 in inner_dict:
					count = inner_dict.get(attribute2)

					sort_list = [attribute1, attribute2]
					attribute1_ = sorted(sort_list)[0]
					attribute2_ = sorted(sort_list)[1]



					d.append({'attribute1':attribute1_, 'attribute2':attribute2_, 'count':count})
					# o.writerow(attribute1 + attribute2 + str(count))


	df = pd.DataFrame(d)
	df['totals'] = df.groupby(['attribute1', 'attribute2'])['count'].transform('sum')

	df[['attribute1', 'attribute2', 'totals']].sort_values(['attribute1', 'attribute2']).drop_duplicates(['attribute1', 'attribute2']).reset_index(drop=True).to_csv(output_name)

	for f in glob.glob('cooccurrence_matrix*.json'):
		os.remove(f)

def get_attributes():

	'''
	Counts the attribute frequency based on the sample scrape and makes attributes.csv
	'''

	attribute_counts = {}

	with open('data/samples.csv', 'r') as infile:
			reader = csv.reader(infile)
			reader_list = list(reader)
			for sample_ in tqdm(reader_list, desc='Extracting attribute counts from samples.', unit='samples'):
				sample = sample_[1:]
				for attribute in sample:
					if attribute in attribute_counts:
						attribute_counts[attribute] += 1
					elif attribute not in attribute_counts:
						attribute_counts[attribute] = 1

	df_ = pd.DataFrame().from_dict(attribute_counts, orient='index').reset_index()
	df_.columns = ['attribute', 'frequency']
	df = df_.sort_values(['frequency', 'attribute'], ascending=False).reset_index(drop=True)
	df.to_csv('data/attributes.csv')

def combine_json():


	dictionaries = []
	for f in glob.glob('values_Thread*_results.json'):
		print(f)
		with open(f) as j:
			json_str = j.read()
			json_data = json.loads(json_str)
			dictionaries.append(json_data)


	all_attributes = set()
	master_dict = {}

	for thread_dict in dictionaries:
		for key, value in thread_dict.items():
			all_attributes.add(key)
	print('No of attributes in json value info: ' + str(len(all_attributes)))


	for attribute in all_attributes:
		attribute_full_dict = {}

		for thread_dict in dictionaries:
			attribute_part_dict = thread_dict.get(attribute)
			if attribute_part_dict:
				attribute_full_dict = {k: attribute_part_dict.get(k, 0) + attribute_full_dict.get(k, 0) for k in set(attribute_part_dict) | set(attribute_full_dict)}

		master_dict[attribute] = attribute_full_dict


	with open('data/values.json', 'w') as fp:
		json.dump(master_dict, fp, sort_keys=True, indent=4)

	# for f in glob.glob('values_Thread*_results.json'):
	# 	os.remove(f)


if __name__ == "__main__":

	pointer = 'http://wwwdev.ebi.ac.uk/biosamples/samples'
	# pointer = 'http://scooby.ebi.ac.uk:8081/biosamples/beta/samples'
	# pointer = 'https://www.ebi.ac.uk/biosamples/samples'

	# data data sub dir if it doesn't exist
	try:
		os.mkdir('./data')
	except FileExistsError:
		pass


	# generates 'samples.csv', 'coexistences.csv' and 'values.csv'

	multithread_crawler(pointer)
	stripID()
	trigger_matrix()
	combine_threads()

	# generate attributes file

	get_attributes()


	# # add in earlier maybe launched by the crawler when this is known to work
	combine_json()

	test.count_combined()
	test.count_each()
	test.check_random()















