import argparse
import json
import logging
import os
import pathlib
import requests
import re

logging.basicConfig(format='%(levelname)s:%(message)s', level=os.environ.get('LOGLEVEL', 'DEBUG'))


def main(config: dict):
    _create_dirs(config)
    # _download_studies(config)
    _download_samples(config)


def _download_samples(config: dict) -> None:
    # Iterate over every sample and jump to its latest analysis
    samples_url = config['samples_url']
    while True:
        resp = requests.get(samples_url).json()
        data = resp['data']
        logging.info(f"Page {resp['meta']['pagination']['page']}:")
        for sample_json in data:
            _init_sample(sample_json, config)
        break


def _init_sample(sample_json: dict, config: dict) -> None:
    sample_path = os.path.join(config['samples_dir'], sample_json['id'])
    pathlib.Path(sample_path).mkdir(parents=True, exist_ok=True)
    sample_json_path = os.path.join(sample_path, 'sample.json')
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


def _download_studies(config: dict) -> None:
    logging.info('Downloading studies')
    studies_url = config['studies_url']
    while True:
        resp = requests.get(studies_url).json()
        data = resp['data']
        logging.info(f"Page {resp['meta']['pagination']['page']}:")
        for study_json in data:
            _init_study(study_json, config)
        # Next page
        studies_url = resp['links']['next']
        if studies_url is None:
            logging.info("Reached the last page")
            return


def _init_study(study_json: dict, config: dict) -> None:
    """
    Initialize files and make additional requests for the given study JSON
    """
    _id = study_json['id']
    (analyses_json, samples_json) = _fetch_study_extras(study_json, config)
    if not _is_correct_experiment_type(study_json, analyses_json, config):
        logging.info(f"Study {_id} is not {config['experiment_type']}, skipping")
        return
    _init_study_files(study_json, analyses_json, samples_json, config)
    logging.info(f"Writing study files for {_id}")
    dl_url = study_json['relationships']['downloads']['links']['related']
    downloads = requests.get(dl_url).json()
    tsv_url = None
    tsv_filename = None
    for dl in downloads['data']:
        dl_id = dl['id']
        # Match for our desired file based on a regex against the download ID
        pattern = r'^.+' + config['file_substring'] + r'.+\.tsv$'
        match = re.search(pattern, dl_id)
        if not match:
            continue
        tsv_url = dl['links']['self']
        tsv_filename = dl_id
        logging.info(f"Found a download for {_id}: {tsv_filename}")
        dl_path = os.path.join(config['studies_dir'], _id, tsv_filename)
        # Check if already downloaded
        if not os.path.isfile(dl_path):
            # Download the file
            logging.info(f"Starting download for {_id}")
            resp = requests.get(tsv_url)
            with open(dl_path, 'wb') as fd:
                fd.write(resp.content)
            logging.info(f"Download finished for {_id}")
        else:
            logging.info(f"File already exists at {dl_path}")


def _fetch_study_extras(study_json: dict, config: dict):
    """
    Fetch additional data surrounding the study
    """
    rels = study_json['relationships']
    analyses_url = rels['analyses']['links']['related']
    analyses_json = requests.get(analyses_url).json()
    samples_url = rels['samples']['links']['related']
    samples_json = requests.get(samples_url).json()
    return (analyses_json, samples_json)


def _is_correct_experiment_type(study_json: dict, analyses_json: dict, config: dict) -> bool:
    """
    Check if the study is the correct experiment type (from the config)
    """
    if config['any_experiment_type']:
        return True
    data = analyses_json['data']
    for analysis in data:
        exp_type = analysis['attributes']['experiment-type']
        if exp_type != config['experiment_type']:
            return False
    return True


def _init_study_files(study_json: dict, analyses_json, samples_json: dict, config: dict) -> None:
    _id = study_json['id']
    dir_path = os.path.join(config['studies_dir'], _id)
    study_json_path = os.path.join(dir_path, 'study.json')
    pathlib.Path(dir_path).mkdir(parents=True, exist_ok=True)
    with open(study_json_path, 'w') as fd:
        json.dump(study_json, fd)
    # Save the analyses and biomes as well
    analyses_path = os.path.join(dir_path, 'analyses.json')
    with open(analyses_path, 'w') as fd:
        json.dump(analyses_json, fd)
    samples_path = os.path.join(dir_path, 'samples.json')
    with open(samples_path, 'w') as fd:
        json.dump(samples_json, fd)


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
