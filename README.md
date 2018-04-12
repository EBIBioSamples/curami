# Curami: a BioSamples curation application

**A semi-automated curation tool to identify and harmonise erroneous attributes in the BioSamples database.**

See github  <https://github.com/EBIBioSamples/curami> for the current repo.

## Quickstart- Running Locally

**Step 1**

To generate input data from BioSamples API crawl: *python backend/make_input.py*

Note that the endpoint is currently hard coded. This will be updated after the release of BioSamples v4 to the new API but is currently pointing to staging and development machines.

**Step 2**

You must initialise and run a new neo4j DB in /CurationDB (see prerequisites for more information) then run the following scripts in series to initialise. *python backend/graph_make.py* followed by *python backend/lexical_filter.py*

**Step 3**

Then to analyse attribute relationships found by the lexical_filter run the following:

*python backend/coexistence.py python backend/values.py*

**Note**

- Calculations_main.py will eventually be able to automate this process.
- Use python 3
- Clustering is still under development (this relates to cluster and sample nodes in the Neo4J graph)

## Why we built Curami
The BioSamples database aims to aggregate sample metadata from all biological samples used throughout the EBI and serve as a central hub for linking and relating this metadata to biological data. To this end, it does not enforce information requirements, thereby lowering the barrier to entry for researchers; this also widens the scope of metadata collection. The downside to a zero validation design is the potential for low quality input which has a negative impact on search and information output. As of January 2018 BioSamples has over 5M samples sharing over 29K attributes. Curami aims to wrangle these 29K attributes and identify which of these attributes represent the same information (and can therefore be merged).

The current scope of this software does not extend to curation of the values associated with these attributes but it does explore the value data as one potential way of comparing attributes. Here we aim to use a holistic semi-automated approach to clean up the attributes and merge those which have been provided in error. This includes harmonising various cases of lexical disparity including case differences, spelling errors and pluralisation. It also uses ontology comparisons (of attributes and associated values) to explore merge opportunities as well as various statistical distances (including attribute coexistence and lexical similarity scoring of value information).

This information is provided to human curators in an intuitive web app, allowing a curator to make quick accurate decisions to clean up the data. By recording these decisions and the related features we are able to leverage machine learning methods to improve sorting, recommendation and identify opportunities to automate.

## About
-   Curami has a modular design so that specific scripts can be reused in different contexts. You will see the structure separation into three parts Acquisition, Analysis and Interaction.

1.  **Acquisition** engages with the biosamples API to extract and parse the data ready for analysis.
2.  **Analysis** has two sub-processes initial pair filtering and pair analysis.
  a.  **Initial pair filtering** finds lexically similar pairs out of a potential ((29K^2)-29K) pairs. Currently a levenshtein cut off of 0.8 is used to link 40K pairs
  b.  **Pair analysis** then calculates various statistical and similarity features for the pairs and builds a knowledge graph (in Neo4J).

3.  **Interaction** serves this information to the user and requests curator feedback. Decisions can be taken to merge, not merge or skip the pair. These modules also offer the ability to navigate through the pairs in various ways. For example you can curate the most popular attributes first or the pairs that are more likely to result in a decision to merge.

## Prerequisites
**Neo4J**

1. Create the directory */CurationDB*
2. Download and install Neo4J Community edition <https://neo4j.com/download/other-releases/>
3. Launch the application and navigate to the new folder and click run to initiate the database
4. Follow the provided link in your browser to the applications web interface
5. After initialisation you will be asked to sign in the initial username is 'neo4j' and the password is the same
6. When prompted, change the password to 'neo5j'. This has been hard coded into the application but can easily be changed. Note that all the scripts use this login information.
**Python**
The required python modules can be found in <https://github.com/EBIBioSamples/curami/blob/master/requirements.txt>
Not that innate python modules are not shown but may be required.
**Nltk.corpus**
See <http://www.nltk.org/data.html>


**Acquisition**
The app requires the following files:

1. attributes.csv csv list of attributes and their frequency of occurrence in the database
2. samples.csv csv with sampleID followed by all the attributes that sample contains
3. coexistences.csv which is used by *graph_make.py* list of all pairs that coexist and the frequency at which they do so
4. values.json list of dictionaries for each attribute. Each dictionary contains a dictionary with associated values and frequency of use.
5.

***backend/make_input.py***crawls the BioSamples API and produces these input files. This script can take a few hours to run depending on your connection speed. You can edit the endpoint by changing the 'pointer' variable in this script. With one crawl all the information is captured (attribute information, value information and co-occurance counting).


***backend/graph_make.py* **uses attributes.csv, samples.csv and coexistences.csv to build a networkX graph. This is saved as a graph file that is readable by Gephi (free graph visualization software similar to cytoscape). *coexistences.gexf* can also be read back into python using the networkX library. Whilst networkX offers many mathematical features it may have scaling and performance issues that would not make it suitable to run a high throughput recommendation engine. Neo4J may be more suitable for this. The intermediate calculations for node weightings can be found in *data/coexistencesProb.csv* which is also produced by this script.


 **A note about probability weighting (used for recommendation)**
If two attributes coexist frequently within samples we may presume they are related and provide distinct information. We could conclude that these facets should not be merged because they provide distinct information (this can be confirmed by checking value data too). However, numerous attributes in the BioSamples Database (such as *organism, synonym, model, package, organismPart* and *sampleSourceName*) will coexist with each other in samples more frequently than less numerous ones. Therefore, to derive the significance of the coexistence count we must normalise against individual attribute frequencies.


In order to do this we calculate the following steps:


1. probability of attribute = no of instances / total instance
2. expected coexistence count = probability of attribute1 * probability of attribute2 * total instances
3. difference = observed coexistence count - expected coexistence count
4. weight = difference / sum of differences


As BioSamples Data input is not randomly generated the vast majority of attributes do not contain any coexistence within samples and the vast majority that do have a positive difference (observed higher than expected). The graph is undirected even though Gephi and Neo4J insists on adding direction depending on which attribute is the 'source' or 'target' but this can be ignored. All weights add up to 1 (as per calculations outlined above) and the graph contains both positive and negative weights (negative when expected is higher than observed). These negative weights are often intuitively relevant (e.g. *organism part* and *serovar* with a difference of -27689 (weight -2.38e-05) or *environment biome* and *organism part* with a difference of -89490 (weight -5.24e-05)) and highly positive weights are also intuitive (e.g. *depth* and *elevation* with a difference of 99617 (weight 8.72e-05)).


**Analysis: Initial pair filtering**


Initial pair filtering is the process of pairing attributes and creating nodes in the Neo4J graph. Due to the large number of potential combinations this analysis must be a fast filter capable of quickly discounting very poor matches. Currently the application only uses Levenshtein comparison with a cut off threshold of 0.8. Therefore the whole application only analyses lexically similar pairs. This is a major limitation. However, when we have discovered predictive features with this first iteration other filters should be added to this process to find further pairs. An example would be a script to pair synonyms which may not necessarily be lexically similar.


Running *backend/lexical_filter.py* will

1. Compare all potential pairs and calculate the Levenshtein distance using a multithreaded refined fuzzy match to find the pairs which have a match score over a threshold of 80. 26,000 attributes paired with each other means that the fuzzy match is performed on 675,974,000 samples (excluding self-match). Therefore any initial code must be quick to throw away poor matches. This generates 29,243 matches (v3 data using all 26,000 CamelCase attributes).
2. Each of these pairs of attributes are then analysed more thoroughly to identify the nature of the differences. 14 different binary tests are performed as detailed below. On the 29,243 matches this takes around 30 minutes.

a.  Number Discrepancy - Is true if the attributes differ due to a numerical character
b.  Case Discrepancy - Is true if stripping case improves the Levenshtein score. Therefore, this measures if case is at least one determinant of the difference.
c.  Space Discrepancy - Indicates if a space difference is at least one part of the discrepancy.
d.  Only Space Discrepancy - If a space difference is the only difference between the two facets. Note that space discrepancies will not be calculated if camel cased attributes are detected.
e.  Special Character Discrepancy - If special characters are partially responsible for the difference this is marked as True.
f.  Just Specials Discrepancy - If special characters are the only difference this is a separate test. This may be a good candidate for automated curation
g.  Word Number Discrepancy - True if the number of tokens in the attribute differs. This indicates that the number of words in the attribute is different. Note that if the script detects capitalisation in the middle of a word and detects no spaces, it presumes that the attribute is camel case and tokenises appropriately. This is recorded with the parameter *possible_camelCase*
h.  Stop Word Discrepancy - Is true if the difference is due to a difference in the stopwords present. The stopwords used are from the NLTK corpus (imported from nltk.corpus import stopwords). These include the following 'on', 'here', 'himself', 'just', 'doesn', 'hadn', 'mightn', 'before', 'our', 'so', 'be', 'haven', 'off', 'up', 'o', 'same', 'ma', 'yourself', 'when', 'between', 'wouldn', 're', 'were', 'too', 'his', 'theirs', 'them', 'few', 'weren', 'of', 'nor', 'only', 'such', 'but', 'the', 'not', 'didn', 'i', 'an', 'is', 'don', 'him', 'a', 'it', 'below', 't', 'ourselves', 'we', 'did', 'each', 'while', 'being', 'couldn', 'he', 'doing', 'y', 'some', 'down', 'yours', 'more', 'hers', 'whom', 'she', 'other', 'very', 'having', 'this', 'into', 'during', 'further', 'by', 'in', 'no', 'because', 'or', 'under', 'are', 'do', 'they', 'their', 'your', 'both', 'why', 'as', 'herself', 'from', 'until', 'all', 'after', 'needn', 'against', 'and', 'myself', 'wasn', 'own', 'was', 'me', 'her', 'shouldn', 'won', 'who', 'had', 'where', 'than', 'will', 'now', 'over', 'm', 'have', 'with', 'through', 'd', 'll', 'isn', 'my', 'to', 'itself', 'has', 'once', 'for', 'been', 'again', 've', 'at', 'mustn', 'those', 'that', 'you', 'any', 's', 'should', 'hasn', 'above', 'does', 'which', 'its', 'shan', 'these', 'if', 'there', 'how', 'ours', 'then', 'can', 'out', 'about', 'ain', 'aren', 'most', 'yourselves', 'am', 'what', 'themselves'
i.  Dictionary Matching - A set of word tokens are generated. These are stripped of numbers, case and special characters. These are tested against enchants en_US disctionary supplemented with a large custom dictionary created using labels from all the ontologies captured via https://www.ebi.ac.uk/rdf. This includes a large list of organisms, chemicals and anatomy thus producing a scientific dictionary. True if there is a difference in spelling between the attributes. Two equally misspelled attributes will be marked as false.
j.  Lemmatisation Matching and Stem Matching- Lemmatisation and stemming are similar processes that strip a word back to its core. This is intended to find issues such as pluralisation or e.g. geographical vs geographically. If the only difference between facets is the addition of an 's' to the end of one of the tokens this is recorded separately with the test *s_discrepancy* and a slight variation *sLower_discrepancy*. In the latter, the only difference is the 's' ending and case differences. These are very good candidates for automated curation.

**Additional Parameters**
In addition to the tests detailed above the script also add the following parameters to the Neo4J Pair nodes:

- Good attribute and bad attribute: based on the tests above this is an imperfect guess as the polarity of the merge. This should get smarter after this first iteration of the app. Although this code is written the default is that the most popular attribute is the 'good' attribute and the potentially 'bad' attribute is the least popular one. Users can easily reverse this decision when they are curating. This should be monitored and changed over time to reduce the number of reverse merges.
- Levenshtein score: the fuzzy score that was initially calculated to pull the pair into the pipeline
- Pseudo Confidence: this is a guessed merge confidence score based on the tests described above. For example number differences would normally indicate that the merge should not take place whereas a spelling issue may increase the score. Undiagnosed problems are also put to the forefront which is useful for initially testing and vetting problems. Eventually this formula will need replacing with a data driven smarter algorithm but it should also ideally be used as a secondary sort as subject area is a more important ranking device.
- Frequencies: These are assigned for both attributes and show how many samples in the database use the attributes. This can be important for deciding which attribute should be kept.

- Once *backend/lexical_filter.py* has competed its run your Neo4J database will now contain the pair nodes. These will be unlinked and missing analysis. In the next section we will describe how these nodes are further analysed to produce more data features.

**Analysis: Pair analysis**

Analysis scripts are modular and can be ran in any order or separately. If further analysis methods are conceived they should be added to this part of the process e.g. an ontology analysis pipeline.

**A note on missing value warnings**
Missing attributes may occur if the pair has an attribute that is not in attributes.csv. The number of missing pairs is recorded. To minimise this, attributes.csv is generated as the last step in the input.py. This should be checked to ensure significant data isn't missing. This process may need to be more stringent in later versions.

***backend/coexistance.py***
Without flags this script will skip nodes that have previously has the relevant parameters calculated. This allows you to stop the script and re run to continue the calculations which is useful for long runs. Passing the -r flag will recalculate the information.

**Calculated Features:**

**Edge Weight**
If the attributes cooccur at least once this weight represents how often they do. This is defined in the section above 'A note about probability weighting'.
**Jaccard Coefficient**
Calculated by networkX. The Jaccard coefficient quantifies the overlap of attributes in the coocurance graph.
**Break Number**
The minimum number of edges that would need to be broken in order to separate the two attributes in the pair. This is useful for attributes that may not coocur. The break number will provide some information about how well related the attributes are.
**Degree**
This is calculated for both attributes separately. This is the number of attributes that coocur at least once with the attribute in question. This represents the promiscuity of the attribute.
 **Edge Total**
Degree of attribute 1 plus the degree of attribute 2.

***backend/values.py***
This module uses data/values.csv as input to compare how similar values are between two attributes. When ran in normal mode the script will skip nodes that are missing the various features calculated by this module. However, when passing the -r (recalculate) tag the script will recalculate the data for each node.

**Calculated Features:**

The *type of match* feature will return one of the following:

1. **numeric match** - when over 90% of both attribute values are numbers (including integers, floats and exponentials).
2. **date match** - when over 90% of both attribute values are dates (checking most date formats).
3. **strings match** - when over 90% of both attribute values are strings (defined as anything excluding numbers and dates).
4. **mixed match string / mixed match numeric / mixed match date** - and combinations thereof are returned if the ratios of these value types are within 10% of each other and the abundance of that value type is greater than 25%
5. **no match** - When none of the above conditions are met.


Given the *type of match* various other comparisons become relevant to consider. If a *numeric match* is detected then the magnitude of difference is calculated. This returns *'Roughly Equivalent*' if the mean of attribute 1's values and attribute 2's values are of the same **order of magnitude** (e.g. 12 and 45 will match but 0.1 and 3 will not). Whilst at first glance this may seem vague, the potential range of values to consider is significant therefore most statistical tests of numerical similarity are not appropriate. In the future it may be useful to also calculate and compare standard deviations (if the magnitude is similar) to ensure that the mean is a decent representative.

If the *type of match* is a string type match fuzzy scores are calculated for all combination of values in each attribute. This is reflected as a **Jaro Score**.

Top values and the number of unique values for each attribute are forwarded to the app to aid the curator. Here endless options are possible. User feedback is needed to decide what other information to capture. An **exact score** gives an indication of how many values are exactly the same in each attribute. This is more informative for string type values but it is calculated for every pair

***backend/auto_cluster.py***
*NB. This script isn't stable and is currently under development. I have described the target for the first version.*

This script will allow us to partition samples that contain the attributes in the pair into clusters thus allowing the curator to apply the curation decisions to specific samples. To do this the graph database must get more complex. Initially the script will add sample nodes and relationships from pair nodes to relevant samples. After clustering, the samples are also attached to k (the number of clusters determined) cluster nodes. Curators can then decide to only merge a specific set of clusters.
Initial trials have revealed that this type of analysis is computationally heavy but isn't frequently required. Therefore, it will be available upon user request within the app user. Trialing several clustering approaches revealed that most methods struggle to successfully determine k automatically. In the initial approach the method was going to be separated into automated and manual methods where a human had already determined k by eye. Sci-kit learn's DB-SCAN tends to be effective at k determination. Nevertheless, it is necessary to allow users to override this if they feel the determination is incorrect. These features need to be added.


This module requires the input data from 'samples.csv'. As with the other analysis scripts, if this program is run in recalculate mode (-r argument passed) it will strip Sample-Cluster relationships that were previously calculated rather than skipping previously calculated Pairs. Therefore when ran in normal mode, the script will essentially pick up where it left off.

**Calculated Features:**


- **tally** of no. of samples which have each or both attributes
- generation of a binary matrix (samples vs attribute presence/absence). Building this sparse table is the time limiting step that is preventing scaling.
- 2D reduction (MCA) of the binary matrix and plotting of **scatter graph**. Later I will also use sparse PCA and compare speeds.
- hierarchical clustering and plotting **dendrogram**
- DB scan for automated clustering, this will produce a **second scatter graph** and a sample membership list to each of k cluster which is later used to produce curation objects.
- total number of samples in pair 1, number of samples in attribute 1, number of samples in attribute 2 and no of shared samples
- file path for MCA scatter plot. N.B. The scatter plot from MCA is generated and saved in 'data/plots/...' for later recall along with the coordinates from the MCA analysis (files named mca_id.log). The log file is a csv with columns x and y coordinates as well as the frequency(s) of samples at that coordinates. These are samples with identical attributes.
- file path for hierarchical clustered dendrogram
- Adds a direct relationship (HAS_ATTRIBUTE) from the Pair nodes to relevant Sample nodes. These are not removed when k has been determined in a later step.

**Issues with calculating clustering for every pair and why on demand calculation is better.**

- When running in normal mode the script won't know if there are any missing samples as it will skip over any Pairs that have previously been calculated. Therefore, it is important to schedule this script in -recalculate mode to ensure extra samples are linked to on a regular basis. This is a good reason to have the analysis completed on demand rather than continually in the background.
- If an attribute contains more than 10,000 (affecting 378/27398 attributes in v3) samples it cannot be processed (due to time and memory issues). Equally it is often not useful to cluster the samples in these attributes because they are most likely the 'good attribute'. In cases where the attribute is present in more than 10,000 samples a dimension reduction is calculated for just one attribute. (In the next version dimension reductions of all single attributes should be pre-computed. Looking for clear diversity here could be done automatically and save much of this processing of pairs. The pairs could be computed only if the user requests them.)
- Equally problematic are cases where the sample is only found in 1 or 2 samples. Again, these are not very interesting from a clustering point of view and they break the MCA reduction. These cases are skipped and logged. Warnings to the user will show if any of these exceptions are encountered in the web app so they know why the clustering information is missing.

**A note on choosing a clustering method**
- Everyone loves K-means but unfortunately it is not an appropriate method for clustering dichotomous data. This is because the Euclidean distance will only be a count of the binary differences between samples. This means that inappropriate ties may occur which cannot be overcome in iterative cluster assignments. Hence, we shouldn't use k-means for clustering binary data.
- Appropriate alternatives are hierarchical clustering (as implemented by autocluster.py), two step clustering or spectral clustering. Or one can use MCA (which is better than PCA for binary data) to reduce the binary data into a number of dimensions which also serves to convert it from being binary (this is the first step of spectral clustering anyway). Then k-means is an appropriate clustering method too.
- In summary, generally dimension reduction (via calculation of eigenvalues) is required before clustering binary data. This step is done in autocluster to 2D. More dimensions improve resolution but this hinders plotting. It is however useful when used as a backend to clustering.
**A note on using Gephi.**
- Gephi is an open-source free graph visualisation program for windows, mac and linux. It is similar to cytoscape. Download at <https://gephi.org>

- When you load this into Gephi you must first insist that the 'weight' column becomes the edge weight. This can be done in the Data Laboratory with the 'Copy Data to Other Column' button intuitively. I also add these values to the label column so that I can see the values if I request them in the graph.

I suggest starting by changing the size of the node to be equivalent to 'Degree' aka how many edges that facet has. I followed this method <https://stackoverflow.com/questions/36239873/change-node-size-gephi-0-9-1>

For general help see this: <https://gephi.org/tutorials/gephi-tutorial-visualization.pdf>

The next step is the layout. There are three relevant algorithms for expanding the nodes. Here are my observations on each, WARNING this is a very reductive description:

- YifanHu(Proportional)
Seems the most intuitive so you can work out why things appear where they do. this is because the whole thing is a minimisation calculation based on the weights. That's why it's a circle, why big stuff tends to stay in the middle and the weakest linked stuff floats to the outer asteroid belt of junk. I recommend starting with this because you can understand what it is doing but it is not the best for getting discreet clusters.
-   OpenOrd
This does not give an intuitive result but it does make nice clusters for various reasons. It is supposedly the quickest but all these three work well enough with the dataset we have. It is great to watch it going through the various stages and would be perfect for a live demo.
-   ForceAtlas(2)
Default settings are nice and gives you something in-between the two above. I changed a few parameters to get the largest nodes out the edge of the screen so I could focus on smaller clusters in the middle. To do this switch on LinLog mode.

**Interaction - A Frontend Guide**

First you must login or create an account. This will establish a user node in the Neo4J graph and allow you to create relationships as you make curation decisions. Once logged in you can see the state of the data. You may notice here that some of your analysis pipelines have not ran successfully or have missed nodes. You can go back to the relevant analysis script and run it to continue to enrich the data and track the process here. You can navigate to the 'pairwise curation tool' either from this view using the button at the bottom of the screen or via the navigation bar at the top of the page.

**Pairwise Curation Tool**
If this is your first time using the tool you will not see any user stats on this screen. If you have previously made some curation decisions these will summasiered here. If you would like to wipe your previous curation this can be done by clicking on the settings cog and the button labelled 'Wipe ALL curations'.

Also in this settings menu are various methods to sort the pairs. 'Smart Sorting' will sort attribute pairs by the pseudo confidence score (in this first software iteration this is not very smart and represents an approximate guess about which features are likely to yield a positive merge decision). 'Max Sample Impact' will sort pairs by the least popular attribute's frequency. This will allow you to increase your curation impact on the most common attributes.
'Major Attributes' sorting will sort by the most popular attribute's frequency. This will allow you to curate the attributes that are the most abundant in the dataset. This can be used to cure attributes that are popular.

**Omit 'vioscreen' attributes**
Around 500 attributes begin with the word vioscreen. These attributes are part of a common medical screen by VIOCARE (<http://www.viocare.com/vioscreen.html>). If you don't want to see these attributes you can choose to omit them using the toggle button in the settings.

**Pair Curation**

Clicking on 'Begin curating' or 'Continue Curating' will take you to the next pair for you to curate. The URL of this page shows you the pair node's id e.g. <http://localhost:5000/attribute_curation/hewgreen/2758> is the page for node 2758. These ids are assigned by Neo4J and can be used to find specific pairs directly via the address bar. If you visit a pair that has previously been curated a black dialogue box will tell you what your previous decision was. You can change your mind my clicking on your new decision.

This view of the app shows relevant information that you can use to make your curation decision. You can scroll down the page and open the conceteena to reveal more information. (NB clustering information has not yet been added to the app).
The four options should be used as follows:
**Don't merge** if the attributes contain dissimilar information.
**Merge** if the attribute on the left hand side should be replaced by the attribute on the right hand side. In this scenario you believe the 'good attribute' is the one on the right hand side and the 'bad attribute' is on the left hand side.
**Merge Reverse** if the attribute on the right hand side is not appropriate and should be replaced by the attribute on the left hand side.
**Skip** if you cannot make a clear decision. These can be later reviewed to understand what further information needs to be provided to the user in order for them to make a decision.
**Beyond V1**
This work has identified many curation opportunities that we were unable to fully develop in this primary version. This first working demo has been shown to users and their feedback is invaluable for future agile development. Some of the use cases we have not been able to meet are as follows:

**Engaging with OLS**
Ontology informed cleanup is not yet directly implemented. The curation app could lead to a stronger thesaurus but we should also use the synonym knowledge we already have. Expanding attributes using zooma and using fuzzy attribute matching based on this is under development. The Zooma tool will be especially useful for identifying false positives.

**Engaging with MarRef**
Domain experts require a curation mechanism that allows them to focus on attributes that lie within their area of expertise (applies to FAANG and CBI). MarRef would like to use the app to explore marine metagenomic data and the related attributes and clean up the data therein. A strong recommendation engine would also allow them to identify related samples. They would like to see which samples meet their criteria and which samples are close identifying what information is missing.

**Engaging with EBI Metagenomics**
Again EBI metagenomics require a domain specific curation ability. They also want to see capability to curate the values associated with the attributes and methods to pull their data out of the bulk of BioSamples. They would like to tag different enclaves of sample based on the type of assay that is being done. E.g. how many samples are oral vs gut metagenomes? Which attributes are predictive features for this tag and which attributes are shared. They hope this can be used by a recommendation engine at input to improve attribute capture and help consistency within the community.

**Engaging with EBI Submissions**
Submissions (aka USI)  would like to leverage the knowledge that the app generates (especially recommendation via co-occurrence weighting) to suggest new fields to submitters when they are submitting data. For this they need an recommendation API that they can query for the suggestion. Ideally this recommendation would also have further dimensions and would be able to recommend values or attributes required to meet previously specified standards such as MIABIS etc.

**Engaging with ENA**
In order to improve metadata capture ENA would like to rank samples based on their metadata. Which samples are missing critical metadata fields that would make their metadata more valuable (and improve their relative scores).

**Engaging with BioSamples**
Provenance of curation is critical. Based on the user's profile we need to identify how valuable the curation is so that we can use the app's curation objects alongside other curation efforts. E.g. automated methods should not be applied if that particular element of metadata has already been reviewed by a domain expert. If we get this wrong we are potentially making the data worse.
Missing links are a problem in BioSamples. By catagorising samples we should be able to predict which external links should be present and find them if they are missing.

**Engaging with SciBite**
-   Once the app is in regular use the information can be used to produce a curation ontology which can be applied to other biological datasets. SciBite were interested in converting the data in the app into an ontology.

To deliver these features the next version of the app requires:

1.  Attribute recommendations using co-occurrence. Given a certain group of 'provided' attributes which other attributes should also be added? (FEATURE NOW IMPLEMENTED AWAITING DOCUMENTATION)
2.  Ability to curate specific domains rather than the whole dataset at once. The two approaches here are to provide a list of sample IDS then slice the data and re-run the analysis or preferably use the recommendation graph to guide the specialist user through their data (a sub graph within the main clade) (FEATURE NOW IMPLEMENTED AWAITING DOCUMENTATION)
3.  Profiling samples. How good is sample x's metadata? This requires clustering of samples and then measurement from the clusters mean.
4.  Expand analysis to utilise ontologies to assess merge pairs. This requires a new analysis module which can work alongside the other analysis scripts.
5.  Identification of strong correlations to identify which features can be used for automated curation.
6.  Implementation of deep learning unsupervised learning or decision tree using training data.
7.  Build a curation ontology using the data generated in the graph.
8.  Curation of value information. Identification of erroneous values (e.g. strings when most of the fields contain numbers.

** Other Features to Add**

- A user should be able to review their decisions in a table so they can review and change if necessary.
- Improve the initial pair filtering to include pairs beyond lexical similarity
- A curation object builder
- Ability to request clustering analysis for individual attributes. Maybe a 'deep analysis button' that could then be put to the top of the users list once complete or reinserted into their current session. Once the calculation has been carried out all users should be able to see this.
- A main script to launch all the analysis that is required and install dependencies. This should be ran at regular intervals to keep the data up to date. Decisions should not be lost when this is retriggered. These should be stored separately to prevent loss.
- Make the Neo4J login more secure by not hard coding the password 'neo5j' into the scripts
