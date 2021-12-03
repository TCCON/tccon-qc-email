#!/usr/bin/env python
from argparse import ArgumentParser
import json
import re


def parse_args():
    p = ArgumentParser(description='Update field names for TCCON DOI metadata JSON files')
    p.add_argument('input_file', help='Original JSON file')
    p.add_argument('output_file', help='Name to give the new JSON file')
    p.add_argument('--indent', type=int, help='Space to indent the output JSON with')

    return vars(p.parse_args())


def convert_ggg2014_to_ggg2020a(input_file, output_file, indent=None):
    with open(input_file) as f:
        metadata = json.load(f)

    # Geolocation top field name changed
    metadata['GeoLocation'] = metadata.pop('geoLocations')

    # Update GGG version number, assume revision 0
    metadata['titles'][0]['title'] = re.sub(
        r'GGG2014.R\d+',
        'GGG2020.R0',
        metadata['titles'][0]['title']
    )

    # May need to check that all names are family, given (i.e. that there is a comma)
    # - Paul's contributor in pasadena was not.

    with open(output_file, 'w') as f:
        json.dump(metadata, f, indent=indent)


if __name__ == '__main__':
    clargs = parse_args()
    convert_ggg2014_to_ggg2020a(**clargs)
