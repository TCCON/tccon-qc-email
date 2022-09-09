import json
import re

def make_bibtex_entries(sites='all'):
    if sites == 'all':
        filter_sites = False
        sites = set()
    else:
        filter_sites = True
        sites = set(sites.split(','))

    # TODO: use the Django settings
    with open('/var/www/tccon-metadata/site_info.json') as f:
        all_site_info = json.load(f)

    bibtex_strings = []
    for site_id, site_info in all_site_info.items():
        if filter_sites and site_id not in sites:
            continue

        bibtex_key = make_bibtex_key(site_id, site_info)

        citation = site_info.get('data_reference', '')
        if len(citation) == 0:
            bibtex_strings.append(f'% Site with id "{site_id}" has not provided a data reference. Please ask them to do so!')
            continue

        try:
            bibtex_strings.append(parse_data_citation(citation, bibtex_key))
        except:
            bibtex_strings.append(f'% Sorry, was not able to produce a citation for site "{site_id}"')

    return '\n\n'.join(bibtex_strings)


def make_bibtex_table(sites='all', citation_cmd='citet'):
    if sites == 'all':
        filter_sites = False
        sites = set()
    else:
        filter_sites = True
        sites = set(sites.split(','))

    table_rows = ['Site ID & Site Name & Location & Data Citation']

    # TODO: use the Django settings
    with open('/var/www/tccon-metadata/site_info.json') as f:
        all_site_info = json.load(f)

    for site_id, site_info in all_site_info.items():
        if filter_sites and site_id not in sites:
            continue

        site_name = site_info.get('long_name', '(undefined)')
        location = site_info.get('location', '(undefined)')
        bib_key = make_bibtex_key(site_id, site_info)
        citation = f'\\{citation_cmd}{{{bib_key}}}'
        table_rows.append(f'{site_id} & {site_name} & {location} & {citation}')

    return ' \\\\\n'.join(table_rows)
    

def parse_data_citation(citation_str, bibtex_key, as_dict=False):
    # Assume format: "Authors. Year. Title doi"
    regex = re.match(r'(?P<authors>.+)\. (?P<year>\d{4}). (?P<title>.+) ((http|https)://)?(doi\.org/)?(?P<doi>10\..+)$', citation_str)
    info = {
        'author': parse_authors(regex.group('authors')),
        'year': regex.group('year'),
        'title': regex.group('title'),
        'doi': regex.group('doi')
    }

    if as_dict:
        return info
    else:
        return f"""@misc{{{bibtex_key},
    author = {{{" and ".join(info["author"])}}},
    title = {{{info["title"]}}},
    year = {{{info["year"]}}},
    doi = {{{info["doi"]}}}
}}"""


def make_bibtex_key(site_id, site_info):
    try:
        return f"{site_info['long_name']}_data"
    except KeyError:
        return f'{site_id}_tccon_data'


def parse_authors(authors):
    # TODO: deal with "and" in the author list?
    authors_in = authors.split(',')
    authors_out = []

    i = 0
    while i < len(authors_in):
        author = authors_in[i].strip()
        if len(author.split()) > 1:
            # Assume that this was written as "First Last" - i.e., no comman in the author name. Add it directly.
            authors_out.append(author)
            i += 1
        else:
            # Assume that this author was written as "Last, First" such that we need to get the next split value and
            # add it to this one
            authors_out.append(f'{authors_in[i+1].strip()} {author}')
            i += 2

    return authors_out


if __name__ == '__main__':
    print(make_bibtex_entries())
    # print(make_bibtex_table())
