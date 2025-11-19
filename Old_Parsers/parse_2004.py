import pdfplumber
import json
import re
import os
import string


# ----------------------------------------
# Helpers
# ----------------------------------------

def safe_int(x):
    if x is None:
        return 0
    try:
        x = str(x).replace(",", "").replace("(", "").replace(")", "").strip()
        if x == "" or x == "-":
            return 0
        return int(float(x))
    except:
        return 0


def safe_float(x):
    if x is None:
        return 0.0
    try:
        x = str(x).replace(",", "").replace("(", "").replace(")", "").strip()
        return float(x)
    except:
        return 0.0


def format_name(n):
    if not n:
        return ""
    n = n.replace("\xa0", " ").strip()
    n = re.sub(r"\(SC\)|\(ST\)", "", n, flags=re.I).strip()
    return string.capwords(n)


# ----------------------------------------
# Template (same as 2024)
# ----------------------------------------

def empty_gender():
    return {"Men": 0, "Women": 0, "Third_Gender": 0, "Total": 0}


def electors_template():
    return {
        "General": empty_gender(),
        "OverSeas": empty_gender(),
        "Service": empty_gender(),
        "Total": empty_gender()
    }


def voters_template():
    return {
        "General": empty_gender(),
        "OverSeas": empty_gender(),
        "Proxy": empty_gender(),
        "Postal": empty_gender(),
        "Total": empty_gender(),
        "Votes Not Counted From CU(s) as Per ECI Instructions": empty_gender(),
        "POLLING PERCENTAGE": {"Men": None, "Women": None, "Third_Gender": None, "Total": 0.0}
    }


def votes_template():
    return {
        "Total Votes Polled On EVM": 0,
        "Total Deducted Votes From EVM": 0,
        "Total Valid Votes polled on EVM": 0,
        "Postal Votes Counted": 0,
        "Postal Votes Deducted": 0,
        "Valid Postal Votes": 0,
        "Total Valid Votes Polled": 0,
        "Test Votes polled On EVM": 0,
        "Votes Polled for 'NOTA'(Including Postal)": 0,
        "Tendered Votes": 0
    }


# -------------------------------------------------
# PARSE SUMMARY PDF (2004)
# -------------------------------------------------

def parse_summary_2004(path):
    results = []

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text or "CONSTITUENCY DATA - SUMMARY" not in text:
                continue

            # Extract state, code, const name, number
            state_m = re.search(r"STATE/UT\s*:\s*([A-Z\s]+)", text)
            code_m = re.search(r"CODE\s*:\s*(S\d+)", text)
            const_m = re.search(r"CONSTITUENCY\s*:\s*([A-Za-z\s\(\)]+)", text)
            no_m = re.search(r"NO\s*:\s*(\d+)", text)

            if not state_m or not code_m or not const_m or not no_m:
                continue

            state = state_m.group(1).strip()
            code = code_m.group(1).strip()
            const_name_raw = const_m.group(1).strip()
            const_name = format_name(const_name_raw)
            const_no = no_m.group(1).strip()

            entry = {
                "ID": f"{code}-{const_no}",
                "State_UT": state,
                "Constituency": const_name,
                "Category": "GENERAL" if "(SC)" not in const_name_raw.upper() and "(ST)" not in const_name_raw.upper()
                           else ("SC" if "(SC)" in const_name_raw.upper() else "ST"),
                "Candidates": [],
                "Electors": electors_template(),
                "Voters": voters_template(),
                "Votes": votes_template(),
                "Polling_Station": {"Number": 0, "Average Electors Per Polling": 0},
                "Dates": [],
                "Result": {
                    "Winner": {"Party": None, "Candidates": None, "Votes": 0},
                    "Runner-Up": {"Party": None, "Candidates": None, "Votes": 0},
                    "Margin": 0
                }
            }

            # ------------------------------
            # Extract Numeric Fields
            # ------------------------------

            # Electors
            g = re.findall(r"GENERAL\s+(\d+)\s+(\d+)\s+(\d+)", text)
            if g:
                men, women, total = g[0]
                entry["Electors"]["General"] = {
                    "Men": safe_int(men),
                    "Women": safe_int(women),
                    "Third_Gender": 0,
                    "Total": safe_int(total)
                }

            # Service
            s = re.findall(r"SERVICE\s+(\d+)\s+(\d+)\s+(\d+)", text)
            if s:
                men, women, total = s[0]
                entry["Electors"]["Service"] = {
                    "Men": safe_int(men),
                    "Women": safe_int(women),
                    "Third_Gender": 0,
                    "Total": safe_int(total)
                }

            # Total electors
            t = re.findall(r"TOTAL\s+(\d+)\s+(\d+)\s+(\d+)", text)
            if t:
                men, women, total = t[0]
                entry["Electors"]["Total"] = {
                    "Men": safe_int(men),
                    "Women": safe_int(women),
                    "Third_Gender": 0,
                    "Total": safe_int(total)
                }

            # Voters GENERAL
            vg = re.findall(r"III\.\s*VOTERS.*?GENERAL\s+(\d+)\s+(\d+)\s+(\d+)", text, re.S)
            if vg:
                men, women, total = vg[0]
                entry["Voters"]["General"]["Men"] = safe_int(men)
                entry["Voters"]["General"]["Women"] = safe_int(women)
                entry["Voters"]["General"]["Total"] = safe_int(total)

            # Proxy
            px = re.findall(r"PROXY\s+(\d+)", text)
            if px:
                entry["Voters"]["Proxy"]["Total"] = safe_int(px[0])

            # Postal
            po = re.findall(r"POSTAL\s+(\d+)", text)
            if po:
                entry["Voters"]["Postal"]["Total"] = safe_int(po[0])

            # Total voters
            tv = re.findall(r"TOTAL\s+(\d+)", text)
            if tv:
                entry["Voters"]["Total"]["Total"] = safe_int(tv[-1])

            # Polling %
            pp = re.findall(r"POLLING PERCENTAGE\s+([\d\.]+)", text)
            if pp:
                entry["Voters"]["POLLING PERCENTAGE"]["Total"] = safe_float(pp[0])

            # Votes
            rej = re.findall(r"REJECTED VOTES.*?(\d+)", text)
            if rej:
                entry["Votes"]["Postal Votes Deducted"] = safe_int(rej[0])

            nret = re.findall(r"NOT RETRIEVED FROM EVM\s+(\d+)", text)
            if nret:
                entry["Votes"]["Total Deducted Votes From EVM"] = safe_int(nret[0])

            valid = re.findall(r"TOTAL VALID VOTES POLLED\s+(\d+)", text)
            if valid:
                entry["Votes"]["Total Valid Votes Polled"] = safe_int(valid[0])

            tend = re.findall(r"TENDERED VOTES\s+(\d+)", text)
            if tend:
                entry["Votes"]["Tendered Votes"] = safe_int(tend[0])

            # Polling stations
            ps = re.findall(r"NUMBER\s*:\s*(\d+)", text)
            if ps:
                entry["Polling_Station"]["Number"] = safe_int(ps[-1])

            avg = re.findall(r"AVERAGE ELECTORS PER POLLING STATION\s+(\d+)", text)
            if avg:
                entry["Polling_Station"]["Average Electors Per Polling"] = safe_int(avg[0])

            # Dates
            dates = re.findall(r"(\d{2}-\d{2}-\d{4})", text)
            entry["Dates"] = dates

            # Result
            win = re.search(r"Winner\s+:\s+([A-Za-z]+)\s+([A-Za-z\s\.]+)\s+(\d+)", text)
            if win:
                entry["Result"]["Winner"]["Party"] = win.group(1)
                entry["Result"]["Winner"]["Candidates"] = format_name(win.group(2))
                entry["Result"]["Winner"]["Votes"] = safe_int(win.group(3))

            ru = re.search(r"Runner up\s+:\s+([A-Za-z]+)\s+([A-Za-z\s\.]+)\s+(\d+)", text)
            if ru:
                entry["Result"]["Runner-Up"]["Party"] = ru.group(1)
                entry["Result"]["Runner-Up"]["Candidates"] = format_name(ru.group(2))
                entry["Result"]["Runner-Up"]["Votes"] = safe_int(ru.group(3))

            # Margin
            mg = re.search(r"MARGIN\s+:\s*(.*?)(\d+)", text)
            if mg:
                entry["Result"]["Margin"] = safe_int(mg.group(2))

            results.append(entry)

    return results


# -------------------------------------------------
# PARSE DETAILED PDF (2004)
# -------------------------------------------------

def parse_detailed_2004(path):
    data = {}

    candidate_re = re.compile(
        r"^\s*(\d+)\.\s+(.+?)\s+(M|F)\s+(\d{1,3})\s+(SC|ST|GEN)\s+([A-Z0-9\(\)]+)\s+(\d+)\s+(\d+)\s+(\d+)$"
    )

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            # detect constituency
            headers = re.findall(r"Constituency\s*:\s*(\d+)\s*\.\s*([A-Za-z\s\(\)]+)", text)
            if not headers:
                continue

            for no, cname_raw in headers:
                cid = f"S01-{no}"
                if cid not in data:
                    data[cid] = []

            # candidate lines
            for line in text.split("\n"):
                m = candidate_re.match(line.strip())
                if m:
                    serial, name, sex, age, cat, party, genv, postv, totalv = m.groups()

                    cand = {
                        "Candidate Name": format_name(name),
                        "Gender": "MALE" if sex == "M" else "FEMALE",
                        "Age": safe_int(age),
                        "Category": cat,
                        "Party Name": party,
                        "Party Symbol": None,
                        "Total Votes Polled In The Constituency": 0,
                        "Valid Votes": 0,
                        "Votes Secured": {
                            "General": safe_int(genv),
                            "Postal": safe_int(postv),
                            "Total": safe_int(totalv)
                        },
                        "% of Votes Secured": {
                            "Over Total Electors In Constituency": 0.0,
                            "Over Total Votes Polled In Constituency": 0.0
                        },
                        "Over Total Valid Votes Polled In Constituency": 0.0,
                        "Total Electors": 0
                    }

                    # the last constituency ID on page
                    last_no = headers[-1][0]
                    cid = f"S01-{last_no}"
                    data[cid].append(cand)

    return data

# -------------------------------------------------
# MERGE SUMMARY + DETAILED
# -------------------------------------------------

def merge_2004(summary, detailed):
    merged = []

    for entry in summary:
        cid = entry["ID"]
        if cid in detailed:
            # Attach candidate list
            entry["Candidates"] = detailed[cid]

            # Compute valid vote percentages
            total_valid = entry["Votes"]["Total Valid Votes Polled"]

            for cand in entry["Candidates"]:
                tv = cand["Votes Secured"]["Total"]
                if total_valid > 0:
                    cand["Over Total Valid Votes Polled In Constituency"] = round(
                        (tv / total_valid) * 100, 2
                    )
                cand["Valid Votes"] = total_valid
                cand["Total Electors"] = entry["Electors"]["Total"]["Total"]

            # Determine Winner + Runner-up
            sorted_cands = sorted(entry["Candidates"], key=lambda x: x["Votes Secured"]["Total"], reverse=True)

            if sorted_cands:
                w = sorted_cands[0]
                entry["Result"]["Winner"] = {
                    "Party": w["Party Name"],
                    "Candidates": w["Candidate Name"],
                    "Votes": w["Votes Secured"]["Total"]
                }

            if len(sorted_cands) > 1:
                r = sorted_cands[1]
                entry["Result"]["Runner-Up"] = {
                    "Party": r["Party Name"],
                    "Candidates": r["Candidate Name"],
                    "Votes": r["Votes Secured"]["Total"]
                }

                entry["Result"]["Margin"] = (
                    sorted_cands[0]["Votes Secured"]["Total"] -
                    sorted_cands[1]["Votes Secured"]["Total"]
                )

        merged.append(entry)

    return merged


# -------------------------------------------------
# MAIN
# -------------------------------------------------

detailed_path = "/mnt/d/IIT_B_Project/SL_NON GIT/pdf_before 2009/detailed/2004_detailed.pdf"
summary_path = "/mnt/d/IIT_B_Project/SL_NON GIT/pdf_before 2009/summary/2004_summary_trimmed.pdf"
output_path = "/mnt/d/IIT_B_Project/SL_NON GIT/parsed_new/parsed_new_2004.json"

summary = parse_summary_2004(summary_path)
detailed = parse_detailed_2004(detailed_path)
merged = merge_2004(summary, detailed)

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(merged, f, indent=4)

print("Saved:", output_path)



