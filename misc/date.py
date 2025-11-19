import pdfplumber
import re
import pandas as pd

PDF_FILE = "2009_summary.pdf"
OUT_TXT = "polling_dates_only.txt"
OUT_CSV = "polling_dates_only.csv"

# Regex patterns
state_re = re.compile(r"State/UT\s*:?\s*([A-Za-z0-9]+)", re.IGNORECASE)
fallback_state = re.compile(r"Code\s*:?\s*(S\d{1,2}|U\d{1,2}|[A-Za-z]\d{1,2})", re.IGNORECASE)

no_re = re.compile(r"No\.?\s*:?\s*(\d{1,3})", re.IGNORECASE)
poll_re = re.compile(r"(\d{1,2})-([A-Za-z]{3})-(\d{4})")

# Month mapping
month_map = {
    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"
}

records = []
seen = set()

def convert_date(day, mon, year):
    """Convert 16-Apr-2009 → 16/04/2009"""
    return f"{day.zfill(2)}/{month_map[mon]}/{year}"

with pdfplumber.open(PDF_FILE) as pdf:
    for page_num, page in enumerate(pdf.pages, start=1):
        text = page.extract_text()
        if not text:
            continue

        # ---- Extract state ----
        sm = state_re.search(text) or fallback_state.search(text)
        if not sm:
            continue
        state_code = sm.group(1).strip().upper()  # S03

        # ---- Extract constituency number ----
        nm = no_re.search(text)
        if not nm:
            continue
        cnum = int(nm.group(1))

        # ID = S03-1 (no padding)
        cid = f"{state_code}-{cnum}"

        # ---- Extract polling date ----
        dm = poll_re.search(text)
        if not dm:
            continue

        day, mon, year = dm.group(1), dm.group(2), dm.group(3)
        polling = convert_date(day, mon, year)

        # ---- Dedupe ----
        if cid not in seen:
            seen.add(cid)
            records.append({"const_id": cid, "polling_date": polling})

# ---- To DataFrame ----
df = pd.DataFrame(records)

# Sort properly
def sort_key(cid):
    prefix, num = cid.split("-")
    return (prefix, int(num))

df = df.sort_values(by="const_id", key=lambda x: x.map(sort_key)).reset_index(drop=True)

# ---- Save TXT ----
with open(OUT_TXT, "w") as f:
    for _, row in df.iterrows():
        f.write(f"{row['const_id']}: {row['polling_date']}\n")

# ---- Save CSV ----
df.to_csv(OUT_CSV, index=False)

print(f"Saved {len(df)} entries.")
print(f"TXT -> {OUT_TXT}")
print(f"CSV -> {OUT_CSV}")
