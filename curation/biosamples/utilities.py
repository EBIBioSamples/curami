import re
import requests

first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')


def clean_json(json):
    new_json = json
    if isinstance(new_json, dict):
        new_json.pop("_links")
    return new_json


def merge_samples(sample_a, sample_b):
    if sample_a["accession"] != sample_b["accession"]:
        raise Exception("Impossible to merge samples with different accessions")
    return {**clean_json(sample_a), **clean_json(sample_b)}


def is_ok(response):
    return response.status_code == requests.codes.ok


def is_successful(response):
    return ("{:d}".format(response.status_code)).startswith("2")


def is_status(response, code=None):
    if code is None:
        raise ValueError("No code has been provided to the function")
    if isinstance(code, list):
        return response.status_code in code
    return response.status_code == code
