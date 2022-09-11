from argparse import ArgumentParser
import json
from pathlib import Path

p = ArgumentParser(description='Copy the "location" field of the site_info.json file to a new "short_location" field')
p.add_argument('site_info_file', help='Path to the site_info.json file')
p.add_argument('new_file', help='Path to where to save the new file; cannot be the same as the input file')
clargs = p.parse_args()


orig_file = Path(clargs.site_info_file)
new_file = Path(clargs.new_file)

if not orig_file.exists():
    raise IOError(f'Given original file {orig_file} does not exist')
if new_file.exists():
    raise IOError(f'Given output location {new_file} exists, overwriting not allowed')

with open(orig_file) as f:
    site_info = json.load(f)


for site_id, info in site_info.items():
    loc = info.get('location')
    if 'short_location' not in info and len(loc) > 32:
        print(f'Note: {site_id} location exceeds 32 characters, recommend truncating.')
    info.setdefault('short_location', loc)


with open(new_file, 'w') as f:
    json.dump(site_info, f, indent=2, ensure_ascii=False)

print(f'Saved updated file to {new_file}')
