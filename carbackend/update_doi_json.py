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

    # Convert from just "name" to that plus family and given name, if that's sensible
    for creator in metadata['creators']:
        convert_name(creator, True, 'creator')
    for contributor in metadata['contributors']:
        is_not_person = contributor['contributorType'] in {'HostingInstitution', 'RegistrationAgency', 'RegistrationAuthority', 'ResearchGroup'}
        convert_name(contributor, not is_not_person, 'contributor')

    with open(output_file, 'w') as f:
        json.dump(metadata, f, indent=indent)


def convert_name(name_dict, is_person, category):
    name = name_dict.pop('name')
    if is_person:
        if name.count(',') != 1:
            print(f'Name {name} is not in expected format')
            given = input('Type the given name: ')
            family = input('Type the family name: ')
        else:
            family, given = [x.strip() for x in name.split(',')]

        name_dict[f'{category}Name'] = f'{family}, {given}'
        name_dict['givenName'] = given
        name_dict['familyName'] = family
    else:
        name_dict[f'{category}Name'] = name



if __name__ == '__main__':
    clargs = parse_args()
    convert_ggg2014_to_ggg2020a(**clargs)
