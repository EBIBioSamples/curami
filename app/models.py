from py2neo import Graph, Node, Relationship, NodeSelector
from passlib.hash import bcrypt
from datetime import datetime
import pandas as pd
from flask import Flask, request, session, redirect, url_for, render_template, flash, abort
import os, time, difflib
import uuid


# url = os.environ.get('GRAPHENEDB_URL', 'http://localhost:7474')
# graph = Graph(url + '/db/data/', username=username, password=password)

graph = Graph('http://localhost:7474/db/data', user='neo4j', password='neo5j')
# username = os.environ.get('NEO4J_USERNAME')
# password = os.environ.get('NEO4J_PASSWORD')

# user profile functions

class User:
    def __init__(self, username):
        self.username = username
        
    def find(self):
        user = graph.find_one('User', 'username', self.username)
        return user

    def register(self, password, email, organisation):
        if not self.find():
            user = Node('User',
                username=self.username,
                password=bcrypt.encrypt(password),
                email=email,
                organisation=organisation,
                sort_type='smart',
                vioscreen_stop='No',
                specialism_attributes=False)
            graph.create(user)
            return True
        else:
            return False

    def verify_password(self, password):
        user = self.find()
        if user:
            return bcrypt.verify(password, user['password'])
        else:
            return False

def timestamp():
    epoch = datetime.utcfromtimestamp(0)
    now = datetime.now()
    delta = now - epoch
    return delta.total_seconds()

def date():
    return datetime.now().strftime('%Y-%m-%d')

# get DB info functions

def get_pairs():
    query = '''
    MATCH (n:Pair) RETURN COUNT(n)
    '''
    return graph.run(query).evaluate()

def get_samples():
    query = '''
    MATCH (n:Sample) RETURN COUNT(n)
    '''
    return graph.run(query).evaluate()

def get_last_coexistance_update():
    query = '''
    MATCH (n) WHERE EXISTS(n.coexistance_update_timestamp)
    RETURN n.coexistance_update_timestamp
    ORDER BY n.coexistance_update_timestamp DESC
    LIMIT 1
    '''
    result = graph.run(query).evaluate()
    date_ = result.split("_")[0].split("-")
    time_ = result.split("_")[1].split("-")
    date = str(date_[2] + '.' + date_[1] + '.' + date_[0])
    time = str(time_[0] + '.' + time_[1])
    return (date, time)

def get_last_autocluster_update():
    query = '''
    MATCH (n) WHERE EXISTS(n.autocluster_update_timestamp)
    RETURN n.autocluster_update_timestamp
    ORDER BY n.autocluster_update_timestamp DESC
    LIMIT 1
    '''
    result = graph.run(query).evaluate()
    date_ = result.split("_")[0].split("-")
    time_ = result.split("_")[1].split("-")
    date = str(date_[2] + '.' + date_[1] + '.' + date_[0])
    time = str(time_[0] + '.' + time_[1])
    return (date, time)

def get_last_lexical_update():
    query = '''
    MATCH (n) WHERE EXISTS(n.lexical_update_timestamp)
    RETURN n.lexical_update_timestamp
    ORDER BY n.lexical_update_timestamp DESC
    LIMIT 1
    '''
    result = graph.run(query).evaluate()
    date_ = result.split("_")[0].split("-")
    time_ = result.split("_")[1].split("-")
    date = str(date_[2] + '.' + date_[1] + '.' + date_[0])
    time = str(time_[0] + '.' + time_[1])
    return (date, time)

def get_last_values_update():
    query = '''
    MATCH (n) WHERE EXISTS(n.values_update_timestamp)
    RETURN n.values_update_timestamp
    ORDER BY n.values_update_timestamp DESC
    LIMIT 1
    '''
    result = graph.run(query).evaluate()
    date_ = result.split("_")[0].split("-")
    time_ = result.split("_")[1].split("-")
    date = str(date_[2] + '.' + date_[1] + '.' + date_[0])
    time = str(time_[0] + '.' + time_[1])
    return (date, time)

def get_num_samples_processed():
    lexical = '''
    MATCH (n)
    WHERE EXISTS(n.lexical_update_timestamp) 
    RETURN count(n)
    '''
    autocluster = '''
    MATCH (n)
    WHERE EXISTS(n.autocluster_update_timestamp) 
    RETURN count(n)
    '''
    values = '''
    MATCH (n)
    WHERE EXISTS(n.values_update_timestamp) 
    RETURN count(n)
    '''
    coexistance = '''
    MATCH (n)
    WHERE EXISTS(n.coexistance_update_timestamp) 
    RETURN count(n)
    '''

    lexical_num_processed = graph.run(lexical).evaluate()
    autocluster_num_processed = graph.run(autocluster).evaluate()
    values_num_processed = graph.run(values).evaluate()
    coexistance_num_processed = graph.run(coexistance).evaluate()

    return (lexical_num_processed, autocluster_num_processed, values_num_processed, coexistance_num_processed)

def get_all_record_info(pair_id):

    node = get_pair_node(pair_id)

    pair_info = {}
    pair_info.update({

        # timestamps
        'autocluster_update_timestamp' : node['autocluster_update_timestamp'],
        'coexistance_update_timestamp' : node['coexistance_update_timestamp'],
        'lexical_update_timestamp' : node['lexical_update_timestamp'],
        'values_update_timestamp' : node['values_update_timestamp'],

        # main stuff
        'name' : node['name'],
        'good_attribute' : node['good_attribute'],
        'bad_attribute' : node['bad_attribute'],
        'levenshtein' : node['levenshtein'],
        'bad_facet_freq' : node['bad_facet_freq'],
        'good_facet_freq' : node['good_facet_freq'],

        # coexistance stuff
        'degree1' : node['degree1'],
        'degree2' : node['degree2'],
        'jaccard_coefficient' : node['jaccard_coefficient'],
        'break_no' : node['break_no'],
        'edge_total' : node['edge_total'],
        'edge_weight' : node['edge_weight'],

        # values

        'type_match' : node['type_match'],
        'magnitude_difference' : node['magnitude_difference'],
        'exact_score' : node['exact_score'],
        'jaro_score' : node['jaro_score'],

        'top_value1' : node['top_value1'],
        'top_value2' : node['top_value2'],

        'type_date_f1' : node['type_date_f1'],
        'type_int_f1' : node['type_int_f1'],
        'type_str_f1' : node['type_str_f1'],

        'str_ratio1' : node['str_ratio1'],
        'date_ratio1' : node['date_ratio1'],
        'int_ratio1' : node['int_ratio1'],

        'type_date_f2' : node['type_date_f2'],
        'type_int_f2' : node['type_int_f2'],
        'type_str_f2' : node['type_str_f2'],

        'str_ratio2' : node['str_ratio2'],
        'date_ratio2' : node['date_ratio2'],
        'int_ratio2' : node['int_ratio2'],

        })

    return pair_info

def get_pair_node(pair_id): # returns a node

    one_fetch = '''
                MATCH (p:Pair)
                WHERE ID(p) = {pair_id}
                RETURN p
                '''
    return graph.run(one_fetch, pair_id=pair_id).evaluate()

def get_lexical_info(pair_id):

    node = get_pair_node(pair_id)

    lexical_info = {}
    lexical_info.update({

        # combinations of these issues can be detected (cumulative)

        'number_discrepancy' : node['number_discrepancy'],
        'case_discrepancy' : node['case_discrepancy'],
        'space_discrepancy' : node['space_discrepancy'],
        'specials_discrepancy' : node['specials_discrepancy'],
        'wordNo_discrepancy' : node['wordNo_discrepancy'],
        'stopWord_discrepancy' : node['stopWord_discrepancy'],
        'spell_discrepancy' : node['spell_discrepancy'],
        'lemma_discrepancy' : node['lemma_discrepancy'],
        'stem_discrepancy' : node['stem_discrepancy'],

        # these detect if the only problem is x and are non-cumulative
        'onlySpace_discrepancy' : node['onlySpace_discrepancy'],
        'just_specials_discrepancy' : node['just_specials_discrepancy'],
        's_discrepancy' : node['s_discrepancy'],
        'sLower_discrepancy' : node['sLower_discrepancy'],

        # other
        'bad_words' : node['bad_words'],
        'possible_camelCase' : node['possible_camelCase']

                })


    if lexical_info.get('onlySpace_discrepancy'):
        lexical_issues = 'Space discrepancy detected'
    elif lexical_info.get('just_specials_discrepancy'):
        lexical_issues = 'Special character discrepancy detected'
    elif lexical_info.get('s_discrepancy'):
        lexical_issues = 'Pluralisation discrepancy detected'
    elif lexical_info.get('sLower_discrepancy'):
        lexical_issues = 'Pluralisation and case discrepancy detected'
    else:
        issues = []
        if lexical_info.get('number_discrepancy'):
            issues.append('numeric')
        if lexical_info.get('case_discrepancy'):
            issues.append('case')
        if lexical_info.get('space_discrepancy'):
            issues.append('space')
        if lexical_info.get('specials_discrepancy'):
            issues.append('special characters')
        if lexical_info.get('stopWord_discrepancy'):
            issues.append('stop word')
        if lexical_info.get('spell_discrepancy'):
            issues.append('spelling')
        if lexical_info.get('lemma_discrepancy'):
            issues.append('lemma')
        if lexical_info.get('stem_discrepancy'):
            issues.append('stem')

        if len(issues) == 0:
            lexical_issues = 'No lexical issues have been detected'
        elif len(issues) == 1:
            lexical_issues = str(issues[0] + 'discrepancy detected')
        elif len(issues) > 1:
            issues_ = str(", ".join(issues[:-1]))
            issues__ = str(", ".join(issues[-1:]))
            lexical_issues = str(str(issues_) + ' and ' + issues__ + ' discrepancies detected')
        else:
            print('code fell through cracks')

    bad_words_ = lexical_info.get('bad_words')
    if bad_words_ is None:
        bad_words_ = str()
    bad_words = str(", ".join(bad_words_))
    possible_camelCase = str(lexical_info.get('possible_camelCase'))
    

    return (lexical_issues, bad_words, possible_camelCase)

def get_last_decision(username, pairID):

    query = '''
    MATCH (n:User)-[r]-(p:Pair)
    WHERE n.username = {username} AND ID(p) = {pairID}
    RETURN r
    ORDER BY r.timestamp DESC
    '''

    result = graph.run(query, username=username, pairID=pairID).evaluate()
    if result:
        decision_type = graph.run(query, username=username, pairID=pairID).evaluate().type()
    else:
        decision_type = False
        last_decision = None

    if decision_type == 'SKIPPED':
        last_decision = 'Skip'
    elif decision_type == 'SUGGESTED_MERGE':
        last_decision = 'Merge'
    elif decision_type == 'SUGGESTED_NOMERGE':
        last_decision = "Don't merge"
    elif decision_type == 'SUGGESTED_REVERSEMERGE':
        last_decision = 'Merge reverse'

    return last_decision

def profile_stats(username_tag):

    all_pairs_curated_ = '''
    MATCH (n:User)-[r:SUGGESTED_MERGE|SUGGESTED_NOMERGE|SUGGESTED_REVERSEMERGE]-(p:Pair)
    WHERE n.username = {username_tag}
    RETURN count(r)
    '''
    SUGGESTED_MERGE_decisions_ = '''
    MATCH (n:User)-[r:SUGGESTED_MERGE]-(p:Pair)
    WHERE n.username = {username_tag}
    RETURN count(r)
    '''
    SUGGESTED_NOMERGE_decisions_ = '''
    MATCH (n:User)-[r:SUGGESTED_NOMERGE]-(p:Pair)
    WHERE n.username = {username_tag}
    RETURN count(r)
    '''
    SUGGESTED_REVERSEMERGE_decisions_ = '''
    MATCH (n:User)-[r:SUGGESTED_REVERSEMERGE]-(p:Pair)
    WHERE n.username = {username_tag}
    RETURN count(r)
    '''

    all_pairs_curated = graph.run(all_pairs_curated_, username_tag=username_tag).evaluate()
    SUGGESTED_MERGE_decisions = graph.run(SUGGESTED_MERGE_decisions_, username_tag=username_tag).evaluate()
    SUGGESTED_NOMERGE_decisions = graph.run(SUGGESTED_NOMERGE_decisions_, username_tag=username_tag).evaluate()
    SUGGESTED_REVERSEMERGE_decisions = graph.run(SUGGESTED_REVERSEMERGE_decisions_, username_tag=username_tag).evaluate()

    return(all_pairs_curated, SUGGESTED_MERGE_decisions, SUGGESTED_NOMERGE_decisions, SUGGESTED_REVERSEMERGE_decisions)

# fetch nodes and next nodes

def fetch_initial_pair_nodes(sort_type, vioscreen_stop, specialism_attributes):

    # this module is to fetch the initial cursor only doesnt require pair_id starting point

    # mode advanced could ensure the user hasn't already curated them
    # secondary order_by no. of samples affected

    if sort_type in ['smart', 'max', 'major']: # if non specialism sort
        cursor = cypher_200(sort_type, vioscreen_stop)
    elif sort_type in ['my_attributes', 'related_to_my_attributes', 'dynamic_specialism']:
        cursor = main_sorter(sort_type, specialism_attributes)

    # print('## cursor from cypher_200: {}'.format(cursor.evaluate()))

    while cursor.forward():
        record = cursor.current()
        name = record['p']['name']
        pair_id = record['id(p)']
        return (name, pair_id) # with this indent it is only getting one for testing!!!!

def cypher_200(sort_type, vioscreen_stop): # uses sort type to return a list of attributes

    if sort_type == 'smart':
        if vioscreen_stop == 'Yes':
            fetch = '''
            MATCH (p:Pair)
            WHERE NOT (p:Pair)-[:SUGGESTED_MERGE|SUGGESTED_NOMERGE|SUGGESTED_REVERSEMERGE|SKIPPED]-()
            AND NOT p.good_attribute =~ 'vioscreen.*' AND NOT p.bad_attribute =~ 'vioscreen.*'
            RETURN p, id(p) ORDER BY p.pseudo_confidence DESC, p.name
            LIMIT 200
            '''
            return graph.run(fetch)

        else:
            fetch = '''
            MATCH (p:Pair)
            WHERE NOT (p:Pair)-[:SUGGESTED_MERGE|SUGGESTED_NOMERGE|SUGGESTED_REVERSEMERGE|SKIPPED]-()
            RETURN p, id(p) ORDER BY p.pseudo_confidence DESC, p.name
            LIMIT 200
            '''
            return graph.run(fetch)

    elif sort_type == 'max': # sorting in descending order by the facet with the least usage in the db
        if vioscreen_stop == 'Yes':
            fetch = '''
            MATCH (p:Pair)
            WHERE NOT (p:Pair)-[:SUGGESTED_MERGE|SUGGESTED_NOMERGE|SUGGESTED_REVERSEMERGE|SKIPPED]-()
            AND NOT p.good_attribute =~ 'vioscreen.*' AND NOT p.bad_attribute =~ 'vioscreen.*'
            WITH toInteger(p.bad_facet_freq) as BAD, toInteger(p.good_facet_freq) AS GOOD, p
            RETURN p, id(p),
            CASE
                WHEN BAD <= GOOD THEN BAD
                ELSE GOOD
            END
            AS m
            ORDER BY m DESC
            LIMIT 200
            '''
        else:
            fetch = '''
            MATCH (p:Pair)
            WHERE NOT (p:Pair)-[:SUGGESTED_MERGE|SUGGESTED_NOMERGE|SUGGESTED_REVERSEMERGE|SKIPPED]-()
            WITH toInteger(p.bad_facet_freq) as BAD, toInteger(p.good_facet_freq) AS GOOD, p
            RETURN p, id(p),
            CASE
                WHEN BAD <= GOOD THEN BAD
                ELSE GOOD
            END
            AS m
            ORDER BY m DESC
            LIMIT 200
            '''
    elif sort_type == 'major': # sorting in descending order by major attribute (highest sample usage)
        if vioscreen_stop == 'Yes':
            fetch = '''
            MATCH (p:Pair)
            WHERE NOT (p:Pair)-[:SUGGESTED_MERGE|SUGGESTED_NOMERGE|SUGGESTED_REVERSEMERGE|SKIPPED]-()
            AND NOT p.good_attribute =~ 'vioscreen.*' AND NOT p.bad_attribute =~ 'vioscreen.*'
            WITH toInteger(p.bad_facet_freq) as BAD, toInteger(p.good_facet_freq) AS GOOD, p
            RETURN p, id(p),
            CASE
                WHEN BAD >= GOOD THEN BAD
                ELSE GOOD
            END
            AS m
            ORDER BY m DESC
            LIMIT 200
            '''
        else:
            fetch = '''
            MATCH (p:Pair)
            WHERE NOT (p:Pair)-[:SUGGESTED_MERGE|SUGGESTED_NOMERGE|SUGGESTED_REVERSEMERGE|SKIPPED]-()
            WITH toInteger(p.bad_facet_freq) as BAD, toInteger(p.good_facet_freq) AS GOOD, p
            RETURN p, id(p),
            CASE
                WHEN BAD >= GOOD THEN BAD
                ELSE GOOD
            END
            AS m
            ORDER BY m DESC
            LIMIT 200
            '''
    else:
        print('Critical: unexpected sort_type')

    print('## cypher_200\nfetch: {}\nvioscreen_stop: {}\nsort_type {}'.format(fetch, vioscreen_stop, sort_type))

    return graph.run(fetch)

def get_next_pair_record(pair_id, sort_type, vioscreen_stop, specialism_attributes):

    if sort_type in ['smart', 'max', 'major']: # if non specialism sort
        cursor = cypher_200(sort_type, vioscreen_stop)
    elif sort_type in ['my_attributes', 'related_to_my_attributes', 'dynamic_specialism']:
        cursor = main_sorter(sort_type, specialism_attributes)

    node = get_pair_node(pair_id) # checks that the node exists
    if node is None:
        return 'Node not in database'
    else:
        current_pair_id = pair_id

        while cursor.forward(): 
            record = cursor.current()
            next_pair_id = record['id(p)']
            if current_pair_id == next_pair_id:
                record = cursor.next()
                next_pair_id = record['id(p)']

            return (current_pair_id, next_pair_id)

def make_relationship(username, merge_node_id, rel_type, next_pair_id):

    # rel_type should be SUGGESTED_MERGE or SUGGESTED_REVERSEMERGE or SUGGESTED_NOMERGE

    selector = NodeSelector(graph)
    selection = selector.select("User", username = username)
    user_node = selection.first()
    merge_node = graph.node(merge_node_id)

    # TODO here the merge_node could be a Pair node or a Cluster node!

    timestamp = time.time()
    graph.merge(Relationship(user_node, rel_type, merge_node, timestamp=timestamp))
    return redirect(url_for('attribute_curation_pair', pair_id=next_pair_id, username=username))

# settings functions

def current_settings(username):
    print('username is: {}'.format(username))
    selector = NodeSelector(graph)
    selection = selector.select("User", username = username)
    user_node = selection.first()
    return (user_node['sort_type'], user_node['vioscreen_stop'], user_node['specialism_attributes'])

def change_sort_type(username, input_sort_type):
    # this is to save the sort_type setting on the user node if it changes

    selector = NodeSelector(graph)
    selection = selector.select("User", username = username)
    user_node = selection.first()
    user_node['sort_type'] = input_sort_type
    graph.push(user_node)

def change_vioscreen_stop(username, input_vioscreen_stop):
    # this is to save the sort_type setting on the user node if it changes
    # print('input_vioscreen_stop is: {}'.format(input_vioscreen_stop))
    selector = NodeSelector(graph)
    # print('selector is: {}'.format(selector))
    selection = selector.select("User", username = username)
    # print('selection is: {}'.format(selection))
    user_node = selection.first()
    # print('user_node is: {}'.format(user_node))
    user_node['vioscreen_stop'] = input_vioscreen_stop
    # print('user_node is: {}'.format(user_node))
    graph.push(user_node)

def change_specialist_attributes(username, edits):

    # if list passed directly then go for it, if edit dict passed parse first

    if type(edits) is list:
        edits = list(set(edits)) # drop duplicates
        user_attributes = edits

    elif type(edits) is dict:
        # parsing edit dict to list
        edits.pop('resub') # form submission as python dict

        # list from dict after strip False, keep True, swap suggestions
        user_attributes = []
        for key, value in edits.items():
            if value == 'False':
                continue
            elif value == 'True':
                user_attributes.append(key)
            else:
                user_attributes.append(value)
        user_attributes = list(set(user_attributes)) # drop duplicates

    print('User Attributes sent to Neo4J: {}'.format(user_attributes))

    selector = NodeSelector(graph)
    selection = selector.select("User", username = username)
    user_node = selection.first()
    user_node['specialism_attributes'] = user_attributes
    graph.push(user_node)

def user_data_wipe(username): # unused at the moment

    cypher = '''
    MATCH (P:User)-[r]-()
        WHERE P.username = {username}
        DETACH DELETE r
    '''
    graph.run(cypher, username=username)

# Reccomendation functions

def reccomend(provided_attributes):

    # takes a comma separated string or a list

    if type(provided_attributes) == str:
        provided_attributes = provided_attributes.split(",")


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
    reccomended_ = pd.DataFrame(graph.run(reccomend_5, provided_attributes=provided_attributes).data())
    reccomended_.columns = ['attribute', 'totalWeight']
    reccomended = list(reccomended_['attribute'])

    return reccomended # a list of len 5 with the reccomended attributes closest match in pos 0

def all_attributes(): # This function takes a list of attributes and checks if they exist in the dataset

        get_all = '''
        MATCH (a:Attribute)
        RETURN a.attribute
        '''

        df = pd.DataFrame(graph.run(get_all).data())
        attribute_list = set(df['a.attribute'])
        return attribute_list

def DYM(provided_attributes): # the 'did you mean' function

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

def reccomend_500(provided_attributes): # returns ordered list 500 closest to user provided provided_attributes

    fetch_reccomend_500 = '''
    MATCH (a:Attribute)
    WHERE (a.attribute IN {provided_attributes})
    WITH collect(a) as subset
    UNWIND subset as a
    MATCH (a)-[r:COOCCURS_WITH]-(b)
    WHERE NOT b in subset
    RETURN b.attribute, sum(r.weight) as totalWeight
    ORDER BY totalWeight DESC LIMIT 500
    '''
    reccomended = pd.DataFrame(graph.run(fetch_reccomend_500, provided_attributes=provided_attributes).data())
    print('reccomended shape is: {}'.format(reccomended.shape))
    reccomended.columns = ['attribute', 'totalWeight']
    # print('type of reccomended is: {}'.format(type(reccomended)))
    print('reccomended is:\n {}'.format(reccomended))
    next500attributes = list(reccomended['attribute'])

    # print('next500attributes is: {}'.format(next500attributes))

    if len(next500attributes) == 0:
        flash('Critical Error: no near attributes found')
        print('Critical Error: no near attributes found')
        return

    return next500attributes

def my_pairs_count(provided_attributes): # how many unexamined pairs exist that contian the users specialist attributes

    pairs_left = 0

    print('provided_attributes in my_pairs_count: {}'.format(provided_attributes))

    for my_attribute in provided_attributes:

        counter = '''
            MATCH (p:Pair)
            WHERE NOT (p:Pair)-[:SUGGESTED_MERGE|SUGGESTED_NOMERGE|SUGGESTED_REVERSEMERGE|SKIPPED]-()
            AND p.good_attribute = {my_attribute}
            OR p.bad_attribute = {my_attribute}
            RETURN count(p)
            '''
        result = graph.run(counter, my_attribute=my_attribute).data()
        count = result[0].get('count(p)')
        pairs_left += count

    return pairs_left

def my_attributes_sort(provided_attributes): # a sorting function allows users to curate the pairs that directly relate to their samples
    
    print('provided_attributes in my_attributes_sort: {}'.format(provided_attributes))
    pairs_left = my_pairs_count(provided_attributes)
    provided_attributes = list(provided_attributes)

    if pairs_left != 0:
        fetch = '''
            MATCH (p:Pair)
            WHERE NOT (p:Pair)-[:SUGGESTED_MERGE|SUGGESTED_NOMERGE|SUGGESTED_REVERSEMERGE|SKIPPED]-()
            AND p.good_attribute IN {provided_attributes}
            AND p.good_attribute IN {provided_attributes}
            RETURN p, id(p) ORDER BY p.pseudo_confidence DESC, p.name
            LIMIT 200

        '''
        return graph.run(fetch, provided_attributes=provided_attributes)
    else:
        return None

def related_to_my_attributes_sort(provided_attributes): # chunking  through nearest 5 attributes at a time returns pair nodes or skips to next chunk

    nearest_500 = reccomend_500(provided_attributes)
    chunk_size = 5
    chunk_list = [nearest_500[x:x+chunk_size] for x in range(0, len(nearest_500), chunk_size)]

    for chunk in chunk_list:
        result = my_attributes_sort(chunk)
        if result != None:
            return my_attributes_sort(chunk)
        else:
            continue

def previous_attributes(username_tag, good_attribute=False): # get 'bad' attributes by default a user has already merged
    # note similar to function profile_stats

    def go_get_previous_attributes(SUGGESTED_MERGE_decisions_, SUGGESTED_REVERSEMERGE_decisions_):
        SUGGESTED_MERGE_decisions_df = pd.DataFrame(graph.run(SUGGESTED_MERGE_decisions_, username_tag=username_tag).data())
        print('SUGGESTED_MERGE_decisions_df:\n {}'.format(SUGGESTED_MERGE_decisions_df))
        if SUGGESTED_MERGE_decisions_df.empty:
            SUGGESTED_MERGE_decisions = []
        else:
            SUGGESTED_MERGE_decisions_df.columns = ['attribute']
            SUGGESTED_MERGE_decisions = list(SUGGESTED_MERGE_decisions_df['attribute'])

        SUGGESTED_REVERSEMERGE_decisions_df = pd.DataFrame(graph.run(SUGGESTED_REVERSEMERGE_decisions_, username_tag=username_tag).data())
        print('SUGGESTED_REVERSEMERGE_decisions_df:\n {}'.format(SUGGESTED_REVERSEMERGE_decisions_df))
        if SUGGESTED_REVERSEMERGE_decisions_df.empty:
            SUGGESTED_REVERSEMERGE_decisions = []
        else:
            SUGGESTED_REVERSEMERGE_decisions_df.columns = ['attribute']
            SUGGESTED_REVERSEMERGE_decisions = list(SUGGESTED_REVERSEMERGE_decisions_df['attribute'])

        return SUGGESTED_MERGE_decisions + SUGGESTED_REVERSEMERGE_decisions


    if good_attribute == False: # will return bad attributes
        SUGGESTED_MERGE_decisions_ = '''
        MATCH (n:User)-[r:SUGGESTED_MERGE]-(p:Pair)
        WHERE n.username = {username_tag}
        RETURN p.bad_attribute
        '''
        SUGGESTED_REVERSEMERGE_decisions_ = '''
        MATCH (n:User)-[r:SUGGESTED_REVERSEMERGE]-(p:Pair)
        WHERE n.username = {username_tag}
        RETURN p.good_attribute
        '''

    elif good_attribute == True: # will return good attrubutes
        SUGGESTED_MERGE_decisions_ = '''
        MATCH (n:User)-[r:SUGGESTED_MERGE]-(p:Pair)
        WHERE n.username = {username_tag}
        RETURN p.good_attribute
        '''
        SUGGESTED_REVERSEMERGE_decisions_ = '''
        MATCH (n:User)-[r:SUGGESTED_REVERSEMERGE]-(p:Pair)
        WHERE n.username = {username_tag}
        RETURN p.bad_attribute
        '''


    return go_get_previous_attributes(SUGGESTED_MERGE_decisions_, SUGGESTED_REVERSEMERGE_decisions_)

def dynamic_specialism_sort(provided_attributes, username):

    # built like this incase the need for flexibility arrises in the future
    previous_bad = previous_attributes(username, False)
    previous_good = previous_attributes(username, True)
    previous_all = set(previous_good + previous_bad + provided_attributes)
    return my_attributes_sort(previous_all)

def main_sorter(sort_type, provided_attributes): # uses sort type to return a list of attributes
    
    print('provided_attributes in main_sorter: {}'.format(provided_attributes))
    
    username = session.get('username')
    change_vioscreen_stop(username, "No") # vioscreen_stop setting is switched off for this function even if it is on.

    if sort_type == 'my_attributes': 
        return my_attributes_sort(provided_attributes)

    if sort_type == 'related_to_my_attributes':
        return related_to_my_attributes_sort(provided_attributes)

    if sort_type == 'dynamic_specialism': # previous bad and good attributes are added to the query for the reccomendation will likely need tweaking
        return dynamic_specialism_sort(provided_attributes, username)








