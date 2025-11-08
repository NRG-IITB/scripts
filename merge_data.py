import json

ROOT = 'parsed/data'
YEARS = ['2009', '2014', '2019', '2024']

data = {}
for year in YEARS:
    with open(f'{ROOT}/{year}.json', 'r') as f:
        data[year] = json.load(f)

ids = []
for pc in data[YEARS[-1]]:
    ids.append(pc['ID'])

merged_data = []

for id in ids:
    entry = {'ID': id}
    entry['Constituency'] = data[YEARS[-1]][ids.index(id)]['Constituency']
    entry['State_UT'] = data[YEARS[-1]][ids.index(id)]['State_UT']
    for year in YEARS:
        for pc in data[year]:
            if pc['ID'] == id:
                # delete ID, Constituency, State_UT to avoid redundancy
                tmp = pc.copy()
                del tmp['ID']
                del tmp['Constituency']
                del tmp['State_UT']
                entry[year] = tmp
                break
    merged_data.append(entry)

with open(f'{ROOT}/merged_data.json', 'w') as f:
    json.dump(merged_data, f, indent=4)