#!/usr/bin/env python3
from argparse import ArgumentParser
import django
import json
import os
import sys

my_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(my_dir, 'carbackend'))
if os.path.exists(os.path.join(my_dir, 'carbackend', 'carbackend', 'settings_local.py')):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carbackend.settings_local')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carbackend.settings')
django.setup()

from qcform.models import SiteReviewers


def row_to_dict(r):
    return {
        'editor': user_to_string(r.editor),
        'reviewer1': user_to_string(r.reviewer1),
        'reviewer2': user_to_string(r.reviewer2),
    }


def user_to_string(user):
    username = user.username
    firstname = user.first_name
    lastname = user.last_name
    if firstname and lastname:
        return f'{firstname} {lastname}'
    else:
        return username


def get_all_reviewers():
    rows = SiteReviewers.objects.all()
    return {r.site: row_to_dict(r) for r in rows}


def get_site_reviewers(site):
    row = SiteReviewers.objects.get(site=site)
    return row_to_dict(row)


def reviewers_as_json(site=None):
    if site:
        reviewers = get_site_reviewers(site)
    else:
        reviewers = get_all_reviewers()

    print(json.dumps(reviewers))


def reviewers_as_csv(site=None):
    reviewers = get_all_reviewers()
    key_order = ['editor', 'reviewer1', 'reviewer2']
    print('site,' + ','.join(key_order))
    for key, row in reviewers.items():
        if site is None or key == site:
            values = ','.join(row[k] for k in key_order)
            print(f'{key},{values}')


def main():
    p = ArgumentParser(description='Retriever editor/reviewer assignments from the CAR backend database')
    p.add_argument('site', nargs='?', help='Optional two-letter site ID of the site to retrieve information for.')
    p.add_argument('-f', '--format', choices=('json', 'csv'), default='json',
                   help='Which format to print the results as. Default is %(default)s.')

    clargs = p.parse_args()
    if clargs.format == 'json':
        reviewers_as_json(clargs.site)
    elif clargs.format == 'csv':
        reviewers_as_csv(clargs.site)
    else:
        print(f'ERROR: Unknown format: {clargs.format}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
