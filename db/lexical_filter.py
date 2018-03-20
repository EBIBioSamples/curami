'''
Lexical Filter

Takes all attributes and does fuzzy matching in an all by all pairwise fasion intital filter cut off is 80% match


'''
import re, csv, sys, datetime, collections, ast, argparse, jellyfish, enchant, multiprocessing
from py2neo import Node, Relationship, Graph, Path, authenticate, NodeSelector
from nltk.tokenize import wordpunct_tokenize
from nltk.stem import WordNetLemmatizer
# from nltk.tokenize import word_tokenize
from enchant.checker import SpellChecker
from nltk.corpus import stopwords
from enchant import DictWithPWL
from fuzzywuzzy import process
from nltk.stem.porter import PorterStemmer
from fuzzywuzzy import fuzz
from tqdm import tqdm
import pandas as pd
import numpy as np


def multithread_fuzz(facet1):

	temp_calc = []
	temp_a2 = []
	temp_a1 = []
	
	for facet2 in all_pairs:
		if facet1 != facet2:

			# jaro_winkler = jellyfish.jaro_winkler(str(facet1), str(facet2))
			# if jaro_winkler > 0.8:
			# 	results_df = results_df.append(pd.DataFrame({'attribute1': facet1,'attribute2': facet2, 'jaro_winkler': jaro_winkler}, index=[0]), ignore_index=True)

			# slightly faster than the jaro_winkler jellyfish
			levenshtein = fuzz.ratio(str(facet1), str(facet2))
			if levenshtein > 80:
				temp_calc.append(levenshtein)
				temp_a2.append(facet2)
				temp_a1.append(facet1)

	temp = pd.DataFrame({'attribute1': temp_a1,'attribute2': temp_a2, 'levenshtein': temp_calc})
	return temp

def issue_filter(df):

	stop = set(stopwords.words('english'))
	d = enchant.DictWithPWL('en_US', 'lowercase_mywords.txt')

	# logic testing
	not_all_count = 0
	count_notcamelcase = 0
	count_camelcase = 0

	for row in tqdm(df.index,total= df.shape[0], unit="rows"):

		# row variables (used for check below)

		attribute1 = str(df.ix[row, 'attribute1'])
		attribute2 = str(df.ix[row, 'attribute2'])
		levenshtein = fuzz.ratio(str(attribute1), str(attribute2))
		df.ix[row, 'levenshtein'] = levenshtein

		attribute1_space = re.sub(r'\s+', '', str(attribute1))
		attribute2_space = re.sub(r'\s+', '', str(attribute2))

		attribute1_stripNo = re.sub(r'\d+', '', attribute1)
		attribute2_stripNo = re.sub(r'\d+', '', attribute2)

		attribute1_case = attribute1.lower()
		attribute2_case = attribute2.lower()

		attribute1_specials = re.sub(r'[a-zA-Z0-9 ]+', '', str(attribute1))
		attribute2_specials = re.sub(r'[a-zA-Z0-9 ]+', '', str(attribute2))

		full_strip1 = re.sub('[^a-zA-Z ]', '', attribute1).lower()
		full_strip2 = re.sub('[^a-zA-Z ]', '', attribute2).lower()

		# check for CamelCase (tokenise differently)
		CamelCase = (attribute1[1:] != attribute1_case[1:]) and (attribute1 == attribute1_space)

		# get tokens
		# NB tokens are letters only, missing spaces will be destroyed!
		if not CamelCase:
			tokens1 = wordpunct_tokenize(full_strip1)
			tokens2 = wordpunct_tokenize(full_strip2)

			numInc_tokens1 = wordpunct_tokenize(attribute1_case)
			numInc_tokens2 = wordpunct_tokenize(attribute2_case)

			noCaseStrip_tokens1 = wordpunct_tokenize(attribute1_stripNo)
			noCaseStrip_tokens2 = wordpunct_tokenize(attribute2_stripNo)


			count_notcamelcase += 1

		else:
			full_strip1 = re.sub('[^a-zA-Z ]', '', attribute1)
			full_strip2 = re.sub('[^a-zA-Z ]', '', attribute2)
			split1 = re.sub(r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))', r' \1', full_strip1).split()
			split2 = re.sub(r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))', r' \1', full_strip2).split()
			tokens1 = [x.lower() for x in split1]
			tokens2 = [x.lower() for x in split2]

			noCaseStrip_tokens1 = [x for x in split1]
			noCaseStrip_tokens2 = [x for x in split2]

			count_camelcase += 1

		# spellcheck
		bad_words1 = []
		bad_words2 = []
		for token in tokens1:
			if not d.check(token): #passes dict test
				bad_words1.append(token)
		for token in tokens2:
			if not d.check(token):
				bad_words2.append(token)

		# lemmatised tokens
		lemma_tokens1 = []
		lemma_tokens2 = []
		for token in tokens1:
			lemma_tokens1.append(WordNetLemmatizer().lemmatize(token)) # lemma of token
		for token in tokens2:
			lemma_tokens2.append(WordNetLemmatizer().lemmatize(token))

		# stemmed tokens
		stem_tokens1 = []
		stem_tokens2 = []
		for token in tokens1:
			stem_tokens1.append(PorterStemmer().stem(token)) # stem of token
		for token in tokens2:
			stem_tokens2.append(PorterStemmer().stem(token))

		'''
		Check for exemptions

		'''

		# if attibutes contain vivoscreen a higher levenshtein cutoff is applied

		if re.search('vivoscreen', attribute1) and re.search('vivoscreen', attribute2):
			attribute1_strip = re.sub('vivoscreen', '', attribute1)
			attribute2_strip = re.sub('vivoscreen', '', attribute2)
			levenshtein = fuzz.ratio(str(attribute1_strip), str(attribute2_strip))
			if levenshtein < 80:
				df.drop(row) # drop the row if the match was only present due to 'vivoscreen'
				continue

		# if both attributes are DNA/RNA sequences they should be automatically skipped

		if re.search('^[atgcuATGCU]+$', attribute1 and attribute2):
			df.drop(row)
			continue

		'''
		Check the reason for pair discrepancies

		'''

		# check if discrepancy is partially due to the presence of a number
		lev_stripNo = fuzz.ratio(str(attribute1_stripNo), str(attribute2_stripNo))
		number_discrepancy = lev_stripNo > levenshtein

		# check if discrepancy is partially due to the presence of case
		lev_case = fuzz.ratio(str(attribute1_case), str(attribute2_case))
		case_discrepancy = lev_case > levenshtein

		# check if discrepancy is partially due to the presence of spaces
		space_discrepancy = (len(attribute1) - len(attribute1_space)) != (len(attribute2) - len(attribute2_space)) # true if there is a space difference at all

		onlySpace_discrepancy = attribute1_space == attribute2_space # true if the space is the only difference

		# check if discrepancy is partially due to special characters
		specials_discrepancy = collections.Counter(attribute1_specials) != collections.Counter(attribute2_specials) # just checks if any special characters are present

		if specials_discrepancy: # is the only difference the special characters?
			translation_table1 = str.maketrans(dict.fromkeys(attribute1_specials))
			attribute1_special_strip = attribute1.translate(translation_table1)
			translation_table2 = str.maketrans(dict.fromkeys(attribute2_specials))
			attribute2_special_strip = attribute2.translate(translation_table2)
			just_specials_discrepancy = attribute2_special_strip == attribute1_special_strip
		else:
			just_specials_discrepancy = False

		# is the discrepancy partially due to an extra word/s
		wordNo_discrepancy = len(tokens1) != len(tokens2)

		# # check if discrepancy is partially due to word duplication
		# wordDuplication_discrepancy = (collections.Counter(numInc_tokens1) == collections.Counter(numInc_tokens2)) != (set(numInc_tokens1) == set(numInc_tokens2))

		# is discrepancy is partially due to stop words (NB numbers and specials are already stripped from tokens)
		list_stops1 = [i.lower() for i in tokens1 if i.lower() in stop]
		list_stops2 = [i.lower() for i in tokens2 if i.lower() in stop]
		stopWord_discrepancy = collections.Counter(list_stops1) != collections.Counter(list_stops2)

		# is the discrepancy partially due to words (tokens) that fail to pass the dictionary (including custom list)
		spell_discrepancy = (collections.Counter(bad_words1) != collections.Counter(bad_words2))

		# are there any words that failed to pass the dictionary? If so, what are they?
		if len(bad_words1 + bad_words2) > 0:
			bad_words = bad_words1 + list(set(bad_words2) - set(bad_words1)) # duplicates removed
		else:
			bad_words = False

		# is the difference partially due to lemmatisation issues (pluralisation of words etc)?
		lemma_discrepancy = fuzz.ratio(str(lemma_tokens1), str(lemma_tokens2)) > fuzz.ratio(str(tokens1), str(tokens2))

		# is the difference only due to and s difference?
		if lemma_discrepancy:
			noS_tokens1 = []
			noS_tokens2 = []
			noSnoStrip_tokens1 = []
			noSnoStrip_tokens2 = []

			for t in tokens1:
				if t[-1:] == 's':
					noS_tokens1.append(t[:-1])
				else:
					noS_tokens1.append(t)

			for t in tokens2:
				if t[-1:] == 's':
					noS_tokens2.append(t[:-1])
				else:
					noS_tokens2.append(t)

			for t in noCaseStrip_tokens1:
				if t[-1:] == 's':
					noSnoStrip_tokens1.append(t[:-1])
				else:
					noSnoStrip_tokens1.append(t)

			for t in noCaseStrip_tokens2:
				if t[-1:] == 's':
					noSnoStrip_tokens2.append(t[:-1])
				else:
					noSnoStrip_tokens2.append(t)



			s_discrepancy = collections.Counter(noS_tokens1) == collections.Counter(noS_tokens2)

			# many have a case and s issue only. This is checked here as this is a good candidate for automated curation.
			if s_discrepancy:
				sLower_discrepancy = collections.Counter(noSnoStrip_tokens1) != collections.Counter(noSnoStrip_tokens2)
			else:
				sLower_discrepancy = False
		else:
			s_discrepancy = False
			sLower_discrepancy = False

		# is the difference partially due to stemming endings (harsher stripping than lemma)?
		stem_discrepancy = fuzz.ratio(str(stem_tokens1), str(stem_tokens2)) > fuzz.ratio(str(tokens1), str(tokens2))



		df.ix[row, 'number_discrepancy'] = number_discrepancy
		df.ix[row, 'case_discrepancy'] = case_discrepancy
		df.ix[row, 'space_discrepancy'] = space_discrepancy
		df.ix[row, 'onlySpace_discrepancy'] = onlySpace_discrepancy
		df.ix[row, 'specials_discrepancy'] = specials_discrepancy
		df.ix[row, 'just_specials_discrepancy'] = just_specials_discrepancy
		df.ix[row, 'wordNo_discrepancy'] = wordNo_discrepancy
		# df.ix[row, 'wordDuplication_discrepancy'] = wordDuplication_discrepancy
		df.ix[row, 'stopWord_discrepancy'] = stopWord_discrepancy
		df.ix[row, 'spell_discrepancy'] = spell_discrepancy
		df.ix[row, 'lemma_discrepancy'] = lemma_discrepancy
		df.ix[row, 's_discrepancy'] = s_discrepancy
		df.ix[row, 'sLower_discrepancy'] = sLower_discrepancy
		df.ix[row, 'stem_discrepancy'] = stem_discrepancy
		df.ix[row, 'bad_words'] = str(bad_words)
		df.ix[row, 'possible_camelCase'] = CamelCase


		# logic testing
		
		if not number_discrepancy and not case_discrepancy and not space_discrepancy and not specials_discrepancy \
		and not wordNo_discrepancy and not stopWord_discrepancy and not \
		spell_discrepancy and not lemma_discrepancy and not stem_discrepancy and not onlySpace_discrepancy \
		and not s_discrepancy and not just_specials_discrepancy and not sLower_discrepancy:
			not_all_count += 1


		# pseudo confidence assignment (slightly weird go at guessing confidence of merge prior to machine learning)

		if number_discrepancy:
			pseudo_confidence = 0.1
		else:
			if onlySpace_discrepancy or just_specials_discrepancy or s_discrepancy or sLower_discrepancy:
				pseudo_confidence = 0.9
			else:
				score = 0.9
				if case_discrepancy:
					score = score - 0.1
				if space_discrepancy:
					score = score - 0.1
				if specials_discrepancy:
					score = score - 0.1
				if wordNo_discrepancy:
					score = score - 0.1
				if stopWord_discrepancy:
					score = score - 0.1
				if spell_discrepancy:
					score = score - 0.1
				if lemma_discrepancy or stem_discrepancy:
					score = score - 0.1
				pseudo_confidence = score

		df.ix[row, 'pseudo_confidence'] = pseudo_confidence


		# determine suggested polarity of pair (suggest good and bad attribute)
		'''
		This is just a guess and can be swapped later on by the curator. Therefore the decision is taken based on a priority
		ordered list which has been devised to roughly capture the likelyhood of a correct decision. This is an area that should be
		altered when results are in about how often curators have to switch the polarity of the merge.
		If a decision cannot be taken the pair remains alphabetically sorted.
		'''

		# attribute1_freq = freq_lookup_dict.get(good_facet) # problem here, good_facet ref before assignment
		# attribute2_freq = freq_lookup_dict.get(bad_facet)

		# if spell_discrepancy:
		# 	if len(bad_words1) > len(bad_words2):
		# 		switch = False
		# 	else:
		# 		switch = True
		# if just_specials_discrepancy:
		# 	if len(attribute1) > len(attribute2):
		# 		switch = True
		# 	else:
		# 		switch = False
		# elif onlySpace_discrepancy:
		# 	if len(attribute1) > len(attribute2):
		# 		switch = True
		# 	else:
		# 		switch = False
		# elif s_discrepancy:
		# 	if len(noS_tokens1) == len(tokens1):
		# 		good_facet = attribute1
		# 		bad_facet = attribute2
		# elif stopWord_discrepancy:
		# 	if len(list_stops1) > len(list_stops2):
		# 		switch = True
		# 	else:
		# 		switch = False
		# elif lemma_discrepancy:
		# 	if (len(str(tokens1)) - len(str(lemma_tokens1))) > (len(str(tokens2)) - len(str(lemma_tokens2))):
		# 		switch = True
		# 	else:
		# 		switch = False
		# elif stem_discrepancy:
		# 	if (len(str(tokens1)) - len(str(stem_tokens1))) > (len(str(tokens2)) - len(str(stem_tokens2))):
		# 		switch = True
		# 	else:
		# 		switch = False
		# else:
		# 	if int(attribute1_freq) > int(attribute2_freq):
		# 	switch = False
		# else:
		# 	switch = True

		# this is less smart but may work better

		attribute1_freq = freq_lookup_dict.get(attribute1)
		attribute2_freq = freq_lookup_dict.get(attribute2)

		if int(attribute1_freq) > int(attribute2_freq):
			switch = False
		else:
			switch = True

		if switch:
			good_facet = attribute2
			bad_facet = attribute1

			good_facet_freq = attribute2_freq
			bad_facet_freq = attribute1_freq

		else:
			good_facet = attribute1
			bad_facet = attribute2

			good_facet_freq = attribute1_freq
			bad_facet_freq = attribute2_freq


		
		lexical_update_timestamp = '{:%Y-%m-%d_%H-%M-%S}'.format(datetime.datetime.now())


		# create pair node in Neo4J db

		node_name = str(attribute1+' § '+attribute2) # this is alphabetically sorted to prevent duplication!


		x = Node('Pair', name = node_name, good_attribute = good_facet, bad_attribute = bad_facet, pseudo_confidence = pseudo_confidence,
		number_discrepancy = number_discrepancy, case_discrepancy = case_discrepancy, space_discrepancy = space_discrepancy,
		specials_discrepancy = specials_discrepancy, wordNo_discrepancy = wordNo_discrepancy,
		stopWord_discrepancy = stopWord_discrepancy, spell_discrepancy = spell_discrepancy, lemma_discrepancy = lemma_discrepancy,
		stem_discrepancy = stem_discrepancy, onlySpace_discrepancy = onlySpace_discrepancy, s_discrepancy = s_discrepancy,
		just_specials_discrepancy = just_specials_discrepancy, sLower_discrepancy = sLower_discrepancy, levenshtein = str(levenshtein),
		possible_camelCase = CamelCase, good_facet_freq = str(good_facet_freq), bad_facet_freq = str(bad_facet_freq), lexical_update_timestamp = lexical_update_timestamp) # create cypher object
		graph.merge(x, 'Pair', 'name') # merge is important to prevent duplicates, need to read more about this


	return (df, not_all_count, count_notcamelcase, count_camelcase)

def data_output(df):

	# # create separated dfs for analysis

	# df_number_discrepancy = df[df.number_discrepancy == True]
	# df_case_discrepancy = df[df.case_discrepancy == True]
	# df_space_discrepancy = df[df.space_discrepancy == True]
	# df_onlySpace_discrepancy = df[df.onlySpace_discrepancy == True]
	# df_specials_discrepancy = df[df.specials_discrepancy == True]
	# df_just_specials_discrepancy = df[df.just_specials_discrepancy == True]
	# df_wordNo_discrepancy = df[df.wordNo_discrepancy == True]
	# # df_wordDuplication_discrepancy = df[df.wordDuplication_discrepancy == True]
	# df_stopWord_discrepancy = df[df.stopWord_discrepancy == True]
	# df_spell_discrepancy = df[df.spell_discrepancy == True]
	# df_lemma_discrepancy = df[df.lemma_discrepancy == True]
	# df_s_discrepancy = df[df.s_discrepancy == True]
	# df_sLower_discrepancy = df[df.sLower_discrepancy == True]	
	# df_stem_discrepancy = df[df.stem_discrepancy == True]


	# df_number_discrepancy.to_csv('df_number_discrepancy.csv')
	# df_case_discrepancy.to_csv('df_case_discrepancy.csv')
	# df_space_discrepancy.to_csv('df_space_discrepancy.csv')
	# df_onlySpace_discrepancy.to_csv('df_onlySpace_discrepancy.csv')
	# df_specials_discrepancy.to_csv('df_specials_discrepancy.csv')
	# df_just_specials_discrepancy.to_csv('df_just_specials_discrepancy.csv')
	# df_wordNo_discrepancy.to_csv('df_wordNo_discrepancy.csv')
	# # df_wordDuplication_discrepancy.to_csv('df_wordDuplication_discrepancy.csv')
	# df_stopWord_discrepancy.to_csv('df_stopWord_discrepancy.csv')
	# df_spell_discrepancy.to_csv('df_spell_discrepancy.csv')
	# df_lemma_discrepancy.to_csv('df_lemma_discrepancy.csv')
	# df_s_discrepancy.to_csv('df_s_discrepancy.csv')
	# df_sLower_discrepancy.to_csv('df_sLower_discrepancy.csv')
	# df_stem_discrepancy.to_csv('df_stem_discrepancy.csv')



	# temp printouts


	# print(df)
	# print(df.shape[0])

	print('number_discrepancy')
	print(df['number_discrepancy'].sum())

	print('case_discrepancy')
	print(df['case_discrepancy'].sum())

	print('space_discrepancy')
	print(df['space_discrepancy'].sum())

	print('onlySpace_discrepancy')
	print(df['onlySpace_discrepancy'].sum())

	print('specials_discrepancy')
	print(df['specials_discrepancy'].sum())

	print('just_specials_discrepancy')
	print(df['just_specials_discrepancy'].sum())

	print('wordNo_discrepancy')
	print(df['wordNo_discrepancy'].sum())

	# print('wordDuplication_discrepancy')
	# print(df['wordDuplication_discrepancy'].sum())

	print('stopWord_discrepancy')
	print(df['stopWord_discrepancy'].sum())

	print('spell_discrepancy')
	print(df['spell_discrepancy'].sum())

	print('lemma_discrepancy')
	print(df['lemma_discrepancy'].sum())

	print('s_discrepancy')
	print(df['s_discrepancy'].sum())

	print('sLower_discrepancy')
	print(df['sLower_discrepancy'].sum())

	print('stem_discrepancy')
	print(df['stem_discrepancy'].sum())

	df.to_csv('temp.csv')

	result_df = df.groupby(['number_discrepancy','case_discrepancy', 'space_discrepancy', 'specials_discrepancy',
	'wordNo_discrepancy', 'stopWord_discrepancy', 'spell_discrepancy',
	'lemma_discrepancy', 'stem_discrepancy', 'onlySpace_discrepancy', 'just_specials_discrepancy', 's_discrepancy', 'sLower_discrepancy']).size().reset_index().rename(columns={0:'count'})

	result_df.to_csv('result_df.csv')

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

if __name__ == '__main__':
# def run():


	graph = Graph('http://localhost:7474/db/data', user='neo4j', password='neo5j') # initialising graph

	# generate pairs after first pass filter

	try:
		# input_df3 = pd.read_csv('data/filtered_pairs.csv', usecols = ['attribute1','attribute2','levenshtein'], sep = '§', engine = 'python')
		# df = pd.read_csv('data/attributes.csv', usecols = ['attribute', 'frequency'])
		# freq_lookup_dict = dict(zip(df.attribute.values, df.frequency.values))
		fill_attribute_graph(graph)

	except FileNotFoundError:
		print('file not found')

	# except FileNotFoundError:

	# 	print(datetime.datetime.now())
	# 	print('Running all by all fuzzy match. This process takes ~15 min for 26,000 x 26,000 attributes on an 8 core machine.')

	# 	input_df = pd.DataFrame(columns= ['attribute1', 'attribute2', 'levenshtein'])
	# 	df = pd.read_csv('data/attributes.csv', usecols = ['attribute', 'frequency'])
	# 	freq_lookup_dict = dict(zip(df.attribute.values, df.frequency.values))

	# 	all_pairs = tuple(list(df['attribute']))

	# 	pool = multiprocessing.Pool()
	# 	result = pool.map(multithread_fuzz, all_pairs)
	# 	input_df = input_df.append(result)

	# 	# check result

	# 	# print(input_df)
	# 	input_df2 = input_df[['attribute1', 'attribute2', 'levenshtein']]
	# 	# input_df2.to_csv('input_df.csv', columns= ['attribute1', 'attribute2', 'levenshtein'], sep = '§') # just a test

	# 	print(datetime.datetime.now())
	# 	print('Fuzzy matched ' + str(input_df2.shape[0]) + ' pairs out of ' + str((df.shape[0] ** 2)-df.shape[0]) + ' possible pairs')

	# 	# remove duplicates

	# 	print('Removing duplicates') 
	# 	input_df3 = input_df2[['attribute1','attribute2']].dropna(how='any').T.apply(sorted).T.drop_duplicates().reset_index(drop=True)
	# 	print('Removed ' + str(input_df2.shape[0] - input_df3.shape[0]) + ' out of ' + str(input_df2.shape[0]))

	# 	input_df3.to_csv('data/filtered_pairs.csv', columns= ['attribute1', 'attribute2', 'levenshtein'], sep = '§')


	# # filtering and adding Pair nodes to graph

	# results = issue_filter(input_df3)
	# results_df = results[0]
	# not_all_count = results[1]
	# count_notcamelcase = results[2]
	# count_camelcase = results[3]


	# # writing out some data

	# print('not_all_count:'+ str(not_all_count)+ ' out of '+ str(results_df.shape[0]))
	# print('count_camelcase:'+ str(count_camelcase)+ ' out of ' + str(results_df.shape[0]))
	# print('count_notcamelcase:'+ str(count_notcamelcase)+ ' out of ' + str(results_df.shape[0]))

	# data_output(results_df)











