"""
Calculates various ditances between two attributes in a graph
of note Attribute Similarities & Jaccard Coefficient which give
unweighted and weighted connection estimations

Key Features:
- looks at Neo4J pair nodes to get attributes to calculate distances on
- updates the Neo4J DB directly after calculating properties of a node
- pairs are loaded in based on 'confidence score' this can be manupulated elsewhere to rank calculations
- in normal (unflagged mode) the program will skip nodes that already have the info
- if you want to recaclulate information for all nodes (after an update or something) pass -r in command line

Further Work:
- try to implement M.E.J. Newman method
- thinking about how I might implement wider changes and new graph distances
- implement another run mode that checks timestamp and updates old calculations

"""
from py2neo import Node, Relationship, Graph, Path, authenticate
import numpy as np
import networkx as nx
from matplotlib import pylab
import matplotlib.pyplot as plt
import pandas as pd
import sys
from tqdm import tqdm
import datetime
import argparse

def get_timestamp():
	""" 
	Get timestamp of current date and time. 
	"""
	timestamp = '{:%Y-%m-%d_%H-%M-%S}'.format(datetime.datetime.now())
	return timestamp

def load_graph(graph):
	print('loading graph....')
	G = nx.read_gexf('data/coexistences.gexf')
	return G

def edge_connections(facet1, facet2):
	# break_no is min no. nodes removed to break all paths source to target
	# maybe this / average or total freq would be interesting
	# print('calculating break number....')
	break_no = nx.node_connectivity(G, facet1, facet2)

	# print('calculating degrees...')
	degree1 = nx.degree(G, facet1)
	degree2 = nx.degree(G, facet2)
	edge_total = degree1 + degree2
	# what fraction of their partner attributes do they share?
	# similar to Jaccard without weighting
	attribute_sim = (break_no*2)/edge_total

	return (break_no, degree1, degree2, edge_total, attribute_sim)

def weighted_connections(facet1, facet2):

	# print('getting edge weight....')
	try:
		edge = G.get_edge_data(facet1,facet2)
		edge_weight = edge.get('weight')
	except AttributeError:
		edge_weight = 0

	# print('calculating Jaccard coefficient....')
	jc = nx.jaccard_coefficient(G, [(facet1, facet2)])
	jc2 = next(jc)
	jaccard_coefficient = jc2[2]

	return (edge_weight, jaccard_coefficient)



# if __name__ == '__main__':
def run():

	# # Test Box

	# facet1 = 'frozenDessertFrequency'
	# facet2 = 'frozenDesertFrequency'

	# facet1 = 'latitude'
	# facet2 = 'longitude'

	# facet1 = 'serovar'
	# facet2 = 'sex'

	# G = load_graph('data/coexistences.gexf')
	# weighted_edge_calcs = weighted_connections(facet1, facet2)
	# edge_weight = weighted_edge_calcs[0]
	# print(facet1)
	# print(facet2)
	# print(edge_weight)
	# sys.exit()

	
	# args
	parser = argparse.ArgumentParser(description='Calculates various distances between two attributes from the coexistance graph.')
	parser.add_argument('--recalculate', '-r', action='store_true', help='recalculates and rewrites all stats for all pairs')
	run_mode = parser.parse_args()
	recalculate_arg = (run_mode.recalculate)

	
	# open log file
	start_timestamp = get_timestamp()
	logname = str('log/' + start_timestamp + '_coexistence.log')
	with open(logname, 'w') as outF:
		outF.write('LOG FILE for coexistence.py\n\n' + 'Start time: ' + start_timestamp + '\n')


		# initialise database graph
		graph = Graph('http://localhost:7474/db/data', user='neo4j', password='neo5j')

		# initialise coexistance graph
		G = load_graph('data/coexistences.gexf')

		# attribute pairs input

		pairs_total = graph.data("MATCH (p:Pair) RETURN count(*) AS total") # just for tqdm
		pairs_total_asNum = pairs_total[0]['total']

		missing_count = 0
		already_computed_count = 0
		newly_computed_count = 0


		if not recalculate_arg: # argument passed at command line to recalculate all nodes

			for n in tqdm(graph.run("MATCH (p:Pair) RETURN p ORDER BY p.pseudo_confidence DESC"),total = pairs_total_asNum, unit = 'pairs'):
				facet1 = n["p"]["bad_attribute"]
				facet2 = n["p"]["good_attribute"]


				if G.has_node(facet1) and G.has_node(facet2): # checking if attributes are in the networkX graph and skip & log if not

					# check if calculations have already been done

					try:
						edge_weight = n["p"].properties['edge_weight']
						jaccard_coefficient = n["p"].properties['jaccard_coefficient']
						break_no = n["p"].properties['break_no']
						degree1 = n["p"].properties['degree1']
						degree2 = n["p"].properties['degree2']
						edge_total = n["p"].properties['edge_total']
						attribute_sim = n["p"].properties['attribute_sim']
						already_computed_count += 1

						# Temporary Output

						print()
						print()
						print('PREVIOUSLY CALCULATED')
						print('--------------------------------------------')
						print('Attribute 1: '+ str(facet1))
						print('Attribute 2:' + str(facet2))
						print('--------------------------------------------')	
						print('Break No.:', break_no)
						print('Degree Total:', edge_total)
						print(facet1,':', degree1)
						print(facet2,':', degree2)
						print('Attribute Similarities:', attribute_sim)
						print('Jaccard Coefficient:', jaccard_coefficient)
						print('Edge Weight:', edge_weight)
						print()
						print('No. of missing pairs so far: ', missing_count)
						print('Pairs previously computed so far: ', already_computed_count)
						print('Pairs newly computed so far: ', newly_computed_count)


					except KeyError:

						# coexistance graph calculations


						unweighted_edge_calcs = edge_connections(facet1, facet2)
						weighted_edge_calcs = weighted_connections(facet1, facet2)

						edge_weight = weighted_edge_calcs[0]
						jaccard_coefficient = weighted_edge_calcs[1]
						break_no = unweighted_edge_calcs[0]
						degree1 = unweighted_edge_calcs[1]
						degree2 = unweighted_edge_calcs[2]
						edge_total = unweighted_edge_calcs[3]
						attribute_sim = unweighted_edge_calcs[4]

						# put the calculations back into graph db

						n['p']['edge_weight'] = edge_weight
						n['p']['jaccard_coefficient'] = jaccard_coefficient
						n['p']['break_no'] = break_no
						n['p']['degree1'] = degree1
						n['p']['degree2'] = degree2
						n['p']['edge_total'] = edge_total
						n['p']['attribute_sim'] = attribute_sim
						n['p']['coexistance_update_timestamp'] = get_timestamp()
						graph.push(n['p'])
						newly_computed_count += 1

						print()
						print()
						print('NEWLY CALCULATED')
						print('--------------------------------------------')
						print('Attribute 1: '+ str(facet1))
						print('Attribute 2:' + str(facet2))
						print('--------------------------------------------')	
						print('Break No.:', break_no)
						print('Degree Total:', edge_total)
						print(facet1,':', degree1)
						print(facet2,':', degree2)
						print('Attribute Similarities:', attribute_sim)
						print('Jaccard Coefficient:', jaccard_coefficient)
						print('Edge Weight:', edge_weight)
						print()
						print('No. of missing pairs so far: ', missing_count)
						print('Pairs previously computed so far: ', already_computed_count)
						print('Pairs newly computed so far: ', newly_computed_count)

						outF.write('--------------------------------------------\n')
						outF.write('NEWLY CALCULATED ' + str(newly_computed_count)+'\n')
						outF.write(str(facet1)+'\n')
						outF.write(str(facet2)+'\n\n')


				else: # if one or more attributes are missing

					# need to write the missing facets to log file
					missing_count +=1
					print()
					print()
					print('ATTRIBUTE MISSING FROM INPUT GRAPH')
					print('--------------------------------------------')
					print('Attribute 1: '+ str(facet1))
					print('Attribute 2:' + str(facet2))
					print('--------------------------------------------')	
					print('Missed '+ str(missing_count)+' so far!')

		else:

			for n in tqdm(graph.run("MATCH (p:Pair) RETURN p ORDER BY p.confidence DESC"),total = pairs_total_asNum, unit = 'pairs'):
				facet1 = n["p"]["bad_facet"]
				facet2 = n["p"]["good_facet"]


				if G.has_node(facet1) and G.has_node(facet2): # checking if attributes are in the networkX graph and skip & log if not

					# NB here we don't check if the node has the info already we just rewrite everything.
					# coexistance graph calculations

					unweighted_edge_calcs = edge_connections(facet1, facet2)
					weighted_edge_calcs = weighted_connections(facet1, facet2)

					edge_weight = weighted_edge_calcs[0]
					jaccard_coefficient = weighted_edge_calcs[1]
					break_no = unweighted_edge_calcs[0]
					degree1 = unweighted_edge_calcs[1]
					degree2 = unweighted_edge_calcs[2]
					edge_total = unweighted_edge_calcs[3]
					attribute_sim = unweighted_edge_calcs[4]

					# put the calculations back into graph db

					n['p']['edge_weight'] = edge_weight
					n['p']['jaccard_coefficient'] = jaccard_coefficient
					n['p']['break_no'] = break_no
					n['p']['degree1'] = degree1
					n['p']['degree2'] = degree2
					n['p']['edge_total'] = edge_total
					n['p']['attribute_sim'] = attribute_sim
					n['p']['coexistance_update_timestamp'] = timestamp
					graph.push(n['p'])
					newly_computed_count += 1

					print()
					print()
					print('NEWLY CALCULATED')
					print('--------------------------------------------')
					print('Attribute 1: '+ str(facet1))
					print('Attribute 2:' + str(facet2))
					print('--------------------------------------------')	
					print('Break No.:', break_no)
					print('Degree Total:', edge_total)
					print(facet1,':', degree1)
					print(facet2,':', degree2)
					print('Attribute Similarities:', attribute_sim)
					print('Jaccard Coefficient:', jaccard_coefficient)
					print('Edge Weight:', edge_weight)
					print()
					print('No. of missing pairs so far: ', missing_count)
					print('Pairs previously computed so far: ', already_computed_count)
					print('Pairs newly computed so far: ', newly_computed_count)

					outF.write('--------------------------------------------\n')
					outF.write('NEWLY CALCULATED ' + str(newly_computed_count)+'\n')
					outF.write(str(facet1)+'\n')
					outF.write(str(facet2)+'\n\n')


				else: # if one or more attributes are missing

					# need to write the missing facets to log file
					missing_count +=1
					print()
					print()
					print('ATTRIBUTE MISSING FROM INPUT GRAPH')
					print('--------------------------------------------')
					print('Attribute 1: '+ str(facet1))
					print('Attribute 2:' + str(facet2))
					print('--------------------------------------------')	
					print('Missed '+ str(missing_count)+' so far!')


		# ideally this output would write out as the process was going rather than just at the end.

		end_timestamp = get_timestamp()
		outF.write('End time: ' + str(end_timestamp) + '\n\n')
		outF.write('Pairs missed: ' + str(missing_count) + '\n')
		outF.write('Pairs previously computed: ' + str(already_computed_count) + '\n')
		outF.write('Pairs computed in this run: ' + str(newly_computed_count) + '\n')
		outF.write('Total pairs: ' + str(pairs_total_asNum) + '\n')
		outF.write('N.B. Pairs are missed when one or both of the attributes cannot \nbe found in the coexistance database\n')



	



	# # Unused

	# print(nx.average_clustering(G)) # on whole graph takes forever
	# see https://networkx.github.io/documentation/networkx-1.10/reference/algorithms.link_prediction.html

	# see popular frequencies in a histogram on whole graph
	# graphs = nx.degree_histogram(G)
	# print(graphs)
















