'''
Script to join constituency names from geo.txt and names.txt
'''
import pandas as pd
import io

geo_text_file = 'geo.txt'
names_text_file = 'names.txt'

with open(geo_text_file, 'r') as f:
    geo_txt_content = f.read()

with open(names_text_file, 'r') as f:
    names_txt_content = f.read()

df_geo = pd.read_csv(io.StringIO(geo_txt_content), header=None, names=['Geo_Name'])
df_names = pd.read_csv(io.StringIO(names_txt_content), header=None, names=['Names_Name'])

df_geo['Geo_Name_Clean'] = df_geo['Geo_Name'].str.strip()
df_names['Names_Name_Clean'] = df_names['Names_Name'].str.strip()

df_joined = pd.merge(
    df_geo, 
    df_names, 
    left_on='Geo_Name_Clean', 
    right_on='Names_Name_Clean', 
    how='outer'
)

df_output = df_joined[[
    'Geo_Name', 
    'Names_Name'
]]

df_output.columns = [
    'Name_from_geo.txt_Source', 
    'Name_from_names.txt_Source'
]
df_output = df_output.fillna('')

csv_output = df_output.to_csv(index=False)
print(csv_output)