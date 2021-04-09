# Jupyter Notebooks

Notebooks for transformation and analysis of MGnify data

Raw data comes from the output of the `lib/download_abundances.py` module.


## Files and directories

* `./transform/` -- Notebooks that change the format of the raw data
  * `go-aggregate-abundances.ipynb`
    * Input the MGnify data downloaded by `lib/download_abundances/by_study.py`
    * Outputs `go-aggregated.tsv`, a single table with columns for the sample/assembly/run ID and every GO term abundance
  * `extract-sample-ids.ipynb`
    * Input the `go-aggregated.tsv` file from above
    * Output `go-aggregated-sample-ids.tsv`, which is all rows from the input file where we have a sample ID. We add additional columns for the Biome ID and the Experiment Type from the downloaded MGnify data.
outputs go-aggregated-samples.tsv -- Take all rows from the a
* `./analyze/` -- Notebooks that run analyses on transformed data
  * `catboost-go-sample-ids.tsv` -- Catboost model to predict Biome from GO abundances and experiment type, using rows from `go-aggregated.tsv` that has sample IDs.
    * Input from `go-aggregated-sample-ids.tsv`
  * `catboost-go-run-ids.tsv` -- The same Catboost analysis as above, but we use the larger training set that has run IDs.
    * Input from `go-aggregated-run-ids.tsv`
* `./unorganized` -- Miscellaneous experimental notebooks that have not yet been organized into the above directories
