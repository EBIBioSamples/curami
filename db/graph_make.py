'''
Builds a networkx graph from the coexistance data and attributes calculated by input.py
'''
import sys
import math
import json
import re
import pandas as pd
import networkx as nx
from tqdm import tqdm


def prob_calc():

	print('Calculating probability normalised weights...')

	# calculate expected probability and weights

	def file_len(fname):
		with open(fname) as f:
			for i, l in enumerate(f):
				pass
		return i + 1

	# read in data
	coexist_df = pd.read_csv('data/coexistences.csv', index_col = 0, dtype={'attribute1': str, 'attribute2': str, 'totals': int})
	attributes_df = pd.read_csv('data/attributes.csv', index_col = 0, dtype={'attribute': str, 'frequency': int})
	sample_no = file_len('data/samples.csv')

	#NB totals is the observed frequency

	# probability calculations and mapping
	attributes_df['prob'] = attributes_df['frequency'] / sample_no
	merge1_df = pd.merge(left = coexist_df, right = attributes_df, left_on = 'attribute1', right_on = 'attribute')
	merge1_df.rename(columns={'prob':'Attribute1_prob'}, inplace=True)
	merge2_df = merge1_df[['attribute1', 'attribute2', 'totals', 'Attribute1_prob']]
	merge3_df = pd.merge(left = merge2_df, right = attributes_df, left_on = 'attribute2', right_on = 'attribute')
	merge3_df.rename(columns={'prob':'Attribute2_prob'}, inplace=True)
	merge4_df = merge3_df[['attribute1', 'attribute2', 'totals', 'Attribute1_prob', 'Attribute2_prob']]

	merge4_df['exp'] = ((merge4_df['Attribute1_prob'] * merge4_df['Attribute2_prob']) * sample_no) # looked into warning it throws can't see an issue

	merge4_df['diff'] = merge4_df['totals'] - merge4_df['exp']
	merge4_df['weight'] = merge4_df['diff']/merge4_df['diff'].sum() # as per stats deffinition 'weights' must add up to 1

	# output
	merge5_df = merge4_df.sort_values(['diff'])
	coexistProb_df = merge5_df[['attribute1', 'attribute2', 'totals', 'exp', 'diff', 'weight']]

	# during merge only rows with the corresponding columns are merged!
	no_missing = coexist_df.shape[0] - coexistProb_df.shape[0]
	if no_missing > 0:
		print('WARNING: '+str(no_missing)+' pairs missing due to input file discrepancy.')
	else:
		print('Full house. No pairs were thrown out.')


	return coexistProb_df

if __name__ == "__main__":
# def run():

	df = prob_calc() # calculates the probability weighted coexistance weights
	df.to_csv('data/coexistencesProb.csv', header = True, mode = 'w')


	print('Building NetworkX...')
	G=nx.Graph()
	G = nx.from_pandas_dataframe(df,source='attribute1', target='attribute2', edge_attr='weight')

	# # for cytoscape save
	# nx.write_gml(G,'coexistences.gml')

	# for gephi save
	nx.write_gexf(G,'data/coexistences.gexf') # this file is used by coexistence.py







