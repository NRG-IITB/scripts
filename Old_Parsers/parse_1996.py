import pdfplumber
import re
import json
import string


def safe_int(x):
    try:
        return int(str(x).replace(",", "").strip())
    except:
        return 0

def safe_float(x):
    try:
        return float(str(x).replace("%", "").strip())
    except:
        return 0.0

def cap(s):
    return string.capwords(s.replace("\xa0", " ").strip())


# ============================================================
# ===============  SUMMARY PARSER (1996) ======================
# ============================================================

def parse_summary_1996(path):
    results = []

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            if "CONSTITUENCY DATA - SUMMARY" not in text:
                continue

            # Basic fields
            state = re.search(r"STATE/UT\s*:\s*([A-Za-z\s]+)", text)
            code = re.search(r"CODE\s*:\s*(S\d+)", text)
            cname = re.search(r"CONSTITUENCY\s*:\s*([A-Za-z\s\(\)]+)", text)
            cno = re.search(r"NO\s*:\s*(\d+)", text)

            if not (state and code and cname and cno):
                continue

            state_name = state.group(1).strip()
            code_val = code.group(1)
            raw_name = cname.group(1).strip()
            name = cap(raw_name)
            no = cno.group(1)

            entry = {
                "ID": f"{code_val}-{no}",
                "State_UT": state_name,
                "Constituency": name,
                "Category": "GENERAL",
                "Candidates": [],

                "Electors": {
                    "General": {"Men": 0, "Women": 0, "Third_Gender": 0, "Total": 0},
                    "Service": {"Men": 0, "Women": 0, "Third_Gender": 0, "Total": 0},
                    "Total": {"Men": 0, "Women": 0, "Third_Gender": 0, "Total": 0},
                },

                "Voters": {
                    "General": {"Men": 0, "Women": 0, "Third_Gender": 0, "Total": 0},
                    "Postal": {"Total": 0},
                    "Total": {"Total": 0},
                    "POLLING PERCENTAGE": {
                        "Men": None, "Women": None,
                        "Third_Gender": None, "Total": 0.0
                    }
                },

                "Votes": {
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
                },

                "Polling_Station": {"Number": 0, "Average Electors Per Polling": 0},

                "Dates": [],

                "Result": {
                    "Winner": {"Party": None, "Candidates": None, "Votes": 0},
                    "Runner-Up": {"Party": None, "Candidates": None, "Votes": 0},
                    "Margin": 0
                }
            }

            # ELECTORS
            eg = re.findall(r"GENERAL\s+(\d+)\s+(\d+)\s+(\d+)", text)
            if eg:
                men, women, total = eg[0]
                entry["Electors"]["General"] = {
                    "Men": safe_int(men),
                    "Women": safe_int(women),
                    "Third_Gender": 0,
                    "Total": safe_int(total)
                }

            es = re.findall(r"SERVICE\s+(\d+)\s+(\d+)\s+(\d+)", text)
            if es:
                men, women, total = es[0]
                entry["Electors"]["Service"] = {
                    "Men": safe_int(men),
                    "Women": safe_int(women),
                    "Third_Gender": 0,
                    "Total": safe_int(total)
                }

            et = re.findall(r"TOTAL\s+(\d+)\s+(\d+)\s+(\d+)", text)
            if et:
                men, women, total = et[0]
                entry["Electors"]["Total"] = {
                    "Men": safe_int(men),
                    "Women": safe_int(women),
                    "Third_Gender": 0,
                    "Total": safe_int(total)
                }

            # VOTERS
            vg = re.findall(r"ELECTORS WHO VOTED.*?GENERAL\s+(\d+)\s+(\d+)\s+(\d+)", text, re.S)
            if vg:
                men, women, total = vg[0]
                entry["Voters"]["General"] = {
                    "Men": safe_int(men),
                    "Women": safe_int(women),
                    "Third_Gender": 0,
                    "Total": safe_int(total)
                }

            vp = re.findall(r"POSTAL\s+(\d+)", text)
            if vp:
                entry["Voters"]["Postal"]["Total"] = safe_int(vp[0])

            vt = re.findall(r"TOTAL\s+(\d+)", text)
            if vt:
                entry["Voters"]["Total"]["Total"] = safe_int(vt[-1])

            pp = re.findall(r"POLL(?:ING)? PERCENTAGE\s*[: ]\s*([\d\.]+)", text)
            if pp:
                entry["Voters"]["POLLING PERCENTAGE"]["Total"] = safe_float(pp[0])

            # VOTES
            polled = re.search(r"POLLED\s+(\d+)", text)
            if polled:
                entry["Votes"]["Total Votes Polled On EVM"] = safe_int(polled.group(1))

            valid = re.search(r"VALID\s+(\d+)", text)
            if valid:
                entry["Votes"]["Total Valid Votes Polled"] = safe_int(valid.group(1))

            rej = re.search(r"REJECTED\s+(\d+)", text)
            if rej:
                entry["Votes"]["Postal Votes Deducted"] = safe_int(rej.group(1))

            tend = re.search(r"TENDERED\s+(\d+)", text)
            if tend:
                entry["Votes"]["Tendered Votes"] = safe_int(tend.group(1))

            # POLLING STATIONS
            ps = re.search(r"NUMBER\s*:\s*(\d+)", text)
            if ps:
                entry["Polling_Station"]["Number"] = safe_int(ps.group(1))

            avg = re.search(r"AVERAGE ELECTORS PER POLLING STATION\s*[: ]\s*(\d+)", text)
            if avg:
                entry["Polling_Station"]["Average Electors Per Polling"] = safe_int(avg.group(1))

            # DATES
            entry["Dates"] = re.findall(r"(\d{2}-\d{2}-\d{4})", text)

            # RESULT
            win = re.search(r"Winner.*?\n([A-Za-z]+)\s+(.+?)\s+(\d+)", text)
            if win:
                entry["Result"]["Winner"] = {
                    "Party": win.group(1),
                    "Candidates": cap(win.group(2)),
                    "Votes": safe_int(win.group(3))
                }

            ru = re.search(r"Runner up.*?\n([A-Za-z]+)\s+(.+?)\s+(\d+)", text)
            if ru:
                entry["Result"]["Runner-Up"] = {
                    "Party": ru.group(1),
                    "Candidates": cap(ru.group(2)),
                    "Votes": safe_int(ru.group(3))
                }

            mg = re.search(r"MARGIN\s*:\s*(\d+)", text)
            if mg:
                entry["Result"]["Margin"] = safe_int(mg.group(1))

            results.append(entry)

    return results



# ============================================================
# ===============  DETAILED PARSER (1996) =====================
# ============================================================

def parse_detailed_1996(path):

    data = {}

    cand_re = re.compile(
        r"^\s*(\d+)\s*\.\s+(.+?)\s+(M|F)\s+([A-Z0-9\(\)\.]+)\s+(\d+)\s+([\d\.]+)%$"
    )

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            heads = re.findall(r"Constituency\s*:\s*(\d+)\s*\.\s*([A-Za-z\s\(\)]+)", text)
            if not heads:
                continue

            for no, cname in heads:
                cid = f"S01-{no}"
                if cid not in data:
                    data[cid] = []

            # candidate rows
            for ln in text.split("\n"):
                ln = ln.strip()
                m = cand_re.match(ln)
                if m:
                    sno, name, sex, party, votes, pct = m.groups()

                    cand = {
                        "Candidate Name": cap(name),
                        "Gender": "MALE" if sex == "M" else "FEMALE",
                        "Age": None,
                        "Category": None,
                        "Party Name": party,
                        "Party Symbol": None,
                        "Total Votes Polled In The Constituency": 0,
                        "Valid Votes": 0,
                        "Votes Secured": {
                            "General": safe_int(votes),
                            "Postal": 0,
                            "Total": safe_int(votes)
                        },
                        "% of Votes Secured": {
                            "Over Total Electors In Constituency": 0.0,
                            "Over Total Votes Polled In Constituency": safe_float(pct)
                        },
                        "Over Total Valid Votes Polled In Constituency": 0.0,
                        "Total Electors": 0
                    }

                    cid = f"S01-{heads[-1][0]}"
                    data[cid].append(cand)

    return data



# ============================================================
# ===============  MERGE =====================================
# ============================================================

def merge_1996(summary, detailed):
    final = []

    for s in summary:
        cid = s["ID"]

        if cid in detailed:
            s["Candidates"] = detailed[cid]

            total_valid = s["Votes"]["Total Valid Votes Polled"]
            total_electors = s["Electors"]["Total"]["Total"]

            for c in s["Candidates"]:
                tv = c["Votes Secured"]["Total"]
                c["Valid Votes"] = total_valid
                c["Total Electors"] = total_electors

                if total_valid > 0:
                    c["Over Total Valid Votes Polled In Constituency"] = round((tv / total_valid) * 100, 2)

            sorted_cands = sorted(s["Candidates"], key=lambda x: x["Votes Secured"]["Total"], reverse=True)

            if sorted_cands:
                s["Result"]["Winner"] = {
                    "Party": sorted_cands[0]["Party Name"],
                    "Candidates": sorted_cands[0]["Candidate Name"],
                    "Votes": sorted_cands[0]["Votes Secured"]["Total"]
                }

            if len(sorted_cands) > 1:
                s["Result"]["Runner-Up"] = {
                    "Party": sorted_cands[1]["Party Name"],
                    "Candidates": sorted_cands[1]["Candidate Name"],
                    "Votes": sorted_cands[1]["Votes Secured"]["Total"]
                }

                s["Result"]["Margin"] = (
                    sorted_cands[0]["Votes Secured"]["Total"]
                    - sorted_cands[1]["Votes Secured"]["Total"]
                )

        final.append(s)

    return final



# ============================================================
# ===============  MAIN ======================================
# ============================================================

summary_path = "/mnt/d/IIT_B_Project/SL_NON GIT/pdf_before 2009/summary/1996_summary_trimmed.pdf"
detailed_path = "/mnt/d/IIT_B_Project/SL_NON GIT/pdf_before 2009/detailed/1996_detailed.pdf"
output_path = "parsed_new/parsed_1996.json"

summary = parse_summary_1996(summary_path)
detailed = parse_detailed_1996(detailed_path)
merged = merge_1996(summary, detailed)

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(merged, f, indent=4)

print("Saved:", output_path)
