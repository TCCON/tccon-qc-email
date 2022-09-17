from argparse import ArgumentParser
import json
from pathlib import Path
import requests


def grid_to_ror(grid):
    # We manually handle some incorrect/redundant GRID Ids
    if grid == "grid.451078.f":
        ror = "https://ror.org/00hm6j694"
    elif grid == 'grid.5805.8':
        ror = "https://ror.org/02en5vm52"
    else:
        url = f"https://api.ror.org/organizations?query.advanced=external_ids.GRID.all:{grid}"
        results = requests.get(url)
        ror = results.json()["items"][0]["id"]
    return ror.split('/')[-1]


def convert_jsons(json_files, out_dir):
    out_dir = Path(out_dir)
    for json_file in json_files:
        json_file = Path(json_file)
        if json_file.is_symlink():
            print(f'Skipping symlink {json_file.name}')
            continue
        else:
            print(f'Updating {json_file.name}')

        with open(json_file) as f:
            info = json.load(f)

        if 'FundingReference' in info:
            funders = info['FundingReference']
        elif 'fundingReferences' in info:
            funders = info['fundingReferences']
        else:
            print(f'  Warning: {json_file.name} had none of the expected keys for funders')
            funders = []

        for i, funder in enumerate(funders, start=1):
            if funder.get('funderIdentifierType', '').upper() == 'GRID':
                grid = funder['funderIdentifier']
                ror = grid_to_ror(grid)
                funder['funderIdentifier'] = ror
                funder['funderIdentifierType'] = 'ROR'
                print(f'  Changed funder {i} GRID {grid} to ROR {ror}')

        for i, contrib in enumerate(info.get('contributors', []), start=1):
            for identifier in contrib.get('nameIdentifiers', []):
                if identifier.get('nameIdentifierScheme', '').upper() == 'GRID':
                    grid = identifier['nameIdentifier']
                    ror = grid_to_ror(grid)
                    identifier['nameIdentifier'] = ror
                    identifier['nameIdentifierScheme'] = 'ROR'
                    print(f'  Changed contributor {i} GRID {grid} to ROR {ror}')

        with open(out_dir / json_file.name, 'w') as f:
            json.dump(info, f, indent=2, ensure_ascii=False)


def main():
    p = ArgumentParser(description='Convert GRID Funding IDs to ROR IDs')
    p.add_argument('json_files', nargs='+', help='The DOI metadata JSON files to convert. Note: symlinks are skipped.')
    p.add_argument('-o', '--out-dir', required=True, help='Directory to output the modified files to')

    clargs = vars(p.parse_args())
    convert_jsons(**clargs)


if __name__ == '__main__':
    main()
