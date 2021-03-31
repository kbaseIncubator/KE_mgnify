"""
Download MGnify data by iterating over samples.
"""
import argparse
import json
import logging
import os
import pathlib
import requests

logging.basicConfig(format='%(levelname)s:%(message)s', level=os.environ.get('LOGLEVEL', 'DEBUG'))


def main(config: dict):
    _create_dirs(config)
    _download_samples(config)


def _download_samples(config: dict) -> None:
    # Iterate over every sample and jump to its latest analysis
    samples_url = config['samples_url']
    while True:
        resp = requests.get(samples_url).json()
        data = resp['data']
        logging.info(f"---------- Page {resp['meta']['pagination']['page']} ----------")
        for sample_json in data:
            _init_sample(sample_json, config)
        # Next page
        samples_url = resp['links']['next']
        if samples_url is None:
            logging.info("Reached the last page")
            return


def _init_sample(sample_json: dict, config: dict) -> None:
    sample_path = os.path.join(config['samples_dir'], sample_json['id'])
    pathlib.Path(sample_path).mkdir(parents=True, exist_ok=True)
    sample_json_path = os.path.join(sample_path, 'sample.json')
    if os.path.exists(sample_json_path):
        logging.info(f"Already downloaded {sample_json['id']}, continuing")
        return
    with open(sample_json_path, 'w') as fd:
        json.dump(sample_json, fd)
        logging.info(f"Wrote to {sample_json_path}")
    # Fetch the runs in order to find the latest analysis
    runs_url = sample_json['relationships']['runs']['links']['related']
    runs = requests.get(runs_url).json()['data']
    if len(runs) == 0:
        logging.info("Sample has no runs, skipping")
        return
    run = runs[0]
    # Fetch the analysis for the latest run
    analysis_url = run['relationships']['analyses']['links']['related']
    analyses = requests.get(analysis_url).json()['data']
    if len(analyses) == 0:
        logging.info(f"Sample {sample_json['id']} has no analyses, continuing")
        return
    analysis = analyses[0]
    analysis_path = os.path.join(sample_path, 'analysis.json')
    with open(analysis_path, 'w') as fd:
        json.dump(analysis, fd)
        logging.info(f"Wrote to {analysis_path}")
    analysis_status = analysis['attributes']['analysis-status']
    if analysis_status == 'failed':
        logging.info("Analysis status is 'failed', continuing")
        return
    # Download the GO abundance table
    go_url = analysis['relationships']['go-terms']['links']['related']
    go_terms = requests.get(go_url).json()
    go_path = os.path.join(sample_path, 'go-terms.json')
    with open(go_path, 'w') as fd:
        json.dump(go_terms, fd)
        logging.info(f"Wrote GO term abundance to {go_path}")
    # Download the taxonomy-SSU data
    tax_ssu_url = analysis['relationships']['taxonomy-ssu']['links']['related']
    tax_ssu = requests.get(tax_ssu_url).json()
    tax_ssu_path = os.path.join(sample_path, 'taxonomy-ssu.json')
    with open(tax_ssu_path, 'w') as fd:
        json.dump(tax_ssu, fd)
        logging.info(f"Wrote taxonomy SSU data to {tax_ssu_path}")


def _create_dirs(config):
    # dirs = ('base_dir', 'studies_dir')
    dirs = ('base_dir', 'samples_dir')
    for name in dirs:
        path = config[name]
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)


def _init_config(args):
    api_url = os.environ.get('API_URL', "https://www.ebi.ac.uk/metagenomics/api/v1").rstrip('/')
    base_urls = requests.get(api_url).json()['data']
    print(base_urls)
    conf = {
            'base_dir': args.dest,
            'studies_dir': os.path.join(args.dest, 'studies'),
            'samples_dir': os.path.join(args.dest, 'samples'),
            'api_url': api_url,
            'studies_url': base_urls['studies'],
            'samples_url': base_urls['samples'],
            'experiment_type': os.environ.get('EXPERIMENT_TYPE', 'amplicon'),
            'file_substring': os.environ.get('FILE_SUBSTRING', 'GO_abundances'),
            'any_experiment_type': os.environ.get('ANY_EXPERIMENT') is not None,
    }
    logging.info(f"Config is:\n{json.dumps(conf, indent=2)}")
    return conf


def _init_parser():
    parser = argparse.ArgumentParser(
        description='Download abundance tables for all studies'
    )
    parser.add_argument('--dest', '-d', help='destination directory path', default='./data/', type=str)
    return parser


if __name__ == '__main__':
    parser = _init_parser()
    args = parser.parse_args()
    config = _init_config(args)
    main(config)
