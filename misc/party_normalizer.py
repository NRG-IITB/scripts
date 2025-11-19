import json
import re

INPUT_JSON = "2024_Ganesh.json"
OUTPUT_JSON = "2024_fixed.json"

# Known major party abbreviations
party_map = {
    "Bharatiya Janata Party": "BJP",
    "Indian National Congress": "INC",
    "Aam Aadmi Party": "AAP",
    "Bahujan Samaj Party": "BSP",
    "Communist Party of India": "CPI",
    "Communist Party of India (Marxist)": "CPM",
    "All India Trinamool Congress": "AITC",
    "Nationalist Congress Party": "NCP",
    "Yuvajana Sramika Rythu Congress Party": "YSRCP",
    "Bharat Rashtra Samithi": "BRS",
    "Telangana Rashtra Samithi": "TRS",
    "Samajwadi Party": "SP",
    "Rashtriya Janata Dal": "RJD",
    "Janata Dal (United)": "JDU",
    "Janata Dal (Secular)": "JDS",
    "Dravida Munnetra Kazhagam": "DMK",
    "All India Anna Dravida Munnetra Kazhagam": "AIADMK",
    "All India Majlis-E-Ittehadul Muslimeen": "AIMIM",
    "Biju Janata Dal": "BJD",
    "Zoram People’s Movement": "ZPM",
    "INDEPENDENT": "IND",
    "Independent": "IND"
}

# Auto abbreviation fallback
def auto_abbrev(name):
    words = re.findall(r"[A-Za-z0-9]+", name)
    letters = [w[0].upper() for w in words if len(w) > 2]
    return "".join(letters)

# Load JSON
with open(INPUT_JSON, "r", encoding="utf-8") as f:
    data = json.load(f)

# Fix only winner & runner-up section
for entry in data:
    result = entry.get("Result") or {}

    for key in ["Winner", "Runner-Up"]:
        sec = result.get(key)
        if sec and "Party" in sec:
            pname = sec["Party"]

            if pname in party_map:
                sec["Party"] = party_map[pname]
            else:
                sec["Party"] = auto_abbrev(pname)

# Save output
with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Winner/Runner party names normalized successfully!")
