# MGnify data downloaders

Utilities for downloading mirrors of MGnify data

## Files and directories

* `by_study.py` - Download all studies along with:
  * SSU taxonomy abundance TSV files (both phylum and full ranks)
  * GO term abundance TSV file
  * Associated JSON: study.json, analyses.json, samples.json
* `by_sample.py` - Download all samples and associated JSON for each one: analysis.json, go-terms.json, and taxonomy-ssu.json 
