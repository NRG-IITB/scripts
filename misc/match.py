import os
import json
import difflib
import csv

# ---------------- CONFIG ----------------
folder = r"C:\Users\dell\Desktop\scripts new\Final_jsons\final"  # your JSON folder
years = ["2014"]
output_csv = os.path.join(folder, "mapping_report.csv")

# Auto-detect base reference JSON
base_file = None
if os.path.exists(os.path.join(folder, "2024_Ganesh.json")):
    base_file = "2024_Ganesh.json"
elif os.path.exists(os.path.join(folder, "2024.json")):
    base_file = "2024.json"
else:
    raise FileNotFoundError("❌ Neither 2024_Ganesh.json nor 2024.json found in folder!")

print(f"✅ Using {base_file} as reference file.\n")

# ---------------- HELPERS ----------------
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ---------------- LOAD BASE YEAR ----------------
base_data = load_json(os.path.join(folder, base_file))
base_map = {entry["Constituency"].strip().upper(): entry["ID"] for entry in base_data}
print(f"📘 Loaded {len(base_map)} constituencies from {base_file}\n")

# ---------------- PROCESS OTHER YEARS ----------------
report_rows = [["Year", "Constituency", "Old_ID", "New_ID", "Match_Type"]]

for year in years:
    filename = f"{year}_check.json"
    path = os.path.join(folder, filename)

    if not os.path.exists(path):
        print(f"⚠️ Skipping {year}: {filename} not found")
        continue

    data = load_json(path)
    print(f"🔹 Processing {year}: {len(data)} constituencies")

    unmatched = []
    updated_data = []

    for entry in data:
        name_key = entry["Constituency"].strip().upper()
        old_id = entry.get("ID")
        new_id = None
        match_type = "Unmatched"

        # 1️⃣ Exact match
        if name_key in base_map:
            new_id = base_map[name_key]
            match_type = "Exact"
        else:
            # 2️⃣ Fuzzy match (for small name variations)
            matches = difflib.get_close_matches(name_key, base_map.keys(), n=1, cutoff=0.85)
            if matches:
                new_id = base_map[matches[0]]
                match_type = "Fuzzy"

        # 3️⃣ Update ID only if matched
        if new_id:
            entry["ID"] = new_id
        else:
            unmatched.append(entry["Constituency"])

        # 4️⃣ Telangana rule
        if entry.get("ID", "").startswith("S29-"):
            entry["State_UT"] = "Telangana"

        updated_data.append(entry)
        report_rows.append([year, entry["Constituency"], old_id or "", new_id or "", match_type])

    # Save updated JSON with identical structure
    out_path = os.path.join(folder, f"{year}_check copy.json")
    save_json(updated_data, out_path)
    print(f"💾 Saved {year}_mapped.json ({len(unmatched)} unmatched)\n")

# ---------------- SAVE CSV REPORT ----------------
with open(output_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerows(report_rows)

print(f"📊 Mapping report saved to: {output_csv}")
print("✅ JSON structure preserved — only 'ID' and 'State_UT' updated where needed.\n")
