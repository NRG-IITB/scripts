import json

# ---- INPUT FILES ----
JSON_INPUT = "2009_final.json"                # your big JSON file
DATE_FILE = "polling_dates_only.txt"          # S01-1: 16/04/2009
JSON_OUTPUT = "final_data_with_dates.json"    # output file


# ---- STEP 1: LOAD DATE MAP ----
date_map = {}
with open(DATE_FILE, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or ":" not in line:
            continue
        
        # Format: S03-1: 16/04/2009
        parts = line.split(":")
        cid = parts[0].strip()
        date = parts[1].strip()
        date_map[cid] = date


# ---- STEP 2: LOAD JSON DATA ----
with open(JSON_INPUT, "r", encoding="utf-8") as f:
    data = json.load(f)


# ---- STEP 3: APPLY DATES ----
for entry in data:
    cid = entry.get("ID")

    if cid in date_map:
        # Dates field becomes ["DD/MM/YYYY"]
        entry["Dates"] = [date_map[cid]]
    else:
        # Keep as empty list if not found
        entry["Dates"] = []


# ---- STEP 4: SAVE OUTPUT ----
with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Completed. Filled dates for", len(data), "entries.")
print("Output saved to:", JSON_OUTPUT)
