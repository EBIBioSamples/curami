'''
Manual clustering script that runs onc euser has provided k. It then performs k-means clustering
adds cluster nodes to the Neo4j DB no.1-> k. Adds relationships:

(Sample)-[IN_CLUSTER]->(Cluster)
(Pair)-[HAS_CLUSTER]->(Cluster)
'''
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from py2neo import Node, Relationship, Graph, Path, authenticate, remote
from tqdm import tqdm
import datetime
import argparse
import sys, csv
from sklearn.cluster import KMeans
from scipy.spatial.distance import cdist


def get_timestamp():
	"""
	Get timestamp of current date and time.
	"""
	timestamp = '{:%Y-%m-%d_%H-%M-%S}'.format(datetime.datetime.now())
	return timestamp


def run_KMeans(pairID, k):
	# KMeans

	MCAdata = ('data/plots/mca_' + str(pairID) + '.dat')

	# for 3d
	# df = pd.read_csv('data/plots/mca3d_22.dat', header=0, index_col=0)
	# df2 = df[['x', 'y', 'z']]

	# for 2d
	df = pd.read_csv(MCAdata, header=0, index_col=0)
	df2 = df[['x', 'y']]

	kmeans = KMeans(n_clusters=k)
	kmeans.fit(df2)
	labels = kmeans.predict(df2)  # same as clusassign = kmeans.fit_predict(X.as_matrix())
	df['clusterID'] = labels

	# get cluster representatives and centroids

	centroids = kmeans.cluster_centers_
	min_dist = np.min(cdist(df2.as_matrix(), kmeans.cluster_centers_, 'euclidean'), axis=1)
	Y = pd.DataFrame(min_dist, index=df2.index, columns=['Center_euclidean_dist'])
	Z = pd.DataFrame(labels, index=df2.index, columns=['cluster_ID'])
	PAP = pd.concat([Y, Z], axis=1)
	grouped = PAP.groupby(['cluster_ID'])
	reps_df = grouped.idxmin()
	reps_dict_ = reps_df.to_dict()
	reps_dict = reps_dict_.get('Center_euclidean_dist')  # the best representatives of each cluster as a dictionary
	reps_list = list(reps_dict.values())

	all_reps = []  # the facets belonging to the representatives
	with open('data/samples.csv', 'r') as f_in:
		for line in f_in:
			data_list = line.rstrip().split(',')
			if data_list[0] in reps_list:
				cluster_no = list(reps_dict.keys())[list(reps_dict.values()).index(data_list[0])]
				representative_ID = data_list[0]
				representative_attributes = data_list[1:]
				reps = [cluster_no] + [representative_ID] + representative_attributes
				all_reps.append(reps)

	plotname = mcadraw(df, pairID)
	return (df, reps_dict, all_reps, plotname)


def mcadraw(row_principal_coordinates, pairID):
	# need to add subplots/extra plots, bar chart and different size of dot representations

	# mca result scatterplot

	g = sns.lmplot('x', 'y', data=row_principal_coordinates, hue='clusterID', \
	               scatter_kws={
		               "s": ((((row_principal_coordinates['s'] / row_principal_coordinates['s'].max()) * 300) + 10))}, \
	               fit_reg=False, legend=False)
	# resize figure box to -> put the legend out of the figure
	box = g.ax.get_position()  # get position of figure
	g.ax.set_position([box.x0, box.y0, box.width * 0.85, box.height * 0.8])  # resize position
	# Put a legend to the right side
	g.ax.legend(loc='best', bbox_to_anchor=(1, 1.2), ncol=1)

	plotname = str('data/plots/kplot_' + str(pairID) + '.png')
	plt.savefig(plotname, format='png', dpi=600)

	# plt.show()

	return plotname


def clus2Neo(n):
	# operation just needs a Pair node object
	mancluster_update_timestamp = get_timestamp()
	pairID = remote(n[0])._id
	k = n[0]['k']
	results = run_KMeans(pairID, k)
	df = results[0]
	reps_dict = results[1]
	all_reps = results[2]
	plotname = results[3]

	# throw reslts back to Neo4J Node
	for n in graph.run('MATCH (p:Pair) WHERE ID(p) = $pairID RETURN p', parameters={"pairID": pairID}):
		n['p']['mancluster_update_timestamp'] = mancluster_update_timestamp
		n['p']['KClus_representatives'] = str(all_reps)
		n['p']['KClus_plot'] = plotname
		graph.push(n['p'])

		# delete any previous (Pair)->(Cluster)<-(Sample) clusters and relationships on the Pair
		# The following must be carried out in sequence!

		# del the HAS_CLUSTER relationship for given Pair
		cluster_cursor = graph.run('MATCH (p:Pair)-[r:HAS_CLUSTER]-(c:Cluster) WHERE ID(p) = $pairID RETURN r',
		                           parameters={"pairID": pairID})
		while cluster_cursor.forward():
			subgraph = cluster_cursor.current().subgraph()
			tr = graph.begin()
			tr.separate(subgraph)
			tr.commit()

		# del all relationships from Clusters with no :HAS_CLUSTER (hits all in graph!)

		cluster_cursor = graph.run(
			'MATCH (c:Cluster)<-[x:IN_CLUSTER]-(:Sample) WHERE NOT ((c)<-[:HAS_CLUSTER]-(:Pair)) RETURN x')
		while cluster_cursor.forward():
			subgraph = cluster_cursor.current().subgraph()
			tr = graph.begin()
			tr.separate(subgraph)
			tr.commit()

		# del all lone Cluster nodes with no relationships (hits all in graph!)

		cluster_cursor = graph.run('MATCH (c:Cluster) WHERE NOT ((c)<-[]-()) RETURN c')
		while cluster_cursor.forward():
			subgraph = cluster_cursor.current().subgraph()
			tr = graph.begin()
			tr.delete(subgraph)
			tr.commit()

		# re-establish the new (Pair)->(Cluster)<-(Sample) relationships
		# print(df)
		clusters_found = []
		for index, row in df.iterrows():

			cluster_no = row['clusterID']
			cluster_node_name = (str(n['p']['name']) + '_' + str(cluster_no))
			sID = row.name

			# add cluster node

			if cluster_no not in clusters_found:
				clusters_found.append(cluster_no)
				cluster_rep_ID = reps_dict.get(cluster_no)
				for sublist in all_reps:
					if sublist[0] == cluster_no:
						cluster_rep_attributes = sublist[2:]

				c = Node('Cluster', cluster_no=cluster_no, cluster_node_name=cluster_node_name,
				         cluster_rep_ID=cluster_rep_ID, cluster_rep_attributes=cluster_rep_attributes)
				graph.merge(c, 'Cluster', 'cluster_node_name')
			else:
				c = graph.evaluate('MATCH (n:Cluster {cluster_node_name: $y}) RETURN n',
				                   parameters={"y": cluster_node_name})

			# create Sample node if it doesn't exist (incase manclus runs before autoclus)

			h = graph.evaluate('MATCH (n:Sample {sampleID: $t}) RETURN n', parameters={"t": sID})  # added for speed
			if h is None:
				outF.write('Sample node' + sID + "was not found so one was added. This shouldn't normally happen!\n")
				h = Node('Sample', sampleID=sID)
				graph.merge(h, 'Sample', 'sampleID')
				f = Relationship(h, 'HAS_ATTRIBUTE', n,
				                 attribute='unknown')  # the unknown attribute type will be stripped when autoclus recalculates
				graph.merge(f)

			# add (Pair)-[]->(Cluster) & (Cluster)<-[]-(Sample)
			q = Relationship(n, 'HAS_CLUSTER', c)
			e = Relationship(h, 'IN_CLUSTER', c)
			graph.merge(q)
			graph.merge(e)


# if __name__ == '__main__':
def run():

	# args
	parser = argparse.ArgumentParser(description='k-means clustering of samples belonging to Pair')
	parser.add_argument('--recalculate', '-r', action='store_true',
	                    help='recalculates and rewrites (Sample)-[IN_CLUSTER]->(Cluster) and (Pair)-[HAS_CLUSTER]->(Cluster)')
	parser.add_argument('--fly', '-f', action='store', nargs='?', default='None', const='None',
	                    help='pass Pair <id> as an argument to get a single result quickly on the fly')

	run_mode = parser.parse_args()
	recalculate_arg = run_mode.recalculate
	fly_arg = run_mode.fly

	# initialise database graph
	graph = Graph('http://localhost:7474/db/data', user='neo4j', password='neo5j')

	# writing output
	start_timestamp = get_timestamp()
	logname = str('log/' + start_timestamp + '_mancluster.log')
	with open(logname, 'w') as outF:
		outF.write('LOG FILE for mancluster.py\n\n' + 'Start time: ' + start_timestamp + '\n')

		if fly_arg != 'None':  # if the program is passed a pair directly via the fly arg process it instantly and return result
			pairID = int(fly_arg)
			n = graph.evaluate('MATCH (u:Pair) WHERE ID(u) = $p RETURN u', parameters={"p": pairID})
			# print(n['name'])
			if n['k'] is None:
				outF.write('CRITICAL: Engaged in --fly mode but given pairID does not have a manually entered k')
				print('CRITICAL: Engaged in --fly mode but given pairID does not have a manually entered k')
			else:
				clus2Neo(n)

		else:
			already_computed_count = 0
			newly_computed_count = 0
			missing_count = 0
			kpairs_total = graph.data('MATCH (p:Pair) WHERE NOT p.k = "None" RETURN count(*) AS total')  # just for tqdm
			kpairs_total_asNum = kpairs_total[0]['total']

			for n in tqdm(graph.run('MATCH (p:Pair) WHERE NOT p.k = "None" RETURN p ORDER BY p.confidence'),
			              total=kpairs_total_asNum, unit='pairs'):

				already_calculated = n[0]['mancluster_update_timestamp']

				if missing_count == 0:
					pairs_total = graph.data('MATCH (p:Pair) WHERE p.k = "None" RETURN count(*) AS total')
					pairs_total_asNum = pairs_total[0]['total']
					missing_count = pairs_total_asNum

				if recalculate_arg:  # argument passed at command line to recalculate all nodes
					newly_computed_count += 1
					pairID = remote(n[0])._id
					node_name = n[0]['name']
					k = n[0]['k']
					clus2Neo(n)
					print()
					print()
					print('NEWLY MANUALLY CLUSTERED')
					print('--------------------------------------------')
					print('Pair Name: ' + str(node_name))
					print('Pair ID:' + str(pairID))
					print('k: ' + str(k))
					print('--------------------------------------------')
					print()
					print('No. of missing pairs so far: ', missing_count)
					print('Pairs previously computed so far: ', already_computed_count)
					print('Pairs newly computed so far: ', newly_computed_count)
				elif already_calculated is None:
					newly_computed_count += 1
					pairID = remote(n[0])._id
					node_name = n[0]['name']
					k = n[0]['k']
					clus2Neo(n)
					print()
					print()
					print('NEWLY MANUALLY CLUSTERED')
					print('--------------------------------------------')
					print('Pair Name: ' + str(node_name))
					print('Pair ID:' + str(pairID))
					print('k: ' + str(k))
					print('--------------------------------------------')
					print()
					print('No. of missing pairs so far: ', missing_count)
					print('Pairs previously computed so far: ', already_computed_count)
					print('Pairs newly computed so far: ', newly_computed_count)
				else:
					pairID = remote(n[0])._id
					node_name = n[0]['name']
					k = n[0]['k']
					already_computed_count += 1

					print()
					print()
					print('PREVIOUSLY MANUALLY CLUSTERED')
					print('--------------------------------------------')
					print('Pair Name: ' + str(node_name))
					print('Pair ID:' + str(pairID))
					print('k: ' + str(k))
					print('--------------------------------------------')
					print()
					print('No. of missing pairs so far: ', missing_count)
					print('Pairs previously computed so far: ', already_computed_count)
					print('Pairs newly computed so far: ', newly_computed_count)
