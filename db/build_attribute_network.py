'''
creates attribute nodes in the Neo4J db tand relationships if the attributes coocur
This part of the db is used by the reccomendation engine
'''

import pandas as pd
from py2neo import Node, Graph, NodeSelector, Relationship
import sys, difflib


def fill_attribute_graph(graph):
    # graph.delete_all()
    attribute_df = pd.read_csv('data/attributes.csv', usecols=['attribute', 'frequency'])
    coexistence_df = pd.read_csv('data/coexistencesProb.csv', usecols=['attribute1','attribute2','totals','exp','diff','weight'])
    freq_lookup_dict = dict(zip(attribute_df.attribute.values, attribute_df.frequency.values))

    # create nodes
    for attribute, frequency in freq_lookup_dict.items():
        x = Node('Attribute', attribute=str(attribute), frequency=str(frequency))  # create cypher object
        graph.merge(x, 'Attribute', 'attribute')  # merge is important to prevent duplicates

    # create relationships
    for index, row in coexistence_df.iterrows():
        rel_type = 'COOCCURS_WITH'
        try:
            selector = NodeSelector(graph)
            attrubute1_node = selector.select("Attribute", attribute=row.attribute1).first()
            attrubute2_node = selector.select("Attribute", attribute=row.attribute2).first()
            if (attrubute1_node != None
            and attrubute2_node != None
            and row.totals != None
            and row.weight != None):
                graph.merge(Relationship(attrubute1_node, rel_type, attrubute2_node, coexistance=row.totals, weight=row.weight))
        except AttributeError:
            print(index)
            print(row)


if __name__ == "__main__":

    graph = Graph('http://localhost:7474/db/data', user='neo4j', password='neo5j')  # initialising graph

    fill_attribute_graph(graph)

























