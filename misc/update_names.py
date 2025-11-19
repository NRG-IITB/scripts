'''
Script to update constituency names and IDs in merged.geojson based on joined.csv and 2024.json
'''

import json
import string

def format_name(name):
    parts = name.split('-')
    parts = [string.capwords(part.strip()) for part in parts]
    return '-'.join(parts).replace('&', 'and')

with open('joined.csv', 'r') as f:
    lines = f.readlines()

pairs = []
for l in lines:
    old, new = l.strip().split(',')
    pairs.append((old, new))

with open('merged.geojson', 'r') as f:
    data = json.load(f)

with open('2024.json', 'r') as f:
    election_data = json.load(f)
    ids = {}
    for r in election_data:
        if r['Constituency'] not in ['Aurangabad', 'Hamirpur', 'Maharajganj']:
            ids[r['Constituency']] = r['ID']
        else:
            ids[r['Constituency']] = 'XX-XXX'

for feature in data['features']:
    name = feature['properties']['pc_name']
    for old, new in pairs:
        if name == new:
            feature['properties'] = {'pc_id': ids[old], 'st_name': format_name(feature['properties']['st_name']), 'pc_name': old}
            break

with open('updated_merged.geojson', 'w') as f:
    data_str = json.dumps(data)
    data_str = data_str.replace('{"type": "Feature"', '\n{"type": "Feature"')
    f.write(data_str)