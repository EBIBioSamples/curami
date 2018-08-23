from py2neo import Node, Graph, NodeSelector, Relationship
import sys, csv
import pandas as pd
from biosamples.client import Client
from biosamples.Models import Curation
from biosamples.aap_client import AAP_Client
from biosamples.utilities import is_ok, is_successful, is_status
import json

'''
for a given user pull in their forward merges
pull in reverse merges and then reverse and add together
create a class for pre curation object
Just need pre and post attribute (also need a jwt from Luca's code)
find luca's code for making this into the right format for a curation object
find out how to POST to biosamples (see Luca's code)




'''
def decision_get(curami_username_tag):

    '''
    Gets the reverse and forward merge decisions and does the appropreate switch
    to return a df that has the correct good and bad
    '''

    def rel_get(curami_username_tag, merge_type):
        get_all = '''
        MATCH (u:User)-[m]-(p:Pair)
        WHERE u.username = {curami_username_tag} AND type(m) = {merge_type}
        RETURN p.good_attribute, p.bad_attribute
        '''
        return pd.DataFrame(graph.data(get_all, curami_username_tag=curami_username_tag, merge_type=merge_type))


    merge_df = rel_get(curami_username_tag, "SUGGESTED_MERGE")
    revmerge_df = rel_get(curami_username_tag, "SUGGESTED_REVERSEMERGE")
    revmerge_df.columns = ["p.good_attribute", "p.bad_attribute"] #switch the column names for the reverse merge table
    concat_df = merge_df.append(revmerge_df, ignore_index=True)
    return concat_df

def get_related_BioSD_ids(bad_attribute):
    with open('../db/data/samples.csv', 'r') as csvfile:
        reader = csv.reader(csvfile)
        sampleIDs = set()
        for row in reader:
            for field in row:
                if field == bad_attribute:
                    sampleIDs.add(row[0])
    return sampleIDs


def get_curation_object(sample, pre_type, post_type, domain):

    attr_value = sample['characteristics'][pre_type][0]['text']

    attr_pre_list = list()
    attr_pre = dict()
    attr_pre['type'] = pre_type
    attr_pre['value'] = attr_value
    attr_pre_list.append(attr_pre)

    attr_post_list = list()
    attr_post = dict()
    attr_post['type'] = post_type
    attr_post['value'] = attr_value
    attr_post_list.append(attr_post)

    return Curation(attributes_pre=attr_pre_list, attributes_post=attr_post_list, domain=domain)


def make_n_post_curation(
                client,
                accession,
                attributes_pre, 
                attributes_post,
                domain,
                jwt
                ):
    

    resp = client.fetch_sample(accession)
    if is_ok(resp):
        print("Got sample from the client")
        # print(json.dumps(resp.json(), ))
        sample = resp.json()
        curation = get_curation_object(sample=sample, pre_type=attributes_pre, post_type=attributes_post, domain=domain)
        resp = client.curate_sample(sample=sample, curation_object=curation, jwt=jwt)
        if not is_successful(resp):
            print("Something went wrong while curating {}".format(sample['accession']))
            print(resp.status_code)
            return
        print("I've curated sample {}".format(sample['accession']))


if __name__ == "__main__":

    graph = Graph('http://localhost:7474/db/data', user='neo4j', password='neo5j')  # initialising graph

    curami_username_tag = "hewgreen"
    aap_username = "hewgreen"
    aap_password = "YwpH-SSB2"
    aap_baseurl = 'https://explore.api.aap.tsi.ebi.ac.uk/auth'
    baseurl = "https://wwwdev.ebi.ac.uk/biosamples"
    domain = "self.Curami"

    aap_client = AAP_Client(username=aap_username, password=aap_password, url=aap_baseurl)
    biosd_client = Client(baseurl=baseurl)
    jwt = aap_client.get_token()


    df = decision_get(curami_username_tag)

    for row in df.iterrows():
        attributes_post = row[1]['p.good_attribute']
        attributes_pre = row[1]['p.bad_attribute']
        related_BioSD_ids = get_related_BioSD_ids(attributes_pre) # a set with bioSD ids that have the bad attribute in them

        for accession in related_BioSD_ids:
            make_n_post_curation(
                client=biosd_client,
                accession=accession,
                attributes_pre=attributes_pre, 
                attributes_post=attributes_post,
                domain=domain,
                jwt=jwt
                )

            print('sample: {}'.format(accession))
            print('bad_attribute aka post: {}'.format(attributes_post))
            print('good_attribute aka pre: {}'.format(attributes_pre))
            sys.exit()








# aiming for def curate_sample(self, sample, curation_object, jwt=None):








