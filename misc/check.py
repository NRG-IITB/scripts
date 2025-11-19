import json
import csv
import os

# ---------------- CONFIG ----------------
folder = "/mnt/c/Users/dell/Desktop/scripts new/Final_jsons/Final"  # update if needed
file_a = "2024_Ganesh.json"
file_b = "2024_final_name_corrected.json"

output_csv = os.path.join(folder, "id_comparison_report.csv")

# ---------------- HELPERS ----------------
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ---------------- LOAD BOTH FILES ----------------
data_a = load_json(os.path.join(folder, file_a))
data_b = load_json(os.path.join(folder, file_b))

# Build maps: ID → Constituency
map_a = {entry["ID"]: entry["Constituency"].strip() for entry in data_a}
map_b = {entry["ID"]: entry["Constituency"].strip() for entry in data_b}

print(f"Loaded {len(map_a)} items from {file_a}")
print(f"Loaded {len(map_b)} items from {file_b}\n")

# ---------------- COMPARE ----------------
rows = [["ID", "Constituency_Ganesh", "Constituency_Final", "Status"]]

all_ids = set(map_a.keys()) | set(map_b.keys())

for cid in sorted(all_ids):
    name_a = map_a.get(cid, "")
    name_b = map_b.get(cid, "")

    if cid in map_a and cid in map_b:
        # ID exists in both → check names
        if name_a == name_b:
            rows.append([cid, name_a, name_b, "MATCH"])
        else:
            rows.append([cid, name_a, name_b, "NAME MISMATCH"])
    elif cid in map_a and cid not in map_b:
        rows.append([cid, name_a, "", "MISSING IN FINAL"])
    elif cid not in map_a and cid in map_b:
        rows.append([cid, "", name_b, "MISSING IN GANESH"])

# ---------------- SAVE REPORT ----------------
with open(output_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerows(rows)

print(f"📊 ID comparison report saved to: {output_csv}")
print("✅ Done — NO modifications made to JSON files.")
