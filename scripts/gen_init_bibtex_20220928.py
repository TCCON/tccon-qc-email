from argparse import ArgumentParser
import json
from pylatexenc.latexencode import unicode_to_latex
from pathlib import Path
import re

def make_bibtex_entries(site_info_file, output_dir, sites='all'):
    output_dir = Path(output_dir)
    if sites == 'all':
        filter_sites = False
        sites = set()
    else:
        filter_sites = True
        sites = set(sites.split(','))

    # TODO: use the Django settings
    with open(site_info_file) as f:
        all_site_info = json.load(f)

    for site_id, site_info in all_site_info.items():
        if filter_sites and site_id not in sites:
            continue

        bibtex_json = {'dataref': dict(bibtex_type='misc', doi_as_url=True, howaccessed='', note='')}

        citation = site_info.get('data_reference', '')
        if len(citation) == 0:
            continue

        try:
            bibtex_json['dataref'].update(parse_data_citation(citation, bibtex_key=None))
        except Exception as e:
            print(f'Sorry, was not able to produce a citation for site "{site_id}". Error was "{e}"')
            continue

        with open(output_dir / f'{site_id}_bibtex_citations.json', 'w') as f:
            json.dump(bibtex_json, f, indent=2, ensure_ascii=False)

def parse_data_citation(citation_str, bibtex_key, as_dict=True):
    # Assume format: "Authors. Year. Title doi"
    regex = re.match(r'(?P<authors>.+)\. (?P<year>\d{4}). (?P<title>.+) ((http|https)://)?(doi\.org/)?(?P<doi>10\..+)$', citation_str)
    info = {
        'author': parse_authors(unicode_to_latex(regex.group('authors'))),
        'year': regex.group('year'),
        'title': regex.group('title'),
        'doi': regex.group('doi')
    }

    if as_dict:
        info['author'] = ' and '.join(info['author'])
        return info
    else:
        return f"""@misc{{{bibtex_key},
    author = {{{" and ".join(info["author"])}}},
    title = {{{info["title"]}}},
    year = {{{info["year"]}}},
    doi = {{{info["doi"]}}}
}}"""


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
    p = ArgumentParser('Generate BibTeX JSON files with the data references based on an existing site info file')
    p.add_argument('site_info_file', help='The site_info.json file to read the original citations from.')
    p.add_argument('output_dir', help='The directory to output the JSON files to')

    clargs = vars(p.parse_args())
    make_bibtex_entries(**clargs)
