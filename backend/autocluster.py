#!/usr/bin/env python

'''
Automated attempts of clustering. While these are generally poor this
scripts's main aim is to provide the human user with the neccesary info
to make a judgement of k (no. of clusters).

The script currently just produces 2D reduction and hierachical clustering.
It does not guess k! This is very poor due to the erratic data in BioSamples,
no single method can automatically determine k robustly. In the future, I intend
to implement all the automated methods currently available and track their output.
I will use this for later machine learning to find patterns which may lead to an
automated method for k determination.

Key Features
- linked with existing Neo4J DB, checks pair info and adds accordingly
- Checks which samples have query attributes and retreves unique IDs
- Builds a binary matrix (x = no. of samples, y = attributes)
- Uses MCA to reduce to 2 dimensions and produces 2D scatter plots
- Uses MCA to reduce to 3D (passed to file for later use by mancluster.py)
- From 2 dimensions hiarachical clustering produces dendrograms
- Passes information to Neo4J (links to graph images)
- Creates Pair to Sample relationships

Note about next step
autocluster can be run on every pair. Before this is passed onto mancluster a human needs
to assign k. Once this is done man cluster then kicks in (on demand via app and with a combing
operating mode to sweep up and perform any missing calculations). This removes the previous direct
links from Pairs to Samples and adds intermediate Cluster nodes.

If this program is run in recalculate mode it will strip Sample-Cluster relationships.

Furture Work
- add more automated k methods aiming to identify a fully automated method.
- review dendrogram plot asthetics


'''

import time
from functools import wraps
import seaborn as sns
import plotly.plotly as py
import plotly.figure_factory as ff
import plotly 
# plotly.tools.set_credentials_file(username='hewgreen', api_key='5kadWSTCyFCa0IRt3SWi')


import prince
import numpy as np
import pandas as pd
import sys, csv, sklearn
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from scipy.spatial.distance import pdist
from sklearn.cluster import AffinityPropagation
from scipy.cluster.hierarchy import dendrogram, linkage, cophenet, fcluster
from py2neo import Node, Relationship, Graph, Path, authenticate
from tqdm import tqdm
import datetime
import argparse
from collections import Counter
import re

def get_timestamp():
	""" 
	Get timestamp of current date and time. 
	"""
	timestamp = '{:%Y-%m-%d_%H-%M-%S}'.format(datetime.datetime.now())
	return timestamp

def build_matrix(facet1, facet2):

	outF.write('Started build_matrix module...' + '\n')

	samples_dict = {}
	unique_facets = []
	unique_samples = []

	facet1_sample_ids = [] # list of IDs
	facet2_sample_ids = [] # list of IDs
	facet1n2_sample_ids = [] # list of IDs

	print('Parsing samples with facet', facet1, 'and', facet2)


	outF.write('Facet 1: ' + facet1 + '\n' + 'Facet 2: ' + facet2 + '\n' + '\n')


	with open('data/samples.csv','r') as f_in:

		for line in f_in:
			data_list = line.rstrip().split(',')
			if (facet1 in data_list) or (facet2 in data_list):
				sample_id = data_list[0] # e.g. SAMN03104714

				# if sample_id not in unique_samples:
				# 	unique_samples.append(sample_id)
				# 	if (len(unique_samples) % 10000 == 0):
				# 		print(len(unique_samples))
				
				if (facet1 in data_list) and (facet2 in data_list):					
					facet1n2_sample_ids.append(sample_id)
				elif facet1 in data_list:
					facet1_sample_ids.append(sample_id)
				elif facet2 in data_list:
					facet2_sample_ids.append(sample_id)

				data_list.remove(sample_id)
				samples_dict[sample_id] = data_list # 'SAMN03105019': ['biomaterialProvider', 'synonym', 'package', 'cultivar', 'organism', 'model', 'organismPart', 'genotype'] for every match!


				for attribute in data_list:
					if attribute not in unique_facets:
						unique_facets.append(attribute)


		unique_samples = facet1n2_sample_ids + facet1_sample_ids + facet2_sample_ids

		
		

		outF.write('Samples with' + ' ' + facet1 + ' ' + ':' + ' ' + str(len(facet1_sample_ids)) + '\n')
		outF.write('Samples with' + ' ' + facet2 + ' ' + ':' + ' ' + str(len(facet2_sample_ids)) + '\n')
		outF.write('Samples with both' + ' ' + str(len(facet1n2_sample_ids)) + '\n')
		outF.write('In total' + ' ' + str(len(unique_samples)) + ' ' + 'unique samples are being analysed with' + ' ' + str(len(unique_facets)) + ' ' + 'attributes.' + '\n')


	print('Generating', len(unique_samples), 'x', len(unique_facets), 'DataFrame...')
	outF.write('Dataframe is' + ' ' +  str(len(unique_samples)) + ' ' +  'x' + ' ' +  str(len(unique_facets)) + '\n' + '\n')

	# unique_facets = [x for x in unique_facets if x is not facet1 and x is not facet2]
	# unique_facets_ = [x for x in unique_facets if x is not facet1]

	# ensures that the query facets themselves are not included in the dimension reduction
	if facet1 in unique_facets: unique_facets.remove(facet1)
	if facet2 in unique_facets: unique_facets.remove(facet2)


	df = pd.DataFrame(index=unique_samples, columns=unique_facets)

	printcounter = 0
	for s in unique_samples:
		attributes_ = samples_dict.get(s)
		printcounter += 1
		if (printcounter % 500 == 0):
			print('Made it to dataframe row', printcounter,'/', len(unique_samples))
		for a in unique_facets:
			if a in attributes_:
				df.loc[s,a] = True
			else:
				df.loc[s,a] = False

				# this should be rewritten with pandas crosstab function to improve speed?

	if printcounter != len(unique_samples):
		outF.write('WARNING: Only made it to dataframe row' + ' ' + str(printcounter) + '/' + str(len(unique_samples)))
	else:
		outF.write('Full house, all samples present' + ' ' +  str(printcounter) + '/' + str(len(unique_samples)) + '\n')

	# df.to_csv('temp.csv')
	outF.write('DataFrame generated, Generating matrix...' + '\n')
	X = df.as_matrix()
	outF.write('Matrix generated' + '\n')

	return (X, unique_facets, unique_samples, facet1n2_sample_ids, facet1_sample_ids, facet2_sample_ids)

def prince_mca(X, facet1n2_sample_ids, facet1_sample_ids, facet2_sample_ids, pairID, unique_samples, unique_facets):
	facet1_trunc = facet1[0:15]
	facet2_trunc = facet2[0:15]

	outF.write('Started prince_mca module...' + '\n')

	df = pd.DataFrame(data = X, index = unique_samples, columns = unique_facets)


	mca = prince.MCA(df, n_components=2)
	v = mca.n_rows

	row_principal_coordinates = mca.row_principal_coordinates
	row_principal_coordinates.columns = ['x', 'y']

	# adding info to df for graph drawing

	row_principal_coordinates.index.name = 'id'
	row_principal_coordinates['Attribute'] = 0
	row_principal_coordinates.loc[row_principal_coordinates.index.isin(facet1_sample_ids), 'Attribute'] = facet1
	row_principal_coordinates.loc[row_principal_coordinates.index.isin(facet2_sample_ids), 'Attribute'] = facet2
	row_principal_coordinates.loc[row_principal_coordinates.index.isin(facet1n2_sample_ids), 'Attribute'] = 'both'

	# adds column describing spot frequency for depth visualisation
	row_principal_coordinates['s'] = row_principal_coordinates.groupby(['x','y']).transform('count')

	# # To see data input
	# print(row_principal_coordinates)
	mcaname = str('data/plots/mca_' + str(pairID) + '.dat')
	row_principal_coordinates.to_csv(mcaname)

	# try:
		# # producing 3D dimension reduction for mancluster.py (generally turned off in mancluster too)
		# mca3 = prince.MCA(df, n_components=3)
		# mca3_df = mca3.row_principal_coordinates
		# mca3_df.columns = ['x', 'y', 'z']
		# mca3_df.index.name = 'id'
		# mca3_df.loc[mca3_df.index.isin(facet1_sample_ids), 'Attribute'] = facet1
		# mca3_df.loc[mca3_df.index.isin(facet2_sample_ids), 'Attribute'] = facet2
		# mca3_df.loc[mca3_df.index.isin(facet1n2_sample_ids), 'Attribute'] = 'both'
		# mca3_df['s'] = mca3_df.groupby(['x','y', 'z']).transform('count')
		# mca3name = str('data/plots/mca3d_' + str(pairID) + '.dat')
		# mca3_df.to_csv(mca3name)
	# except ValueError: # an unknown issue which rarely occurs to reproduce run phenotypes and phenotype
		# continue

	return (row_principal_coordinates, mcaname)

def hiarachical_cluster(row_principal_coordinates, facet1, facet2, pairID):
	'''
	I'm using this method to draw a dendrogram tree so the user can visualise
	where the cluster cutoff should potentially be. This should help the human 
	make the cluster decision.
	'''

	X = row_principal_coordinates[['x','y']].as_matrix()

	# switch this on to check/use the best conditions my default is average and euclidean. stop outF default message
	# if coph later proves an unuseful determinant the best_params module should be skipped to speed up calculations

	# best_params = best_linkage(X)
	# best_method = best_params[0]
	# best_metric = best_params[1]
	# coph = best_params[2]
	# Z = linkage(X, best_method, best_metric)

	Z = linkage(X, 'average', 'euclidean')
	coph, coph_dists = cophenet(Z, pdist(X))
	outF.write('\n used default: method- average, metric- euclidean\n')

	# NB array has the format [idx1, idx2, dist, sample_count]


	# auto clustering useing fclusters default criterion='inconsistent'
	row_principal_coordinates['auto_cluster'] = fcluster(Z, 5, depth = 10)
	row_principal_coordinates['facet'] = ['facet 1' if ele == facet1 else 'facet 2' for ele in row_principal_coordinates['Attribute']]
	# print(row_principal_coordinates)


	'''
	DRAWING GRAPHS
	+ hiarachical dendrogram with matlibplot
	'''

	# drawing dendrogram with matlibplot

	names = row_principal_coordinates['facet'].tolist()
	label_colors = {'facet 1': 'b', 'facet 2': 'r'}

	# These are the "Tableau 20" colors as RGB.    
	tableau20 = [(31, 119, 180), (174, 199, 232), (255, 127, 14), (255, 187, 120),\
				(44, 160, 44), (152, 223, 138), (214, 39, 40), (255, 152, 150),\
				(148, 103, 189), (197, 176, 213), (140, 86, 75), (196, 156, 148),\
				(227, 119, 194), (247, 182, 210), (127, 127, 127), (199, 199, 199),\
				(188, 189, 34), (219, 219, 141), (23, 190, 207), (158, 218, 229)]


	# Scale the RGB values to the [0, 1] range, which is the format matplotlib accepts.
	for i in range(len(tableau20)):
		r, g, b = tableau20[i]
		tableau20[i] = (r / 255., g / 255., b / 255.)


	plt.figure(figsize=(12, 8))
	# plt.title('Hierarchical Clustering Dendrogram')
	# plt.xlabel('samples')
	plt.ylabel('distance')
	dendrogram(
		Z,
		p = 20, # only show top 50 merges
		leaf_rotation=90.,  # rotates the x axis labels
		leaf_font_size=8.,  # font size for the x axis labels

		# # use this for compression of huge dendrograms
		# show_contracted = True,
		# truncate_mode='lastp',

		show_leaf_counts=True,

		# x labels
		labels=names
		
	)
	ax = plt.gca()
	xlbls = ax.get_xmajorticklabels()
	for lbl in xlbls:
		lbl.set_color(label_colors[lbl.get_text()])
	legend = ax.legend(loc='upper center', shadow=True)

	# Ensure that the axis ticks only show up on the bottom and left of the plot.
	ax.get_xaxis().tick_bottom()
	ax.get_yaxis().tick_left()
	# Get rid of the box
	ax.spines["top"].set_visible(False)
	ax.spines["bottom"].set_visible(False)
	ax.spines["right"].set_visible(False)
	ax.spines["left"].set_visible(False)
	facet_label = str('facet 1: ' + facet1 + '\nfacet2: ' + facet2)
	ax.text(0, -0.2, facet_label, fontsize=10)

	plotname = str('data/plots/dendro_' + str(pairID) + '.svg')
	plt.savefig(plotname, format='svg', dpi=600) 
	# plt.show()
	plt.clf()
	plt.close('all')



	return plotname

def best_linkage(X):

	# Tests multiple options for linkage for the hiarachical clustering
	# not automatically switched on.

	method_options = ['single', 'complete', 'average', 'weighted', 'centroid', 'median', 'ward']
	metric_options = ['euclidean', 'cityblock', 'hamming', 'cosine']
	
	best_method_score = 0
	best_method = ''
	for u in method_options:
		Z = linkage(X, u)
		coph, coph_dists = cophenet(Z, pdist(X))
		# print('Method:', u, 'gave cophenetic correlation distance', coph)
		if coph > best_method_score:
			best_method_score = coph
			best_method = u
	# print('Best method is', best_method)

	best_metric_score = 0
	best_metric = ''
	if best_method is not 'ward':
		for q in metric_options:
			Z = linkage(X, best_method, q)
			coph, coph_dists = cophenet(Z, pdist(X))
			# print('Within', best_method, ',', q, 'gave score', coph)
			if coph > best_metric_score:
				best_metric_score = coph
				best_metric = q

	print('Best linkage method is', best_method, 'using metric', best_metric)
	print('Score:', best_metric_score)

	outF.write('\n' + 'Best linkage method is ' + str(best_method) + ' using metric ' + str(best_metric) + '\n' + 'Score: ' + str(best_metric_score))
	return (best_method, best_metric, best_metric_score)

def mcadraw(row_principal_coordinates, pairID):

	# need to add subplots/extra plots, bar chart and different size of dot representations

	# mca result scatterplot

	g = sns.lmplot('x', 'y', data=row_principal_coordinates, hue='Attribute',\
	scatter_kws={"s": ((((row_principal_coordinates['s'] / row_principal_coordinates['s'].max()) * 300)+10))},\
	fit_reg = False, legend=False)
	# resize figure box to -> put the legend out of the figure
	box = g.ax.get_position() # get position of figure
	g.ax.set_position([box.x0, box.y0, box.width * 0.85, box.height * 0.8]) # resize position
	# Put a legend to the right side
	g.ax.legend(loc='best', bbox_to_anchor=(1, 1.2), ncol=1)

	plotname = str('data/plots/mcaplot_' + str(pairID) + '.svg')
	plt.savefig(plotname, format='svg', dpi=600)
	plt.clf()
	plt.close('all')

	return plotname

def run_calcs(facet1, facet2, missing_count, already_computed_count, newly_computed_count, pairID, n):
	# do the calculations

	data_build = build_matrix(facet1, facet2)


	if data_build is None: # ensure that we have some value info in the input

		missing_count +=1
		print()
		print()
		print('AN ATTRIBUTE DOESN\'T HAVE ANY SAMPLES IN samples.csv')
		print('data build is None')
		print('--------------------------------------------')
		print('Attribute 1: '+ facet1)
		print('Attribute 2: '+ facet2)
		print('id: ' + str(pairID))
		print('--------------------------------------------')	
		print('Missed '+ str(missing_count)+' so far!')
		outF.write('--------------------------------------------\n')
		outF.write('MISSED PAIR ' + str(missing_count)+'\n')
		outF.write(str(facet1)+'\n')
		outF.write(str(facet2)+'\n\n')

	else: # aka we have some sample info for both attributes so we can crack on (except ones that are too big these are not in the data_build)

		X = data_build[0]
		unique_facets = data_build[1]
		unique_samples = data_build[2]
		facet1n2_sample_ids = data_build[3]
		facet1_sample_ids = data_build[4]
		facet2_sample_ids = data_build[5]

		tot_samples_affected = len(unique_samples)
		samples_in_a1 = len(facet1_sample_ids)
		samples_in_a2 = len(facet2_sample_ids)
		samples_in_both = len(facet1n2_sample_ids)

		newly_computed_count += 1

		# print(data_build[0])
		# print(data_build[1])
		# print(data_build[2])
		# print(data_build[3])
		# print(data_build[4])
		# print(data_build[5])

		
		# Principal Component Analysis / Multiple Correspondence Analysis

		mca_results = prince_mca(X, facet1n2_sample_ids, facet1_sample_ids, facet2_sample_ids, pairID, unique_samples, unique_facets)
		row_principal_coordinates = mca_results[0]
		mca_data = mca_results[1]

		# print(mca_results[0])
		# print(mca_results[1])

		# Temporary Output

		print()
		print()
		print('NEWLY CALCULATED')
		print('--------------------------------------------')
		print('Attribute 1: '+ facet1)
		print('Attribute 2: '+ facet2)
		print('id: ' + str(pairID))
		print('--------------------------------------------')	
		print('no of samples in pair:', tot_samples_affected)
		print('no of samples in attribute 1:', samples_in_a1)
		print('no of samples in attribute 2:', samples_in_a2)
		print()
		print('No. of missing pairs so far: ', missing_count)
		print('Pairs previously computed so far: ', already_computed_count)
		print('Pairs newly computed so far: ', newly_computed_count)

		outF.write('--------------------------------------------\n')
		outF.write('NEWLY CALCULATED ' + str(newly_computed_count)+'\n')
		outF.write('Attribute 1: ' + str(facet1)+'\n')
		outF.write('Attribute 2: ' + str(facet2)+'\n')

		# Generate Scatterplot

		# mca_plot = mcadraw(row_principal_coordinates, pairID) # mca result scatterplot
		# outF.write('id: ' + str(pairID)+'\n')
		# outF.write('Scatter plot generated. See ' + mca_plot + '\n\n')
		# dendro_plot = hiarachical_cluster(row_principal_coordinates, facet1, facet2, pairID)


		# put the calculations back into graph db

		autocluster_update_timestamp = get_timestamp()

		n['p']['total_no_of_samples_in_pair'] = (len(facet1_sample_ids) + len(facet2_sample_ids))
		n['p']['no_of_samples_in_attribute_1'] = len(facet1_sample_ids)
		n['p']['no_of_samples_in_attribute_2'] = len(facet2_sample_ids)
		n['p']['no_of_shared_samples_in_pair'] = len(facet1n2_sample_ids)
		# n['p']['mca_plot'] = mca_plot
		n['p']['mca_data'] = mca_data
		# n['p']['dendro_plot'] = dendro_plot
		n['p']['autocluster_update_timestamp'] = autocluster_update_timestamp

		graph.push(n['p'])
		
		# delete existing Sample to Pair relationships

		pair_name = n["p"]["name"]
		# p = graph.node(pairID)
		graph_cursor = graph.run('MATCH (u:Pair)-[r:HAS_ATTRIBUTE]-(:Sample) WHERE ID(u) = $p RETURN r', parameters={"p":pairID})
		# graph_cursor = graph.run('MATCH (:Sample)-[r:HAS_ATTRIBUTE]->(u:Pair) WHERE ID(u) = $p RETURN r', parameters={"p":p})
		# graph_cursor = graph.run('MATCH (:Sample {sampleID:"SAMEA714557"})-[r]-(:Sample) RETURN r')

		while graph_cursor.forward():
			subgraph = graph_cursor.current().subgraph()
			tr = graph.begin()
			tr.separate(subgraph)
			tr.commit()

		# create sample nodes that connect to cluster nodes
		# by default these connect to no clusters only samples (aka no clusters) prior to human k input

		# store = Store(n)

		# print(type(n))
		# sys.exit()

		p = graph.evaluate('MATCH (u:Pair) WHERE ID(u) = $p RETURN u', parameters={"p":pairID})

		for sID in facet1n2_sample_ids:

			h = Node('Sample', sampleID = sID) # create cypher object
			graph.merge(h, 'Sample', 'sampleID') # merge is important to prevent duplicates
			f = Relationship(h, 'HAS_ATTRIBUTE', p, attribute='both')
			graph.merge(f) # adding relationship to graph

		for sID in facet1_sample_ids:

			h = Node('Sample', sampleID = sID) # create cypher object
			graph.merge(h, 'Sample', 'sampleID') # merge is important to prevent duplicates
			f = Relationship(h, 'HAS_ATTRIBUTE', p, attribute=facet1)
			graph.merge(f) # adding relationship to graph


		for sID in facet2_sample_ids:

			h = Node('Sample', sampleID = sID) # create cypher object
			graph.merge(h, 'Sample', 'sampleID') # merge is important to prevent duplicates
			f = Relationship(h, 'HAS_ATTRIBUTE', p, attribute=facet2)
			graph.merge(f) # adding relationship to graph


	return [missing_count, newly_computed_count]




if __name__ == '__main__':
# def run():

	# args
	sys.setrecursionlimit(10000)

	parser = argparse.ArgumentParser(description='Clusters/dimension rediction of all samples that have attribute 1 and/or attribute2')
	parser.add_argument('--recalculate', '-r', action='store_true', help='recalculates and rewrites all clustering for all pairs')
	run_mode = parser.parse_args()
	recalculate_arg = (run_mode.recalculate)

	# initialise database graph
	print('Initialising graph and run logs...')
	graph = Graph('http://localhost:7474/db/data', user='neo4j', password='neo5j')

	# writing output
	start_timestamp = get_timestamp()
	logname = str('log/' + start_timestamp + '_autocluster.log')
	with open(logname, 'w') as outF:
		outF.write('LOG FILE for cluster.py\n\n' + 'Start time: ' + start_timestamp + '\n')


		pairs_total = graph.data("MATCH (p:Pair) RETURN count(*) AS total") # just for tqdm
		pairs_total_asNum = pairs_total[0]['total']

		missing_count = 0
		already_computed_count = 0
		newly_computed_count = 0


		# reading samples.csv into memory
		print('Loading samples.csv to memory for attribute frequency counting...')
		all_words = re.findall(r'\w+', open('data/samples.csv').read()) # this functionality doubles memory needs but it is the fastest method of counting

		# # This can read the samples.csv into a dataframe
		# samples_df = pd.read_csv('samples.csv', sep = '\n', names=['SampleID'])
		# cols = ['SampleID','Attributes']
		# samples_df[cols]=samples_df.SampleID.str.split(',', n=1, expand=True)
		# samples_df.Attributes = samples_df.Attributes.str.split(',')



		if not recalculate_arg: # argument passed at command line to recalculate all nodes

			for n in tqdm(graph.run("MATCH (p:Pair) RETURN p, id(p) ORDER BY p.pseudo_confidence DESC"),total = pairs_total_asNum, unit = 'pairs'):
				facet1 = n["p"]["bad_attribute"]
				facet2 = n["p"]["good_attribute"]

				facet1_ = (facet1[:15] + '..') if len(facet1) > 15 else facet1 # truncated name option used for graph titles
				facet2_ = (facet2[:15] + '..') if len(facet2) > 15 else facet2 # truncated name option used for graph titles
				pairID = n["id(p)"]


				# check if calculations have already been done

				try: # aka all of this has been done so skip it
					tot_samples_affected = n['p'].properties['total_no_of_samples_in_pair']
					samples_in_a1 = n['p'].properties['no_of_samples_in_attribute_1']
					samples_in_a2 = n['p'].properties['no_of_samples_in_attribute_2']
					samples_in_both = n['p'].properties['no_of_shared_samples_in_pair']
					mca_plot = n['p'].properties['mca_plot']
					mca_data = n['p'].properties['mca_data']
					dendro_plot = n['p'].properties['dendro_plot']
					autocluster_update_timestamp = n['p'].properties['autocluster_update_timestamp']
				

					already_computed_count += 1

					# Temporary Output

					print()
					print()
					print('PREVIOUSLY CALCULATED')
					print('--------------------------------------------')
					print('Attribute 1: '+ facet1)
					print('Attribute 2:' + facet2)
					print('id: ' + str(pairID))
					print('--------------------------------------------')	
					print('no of samples in pair:', tot_samples_affected)
					print('no of samples in attribute 1:', samples_in_a1)
					print('no of samples in attribute 2:', samples_in_a2)


					print()
					print('No. of missing pairs so far: ', missing_count)
					print('Pairs previously computed so far: ', already_computed_count)
					print('Pairs newly computed so far: ', newly_computed_count)

				except: # aka at least one calc is missing so redo them


					# quick check for attribute counts
					
					facet1_count = int(Counter(all_words)[facet1])
					facet2_count = int(Counter(all_words)[facet2])

					problem_facet = None

					# see if the attribute is very large

					if facet1_count > 10000 or facet2_count > 10000:
						if facet1_count > 10000:
							problem_facet = facet1
							facet1 = str(facet1 + ' IS TOO BIG!!!')
						elif facet2_count > 10000:
							problem_facet = facet2
							facet2 = str(facet2 + ' IS TOO BIG!!!')
					if facet1_count > 10000 and facet2_count > 10000:
						problem_facet = 'both facets'


						print()
						print()
						print('AN ATTRIBUTE HAS TOO MANY SAMPLES FOR ANALYSIS')
						print('--------------------------------------------')
						print('Attribute 1: '+ str(facet1))
						print('Attribute 1 Count: '+ str(facet1_count))
						print('Attribute 2: '+ str(facet2))
						print('Attribute 2 Count: '+ str(facet2_count))
						print('id: ' + str(pairID))
						print('--------------------------------------------')
						print('Missed '+ str(missing_count)+' so far!')
						print(problem_facet + ' frequency is > 10,000 samples')
						print()
						outF.write('--------------------------------------------\n')
						outF.write(str(problem_facet) + ' frequency is > 10,000 samples')
						outF.write(str(facet1)+'\n')
						outF.write(str(facet2)+'\n\n')
						

					if problem_facet == 'both facets':
						missing_count +=1
						print('BOTH FACETS ARE TOO BIG!!!')
						continue
					
					if facet1_count == 0 or facet2_count == 0:

						missing_count +=1
						print()
						print()
						print('AN ATTRIBUTE DOESN\'T HAVE ANY SAMPLES IN samples.csv')
						print('--------------------------------------------')
						print('Attribute 1: '+ facet1)
						print('Attribute 2: '+ facet2)
						print('id: ' + str(pairID))
						print('Attribute 2 Count: '+ str(facet2_count))
						print('Attribute 2 Count: '+ str(facet2_count))
						print('--------------------------------------------')
						print('Missed '+ str(missing_count)+' so far!')
						outF.write('--------------------------------------------\n')
						outF.write('MISSED PAIR ' + str(missing_count)+'\n')
						outF.write(str(facet1)+'\n')
						outF.write(str(facet2)+'\n\n')
						outF.write('Attribute 1 Count: '+ str(facet1_count))
						outF.write('Attribute 2 Count: '+ str(facet2_count))
						continue

					if (facet1_count <= 2 and facet2_count <= 2) or ((facet1_count > 10000 or facet2_count > 10000) and (facet1_count <= 2 or facet2_count <= 2)):

						missing_count +=1
						print()
						print()
						print('AN ATTRIBUTE HAD 1 OR 2 SAMPLES IN samples.csv')
						print('MCA cannot be performed on 1 sample')
						print('This has been logged')
						print('--------------------------------------------')
						print('Attribute 1: '+ facet1)
						print('Attribute 2: '+ facet2)
						print('id: ' + str(pairID))
						print('--------------------------------------------')
						print('Missed '+ str(missing_count)+' so far!')
						outF.write('--------------------------------------------\n')
						outF.write('AN ATTRIBUTE ONLY HAS 1 SAMPLE IN samples.csv')
						outF.write('MCA cannot be performed on 1 sample')
						outF.write(str(facet1)+'\n')
						outF.write(str(facet2)+'\n\n')
						continue





					calc_counts = run_calcs(facet1, facet2, missing_count, already_computed_count, newly_computed_count, pairID, n)
					missing_count = calc_counts[0]
					newly_computed_count = calc_counts[1]


		elif recalculate_arg: # argument passed at commandline to recalculate stats

			for n in tqdm(graph.run("MATCH (p:Pair) RETURN p, id(p) ORDER BY p.pseudo_confidence DESC"),total = pairs_total_asNum, unit = 'pairs'):
				facet1 = n["p"]["bad_attribute"]
				facet2 = n["p"]["good_attribute"]
				facet1_ = (facet1[:15] + '..') if len(facet1) > 15 else facet1 # truncated name option used for graph titles
				facet2_ = (facet2[:15] + '..') if len(facet2) > 15 else facet2 # truncated name option used for graph titles
				pairID = n["id(p)"]

				# notice that in this mode we do not check if calculations have already been done.

				# quick check for attribute counts
					
				facet1_count = int(Counter(all_words)[facet1])
				facet2_count = int(Counter(all_words)[facet2])

				problem_facet = None


				if facet1_count > 10000 or facet2_count > 10000:
					if facet1_count > 10000:
						problem_facet = facet1
						facet1 = str(facet1 + ' IS TOO BIG!!!')
					elif facet2_count > 10000:
						problem_facet = facet2
						facet2 = str(facet2 + ' IS TOO BIG!!!')
					elif facet1_count > 10000 and facet2_count > 10000:
						problem_facet = 'both facets'


					print()
					print()
					print('AN ATTRIBUTE HAS TOO MANY SAMPLES FOR ANALYSIS')
					print('--------------------------------------------')
					print('Attribute 1: '+ str(facet1))
					print('Attribute 1 Count: '+ str(facet1_count))
					print('Attribute 2: '+ str(facet2))
					print('Attribute 2 Count: '+ str(facet2_count))
					print('id: ' + str(pairID))
					print('--------------------------------------------')
					print('Missed '+ str(missing_count)+' so far!')
					print(problem_facet + ' frequency is > 10,000 samples')
					print()
					outF.write('--------------------------------------------\n')
					outF.write(str(problem_facet) + ' frequency is > 10,000 samples')
					outF.write(str(facet1)+'\n')
					outF.write(str(facet2)+'\n\n')
					

				if problem_facet is 'both facets':
					missing_count +=1
					continue
				
				if (facet1_count or facet2_count) == 0:

					missing_count +=1
					print()
					print()
					print('AN ATTRIBUTE DOESN\'T HAVE ANY SAMPLES IN samples.csv')
					print('--------------------------------------------')
					print('Attribute 1: '+ facet1)
					print('Attribute 2: '+ facet2)
					print('id: ' + str(pairID))
					print('Attribute 2 Count: '+ str(facet2_count))
					print('Attribute 2 Count: '+ str(facet2_count))
					print('--------------------------------------------')
					print('Missed '+ str(missing_count)+' so far!')
					outF.write('--------------------------------------------\n')
					outF.write('MISSED PAIR ' + str(missing_count)+'\n')
					outF.write(str(facet1)+'\n')
					outF.write(str(facet2)+'\n\n')
					outF.write('Attribute 1 Count: '+ str(facet1_count))
					outF.write('Attribute 2 Count: '+ str(facet2_count))
					continue

				if (facet1_count <= 2 and facet2_count <= 2) or ((facet1_count > 10000 or facet2_count > 10000) and (facet1_count <= 2 or facet2_count <= 2)):

					missing_count +=1
					print()
					print()
					print('AN ATTRIBUTE HAD 1 OR 2 SAMPLES IN samples.csv')
					print('MCA cannot be performed on 1 sample')
					print('This has been logged')
					print('--------------------------------------------')
					print('Attribute 1: '+ facet1)
					print('Attribute 2: '+ facet2)
					print('id: ' + str(pairID))
					print('--------------------------------------------')
					print('Missed '+ str(missing_count)+' so far!')
					outF.write('--------------------------------------------\n')
					outF.write('AN ATTRIBUTE ONLY HAS 1 SAMPLE IN samples.csv')
					outF.write('MCA cannot be performed on 1 sample')
					outF.write(str(facet1)+'\n')
					outF.write(str(facet2)+'\n\n')
					continue

				calc_counts = run_calcs(facet1, facet2, missing_count, already_computed_count, newly_computed_count, pairID)
				missing_count = calc_counts[0]
				newly_computed_count = calc_counts[1]



