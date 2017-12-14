{% extends "layout.html" %} {% block body %}
<div class="row">

<div id="toc" class="col-md-3 offset-md-8 row">

</div>

<div class="col-md-8 row">

BioSamples Attribute Curator Documentation
==========================================

**A semi-automated curation tool to identify and harmonise erroneous
attributes in the BioSamples database.**

### Scope

The digital BioSamples database aims to aggregate sample metadata from
all biological samples used throughout the world and serve as a central
hub for linking and relating this metadata to biological data. To this
end, it does not enforce information requirements, thereby lowering the
barrier to entry for researchers; this also widens the scope of metadata
collection. The downside to a zero validation design is the potential
for low quality input which has a negative impact on search and
information output. Therein lies the need for this software. As of
October 2017 BioSamples has over 4.710\^6 samples sharing over 27,000
attributes and is quickly growing.

The scope of this software does not extend to curation of the values
associated with these attributes but it does explore the value data as
one potential way of comparing attributes. Here we aim to use a holistic
semi-automated approach to clean up the attributes and merge those which
have been provided in error. This includes harmonising various cases of
lexical disparity including case differences, spelling errors and
pluralisation). It also uses ontology comparisons (of attributes and
associated values) to explore merge opportunities as well as various
statistical distances (including attribute coexistence and lexical
similarity scoring of value information).

After identification of attribute pairs for curation, we extrapolate
clusters of samples to ensure curations are only applied to relevant
samples. This improves our confidence and flexibility. Automated and
semi-automated analysis are recorded and remembers in a clearly
accessible way to avoid duplicate computation and provide data for
correlation analysis (and other machine learning methods). This latter
analysis should dramatically improve the power of this tool and is an
essential component in its design.

##### Beyond Immediate Scope {#beyond-immediate-scope (v1.1)}

-   Profiling attributes on an individual basis
-   Ontology informed clean-up- although not directly considered this
    will inevitably be improved through use of this tool.
-   Profiling of samples- although clustering methods herein could be
    adapted to meet this goal.
-   Checking external links and references- this should be incorporated
    when possible (relates to profiling samples).
-   Replacing value information- although the methods herein can be
    adapted this would ideally operate as a separate pipeline as
    specific considerations differ.
-   Implementation of deep learning unsupervised learning or decision
    tree using training data from v1.0

### Scripts

##### main.py

Controlling script. Imports other scripts. Decides when to generate new
input. Launches analysis scripts in correct order. Amalgamates results.
Stores and edits output files.

**Organisation**
Broadly the pipeline operates as such:

input -&gt; pair filtering -&gt; analysis -&gt; clustering -&gt; human
input -&gt; curation items

-   input- generate input files required if they are old
-   pair filtering- pairwise scripts that are fast enough to analyse
    every pair and suggest merge opportunities\^\*
-   analysis- including coexistence graph analysis and value matching
    distances. These scripts also generate pairwise distances but they
    tend to be slower. Therefore they are applied to a pre-trimmed list
    of pairs.
-   clustering- samples affected by suggested merges are clustered to
    ensure homogeneity before merging. At this stage it is also possible
    to apply the curations to specific samples.
-   human input- human curators are presented with various data to make
    merge decisions.
-   curation items- the output is a list of sample specific attribute
    merges ready to be turned into curation items.

\^\* note that the lexical script does much more than filter results. It
also XXXXXXXX

Script wise pipe:

input.py -&gt; lexical.py -&gt; coexistance.py -&gt; values.py -&gt;
cluster.py

**Output**
##### input.py

Generates inputs for pipeline and stores output into ./data as csv or
json. This script makes 4 files:

1.  attributes.csv csv list of attributes and their frequency of
    occurrence in the database

2.  samples.csv csv with sampleID followed by all the attributes that
    sample contains

3.  coexistences.json list of all pairs that coexist in the same sample
    and the frequency at which they do so

4.  values list of dictionaries containing key:value pairs as
    attribute:\[value\], with values stored as a list

The 'attribute.csv' is generated quickly (XXXXXX time) as it only
requires 1 Solr request. This file is only used for XXXXXX.
'samples.csv' is generated by iterative page requests through BioSamples
v3 API and scrapes each page. This process is multithread enabled to
speed up the process but this is still a process that takes longer than
8 hours. The temporary threads this process produces are concatenated to
produce 'samples.csv'. The sampleID is then stripped from each line and
the output is then used to feed the modules that count the coexistence
which ultimately builds 'coexistences.json'.

This script then does some pre-processing of the data. It converts the
json into csv format (coexistences.csv)

##### graph\_make.py

This pre-processing script uses **attributes.csv** and
**coexistences.json** to calculate weighting and create a networkX
graph. This output is stored in three files:

1.  coexistences.csv This is a csv converted directly from the json
    using re. While this may be prone to breaking and would ideally be
    replaced with a json reader, unfortunately there are issues due to
    the flat structure of the json file.
2.  coexistencesProb.csv Pandas is used to lookup attribute frequencies
    and calculate expected coexistence counts. These can be compared to
    expected coexistence counts to calculate a weight (see below for
    more details).
3.  coexistences.gexf NetworkX graph output suitable for reading by
    Gephi (see *A note on Gephi*).

**Why do we require probability weighting?**
If two attributes coexist frequently within samples we may presume they
are related and provide distinct information. We could conclude that
these facets should not be merged because they provide distinct
information (this can be confirmed by checking value data too). However,
numerous attributes in the BioSamples Database (such as organism,
synonym, model, package, organismPart and sampleSourceName) will coexist
with each other in samples more frequently than less numerous ones.
Therefore, to derive the significance of the coexistence count we must
normalise against individual attribute frequencies.

In order to do this we calculate the following steps:

1.  probability of attribute = no of instances / total instances
2.  expected coexistence count = probability of attribute1 \*
    probability of attribute2 \* total instances
3.  difference = observed coexistence count - expected coexistence count
4.  weight = difference / sum of differences

As BioSamples Data input is not randomly generated the vast majority of
attributes do not contain any coexistence within samples and the vast
majority that do have a positive difference (observed higher than
expected). The graph is undirected even though Gephi insists on adding
direction depending on which attribute is the 'source' or 'target' but
this is only a visualisation bug. All weights add up to 1 (as per
calculations outlined above) and the graph contains both positive and
negative weights (negative when expected is higher than observed). These
negative weights are often intuitively relevant (e.g. organismPart and
serovar with a difference of -27689 or environmentBiome and organismPart
with a difference of -89490) and highly positive weights are also
intuitive (e.g. depth and elevation with a difference of 99617).

**Missing value warnings.**
Missing attributes may occur if the pair has an attribute that is not in
attributes.csv. The number of missing pairs is recorded. To minimise
this, attributes.csv is generated as the last step in the input.py. This
should be checked to ensure significant data isn't missing. This process
may need to be more stringent in later versions.

**A note on using Gephi.**
Gephi is an open-source free graph visualisation program for windows,
mac and linux. Download at https://gephi.org

1.  When you load this into Gephi you must first insist that the
    'weight' column becomes the edge weight. This can be done in the
    Data Laboratory with the 'Copy Data to Other Column' button
    intuitively. I also add these values to the label column so that I
    can see the values if I request them in the graph.

2.  I suggest starting by changing the size of the node to be equivalent
    to 'Degree' aka how many edges that facet has. I followed this
    method
    https://stackoverflow.com/questions/36239873/change-node-size-gephi-0-9-1

For general help see this:
https://gephi.org/tutorials/gephi-tutorial-visualization.pdf

3.  The next step is the layout. There are three relevant algorithms for
    expanding the nodes. Here are my observations on each, WARNING this
    is a very reductive description:

YifanHu(Proportional)

Seems the most intuitive so you can work out why things appear where
they do. this is because the whole thing is a minimisation calculation
based on the weights. That’s why it’s a circle, why big stuff tends to
stay in the middle and the weakest linked stuff floats to the outer
asteroid belt of junk. I recommend starting with this because you can
understand what it is doing but it is not the best for getting discreet
clusters.

OpenOrd

This does not give an intuitive result but it does make nice clusters
for various reasons. It is supposedly the quickest but all these three
work well enough with the dataset we have. It is great to watch it going
through the various stages and would be perfect for a live demo.

ForceAtlas(2)

Default settings are nice and gives you something in-between the two
above. I changed a few parameters to get the largest nodes out the edge
of the screen so I could focus on smaller clusters in the middle. To do
this switch on LinLog mode.

##### lexical.py

This is an input script that looks for lexically similar (&gt;80 score
on Levenshtein fuzzy match) attributes based on their name alone. It
uses a multithreaded refined fuzzy match to find the pairs which have a
match score over a threshold of 80. 26,000 attributes paired with each
other means that the fuzzy match is performed on 675,974,000 samples
(excluding self-match). Therefore any initial code must be quick to
throw away poor matches. This generates 29,243 matches (v3 data using
all 26,000 CamelCase attributes).

Each of these pairs of attributes are then analysed more thoroughly to
identify the nature of the differences. 14 different tests are performed
as detailed below. On the 29,243 matches this takes around 30 minutes.

Number Discrepancy
This is `True` if the attributes differ due to a numerical character.

Case Discrepancy
This is `True` if stripping case improved the Levenshtein score.
Therefore, this measures if case is at least one determinant of the
difference.

Space Discrepancy
Indicating if a space difference is at least one part of the
discrepancy. `onlySpace_discrepancy` is `True` if a space difference is
the only difference between the two facets. Note that these two
determinants will all be negative if camel cased attributes are fed into
the system.

Special Character Discrepancy
If special characters are partially responsible for the difference this
is marked as `True`. If special characters are the only difference there
is a separate test `just_specials_discrepancy`. This may be a good
candidate for automated curation.

Word Number Discrepancy
This is `True` if the number of tokens in the attribute differs. This
indicates that the number of words in the attribute is different. Note
that if the script detects capitalisation in the middle of a word and
detects no spaces, it presumes that the attribute is camel case and
tokenises appropriately. This is recorded with the parameter
`possible_camelCase`.

Stop Word Discrepancy
If the difference is due to a difference in the stopwords present in the
two attributes this is marked as `True`. The stopwords used are from the
NLTK corpus (imported `from nltk.corpus import stopwords`). These
include the following
`'on', 'here', 'himself', 'just', 'doesn', 'hadn', 'mightn', 'before', 'our', 'so', 'be', 'haven', 'off', 'up', 'o', 'same', 'ma', 'yourself', 'when', 'between', 'wouldn', 're', 'were', 'too', 'his', 'theirs', 'them', 'few', 'weren', 'of', 'nor', 'only', 'such', 'but', 'the', 'not', 'didn', 'i', 'an', 'is', 'don', 'him', 'a', 'it', 'below', 't', 'ourselves', 'we', 'did', 'each', 'while', 'being', 'couldn', 'he', 'doing', 'y', 'some', 'down', 'yours', 'more', 'hers', 'whom', 'she', 'other', 'very', 'having', 'this', 'into', 'during', 'further', 'by', 'in', 'no', 'because', 'or', 'under', 'are', 'do', 'they', 'their', 'your', 'both', 'why', 'as', 'herself', 'from', 'until', 'all', 'after', 'needn', 'against', 'and', 'myself', 'wasn', 'own', 'was', 'me', 'her', 'shouldn', 'won', 'who', 'had', 'where', 'than', 'will', 'now', 'over', 'm', 'have', 'with', 'through', 'd', 'll', 'isn', 'my', 'to', 'itself', 'has', 'once', 'for', 'been', 'again', 've', 'at', 'mustn', 'those', 'that', 'you', 'any', 's', 'should', 'hasn', 'above', 'does', 'which', 'its', 'shan', 'these', 'if', 'there', 'how', 'ours', 'then', 'can', 'out', 'about', 'ain', 'aren', 'most', 'yourselves', 'am', 'what', 'themselves'`.

Dictionary Matching
A set of word tokens are generated. These are stripped of numbers, case
and special characters. These are tested against enchants en\_US
disctionary supplemented with a large custom dictionary created using
labels from all the ontologies captured via https://www.ebi.ac.uk/rdf.
This includes a large list of organisms, chemicals and anatomy thus
producing a scientific dictionary.

This parameter is only set as `True` if there is a difference in
spelling between the attributes. Two equally misspelled attributes will
fall through the cracks.

Lemmatisation Matching and Stem Matching
Lemmatisation and stemming are similar processed which strip a word back
to its essential core. This is intended to find issues such as
pluralisation or geographical vs geographically. If the only difference
between facets is the addition of an 's' to the end of one of the tokens
this is recorded additionally in the boolean parameter `s_discrepancy`
and a slight variation `sLower_discrepancy` (where the only difference
is the 's' and case differences). These are very good candidates for
automated curation.

Additional Parameters
In addition to the tests detailed above the script also add the
following parameters to the Neo4J Pair nodes:

-   Good attribute and bad attribute: based on the tests above this is
    an imperfect guess as the polarity of the merge
-   Levenshtein score: the fuzzy score that was initially calculated to
    pull the pair into the pipeline
-   Pseudo Confidence: this is a guessed merge confidence score based on
    the tests described above. For example number differences would
    normally indicate that the merge should not take place whereas a
    spelling issue may increase the score. Undiagnosed problems are also
    put to the forefront which is useful for initially testing and
    vetting problems. Eventually this formula will need tweaking but it
    should also ideally be used as a secondary sort as subject area is a
    more important ranking device. This will be implemented using the
    recommendations from the coexistence graph.
-   Frequencies: These are assigned for both attributes and show how
    many samples in the database use the attributes. This can be
    important for deciding which facet to use.

##### coexistance.py

needs graph\_make.py to be run first input: \* query pairs from files
starting with merge \* fold\_diff\_weighted\_network.gexf

pulls in all csv starting with 'merge'

output: mergeHighConfidence\_stats.csv mergeLowConfidence\_stats.csv

I'm hoping I can iteratively add to these files as I feed them to each
stats module.

has -r ability vs the usual continue mode - need to add all its outputs
here and what they mean

##### values.py

This module uses data/values.csv as input to compare how similar values
are between two attributes. When ran in normal mode the script will skip
nodes that are missing the various features calculated by this module.
However, when running with the -r (recalculate) tag the script will
recalculate the data for each node.

The *type of match* feature will return one of the following:

1.  **numeric match** - when over 90% of both attribute values are
    numbers (including integers, floats and exponentials).
2.  **date match** - when over 90% of both attribute values are dates
    (checking most date formats).
3.  **strings match** - when over 90% of both attribute values are
    strings (defined as anything excluding numbers and dates).
4.  **mixed match string**/**mixed match numeric**/**mixed match date**-
    and combinations thereof are returned if the ratios of these value
    types are within 10% of each other and the abundance of that value
    type is greater than 25%.
5.  **no match** - When none of the above conditions are met.

Given the *type of match* various other comparisons become relevant to
consider. If a *numeric match* is detected then the magnitude of
difference is calculated. This returns *'Roughly Equivalent'* if the
mean of attribute 1's values and attribute 2's values are of the same
order of magnitude (e.g. 12 and 45 will match but 0.1 and 3 will not).
Whilst at first glance this may seem vague, the potential range of
values to consider is significant therefore most statistical tests of
numerical similarity are not appropriate. In the future it may be useful
to also calculate and compare standard deviations to ensure that the
mean is a decent representative.

If the *type of match* is a string type match fuzzy scores are
calculated for all combination of values in each attribute. This is
reflected as a *Jaro Score*.

Top values and the number of unique values for each attribute are
forwarded to the app to aid the curator. Here endless options are
possible. User feedback is needed to decide what other information to
capture. An *exact score* gives an indication of how many values are
exactly the same in each attribute. This is more informative for string
type values but it is calculated for every pair.

##### auto\_cluster.py

This script performs clustering up to the point of k (cluster number)
determination. Whilst various automated methods exist to determine k,
they are unsuitable on the highly variable BioSample dataset. Therefore,
this script aims to equip the user with as much information as possible
to make a judgement on k. After k has been manually entered the
mancluster.py script can then perform further calculations and provide
information on individual clusters such as median sample representations
of that cluster. This module requires the input data from 'samples.csv'.
If this program is run in recalculate mode (-r argument passed) it will
strip Sample-Cluster relationships that were previously calculated
rather than skipping previously calculated Pairs. Therefore when ran in
normal mode, the script will essentially pick up where it left off.

The clustering that can be done automatically prior to a user entered k
includes:

-   tally of no. of samples which have each or both attributes
-   generation of a binary matrix (samples vs attribute
    presence/absence)
-   2D reduction (MCA) of the binary matrix and plotting of scatter
    graph
-   hierarchical clustering and plotting dendrogram

N.B. When running in normal mode the script won't know if there are any
missing samples as it will skip over any Pairs that have previously been
calculated. Therefore, it is important to schedule this script in
-recalculate mode to ensure extra samples are linked to on a regular
basis.

**Exceptions**
If an attribute contains more than 10,000 (affecting 378/27398
attributes in v3) samples it cannot be processed (due to time and memory
issues). Equally it is often not useful to cluster the samples in these
attributes because they are most likely the 'good attribute'. In cases
where the attribute is present in more than 10,000 samples a dimension
reduction is calculated for just one attribute. (In the next version
dimension reductions of all single attributes should be pre-computed.
Looking for clear diversity here could be done automatically and save
much of this processing of pairs. The pairs could be computed only if
the user requests them.)

Equally problematic are cases where the sample is only found in 1 or 2
samples. Again, these are not very interesting from a clustering point
of view and they break the MCA reduction. These cases are skipped and
logged. Warnings to the user will show if any of these exceptions are
encountered in the web app so they know why the clustering information
is missing.

**The output of this script for each Pair in the Neo4j graph**
Added to Pair node: 1. total no of samples in pair 1. no of samples in
attribute 1 1. no of samples in attribute 2 1. no of shared samples in
pair 1. file path for MCA scatter plot 1. file path for hierarchical
clustered dendrogram

Relationships added: 1. Adds a direct relationship (HAS\_ATTRIBUTE) from
the Pair nodes to relevant Sample nodes. These are not removed when k
has been determined in a later step.

The scatter plot from MCA is generated and saved in 'data/plots/...' for
later recall along with the coordinates from the MCA analysis (files
named mca\_id.log). The log file is a csv with columns x and y
coordinates as well as the frequency (s)of samples at that coordinates.
These are samples with identical attributes.

### Further work

-   add more automated k methods aiming to identify a fully automated
    method.
-   review dendrogram plot aesthetics
-   after k has been manually determined k-means clustering needs to
    work from xD data not 2D data hence autoclus needs to pass on the
    binary matrix?
-   calculates the number of samples affected by the merge. this needs
    to be used to rank when human curators see facets.

##### man\_cluster.py

This script will only trigger when a user has entered a k. It should be
able to run automatically but mainly on demand via the app. When k is
entered this script should fire and produce results ASAP for that facet.
If the user changes their mind it should trigger again. The automatic
firing of this should update and mop up anything that is old or hasn't
been calculated.

**Choosing a clustering method**
Everyone loves K-means but unfortunately it is not an appropriate method
for clustering dichotomous data. This is because the Euclidean distance
will only be a count of the binary differences between samples. This
means that inappropriate ties may occur which cannot be overcome in
iterative cluster assignments. Hence, we shouldn't use k-means for
clustering binary data.

Appropriate alternatives are hierarchical clustering (as implemented by
autocluster.py), two step clustering or spectral clustering. Or one can
use MCA (which is better than PCA for binary data) to reduce the binary
data into a number of dimensions which also serves to convert it from
being binary (this is the first step of spectral clustering anyway).
Then k-means is an appropriate clustering method too.

In summary, generally dimension reduction (via calculation of
eigenvalues) is required before clustering binary data. This step is
done in autocluster to 2D. More dimensions improve resolution but this
hinders plotting. It is however useful when used as a backend to
clustering.

##### Neo4J Curation Database

This stores the output from all the scripts.

-   pairs are sorted alphabetically prior to node creation to prevent
    duplication of reverse pairs.
-   before I have the lexical script working I need to manually create
    the pairs from the lexical script to give me a platform to get the
    other scripts working.

</div>

</div>

{% endblock %}
