'''
N.B. this requires that you have ran the build_attribute_network.py in the backend so that
the attribute nodes are created in the graph.

1. if check_exist flag is true, checks that the provided attributes (actually exist).
If they don't you can see which ones are lexically similar or I could auto add these or jsut flag they are being ignored/ a did you mean?
This is separated out because it is slightly heavier to look at the attributes but this is only 30,000 string list so not too bad performance
2. once you have a group of attributes that actually exist you can use the function to get suggestions.
3. the app can then use these suggestions to allow the user to curate in their domain of interest


input needed from app: provided_attributes_str = 'longitude, lngtude'

'''

import pandas as pd
from py2neo import Node, Graph, NodeSelector, Relationship
import sys, difflib, os

graph = Graph('http://localhost:7474/db/data', user='neo4j', password='neo5j')
username = os.environ.get('NEO4J_USERNAME')
password = os.environ.get('NEO4J_PASSWORD')


'''
This function takes a list of attributes and checks if they exist in the dataset
'''
def all_attributes():

        get_all = '''
        MATCH (a:Attribute)
        RETURN a.attribute
        '''

        df = pd.DataFrame(graph.run(get_all).data())
        attribute_list = set(df['a.attribute'])
        return attribute_list

def DYM(provided_attributes):

    attribute_set = all_attributes()


    DYM_suggestions = dict()

    for query_attribute in provided_attributes:
        if query_attribute not in attribute_set:
            DYM_suggestion = difflib.get_close_matches(query_attribute, attribute_set) # DYM_suggestion is a list with multiple close matches
            if len(DYM_suggestion) == 0: # if no close matches are found
                DYM_suggestion = False
            elif len(DYM_suggestion) > 3:
                DYM_suggestion = DYM_suggestion[0:3]
        else:
            DYM_suggestion = True # if the provided attribute is in the dataset (so no suggestions needed)
        DYM_suggestions[query_attribute] = DYM_suggestion

    return DYM_suggestions


def reccomend_5(provided_attributes): # returns the nearest 5 attributes to the list of provided attributes

        reccomend_5 = '''
        MATCH (a:Attribute)
        WHERE (a.attribute IN {provided_attributes})
        WITH collect(a) as subset
        UNWIND subset as a
        MATCH (a)-[r:COOCCURS_WITH]-(b)
        WHERE NOT b in subset
        RETURN b.attribute, sum(r.weight) as totalWeight
        ORDER BY totalWeight DESC LIMIT 5
        '''
        reccomended_df = pd.DataFrame(graph.run(reccomend_5, provided_attributes=provided_attributes).data())
        reccomended = list(reccomended_df['b.attribute'])

        return reccomended














