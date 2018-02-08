# curami

## Quickstart
### Step 1
To generate input data from BioSamples API crawl:
`python backend/make_input.py`
### Step 2
You must initialise and run a new neo4j DB in `/CurationDB` then run the following scripts in series to initialise.
`python backend/graph_make.py`
`python backend/lexical_filter.py`
### Step 3
Then to analyse attribute relationships found by the lexical_filter run the following:

`python backend/coexistence.py`
`python backend/values.py`

### Note
* Calculations_main.py will eventually be able to automate this process.
* Use python 3
* Clustering is still under development
