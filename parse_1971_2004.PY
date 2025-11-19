import pdfplumber
import json
import re
import string
import os

# ============================================================
# SHARED HELPERS
# ============================================================

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
# SUMMARY PARSER FOR ALL YEARS < 2004
# Works for: 1971, 1977, 1980, 1984, 1989, 1991, 1996, 1998, 1999
# ============================================================

def parse_summary_pre2004(path):
    items = []

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()

            if not text:
                continue

            if "CONSTITUENCY DATA - SUMMARY" not in text:
                continue

            state = re.search(r"STATE/UT\s*:\s*([A-Za-z\s]+)", text)
            code  = re.search(r"CODE\s*:\s*(S\d+)", text)
            cname = re.search(r"CONSTITUENCY\s*:\s*([A-Za-z\s\(\)]+)", text)
            cno   = re.search(r"NO\s*:\s*(\d+)", text)

            if not (state and code and cname and cno):
                continue

            entry = {
                "ID": f"{code.group(1).strip()}-{cno.group(1).strip()}",
                "State_UT": state.group(1).strip(),
                "Constituency": cap(cname.group(1).strip()),
                "Category": "GENERAL",
                "Candidates": [],

                "Electors": {
                    "General": {"Men": 0, "Women": 0, "Third_Gender": 0, "Total": 0},
                    "Service": {"Men": 0, "Women": 0, "Third_Gender": 0, "Total": 0},
                    "Total": {"Men": 0, "Women": 0, "Third_Gender": 0, "Total": 0}
                },

                "Voters": {
                    "General": {"Men": 0, "Women": 0, "Third_Gender": 0, "Total": 0},
                    "Postal": {"Total": 0},
                    "Total": {"Total": 0},
                    "POLLING PERCENTAGE": {
                        "Men": None, "Women": None, "Third_Gender": None, "Total": 0.0
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

            eg = re.findall(r"GENERAL\s+(\d+)\s+(\d+)\s+(\d+)", text)
            if eg:
                m,w,t = eg[0]
                entry["Electors"]["General"] = {"Men": safe_int(m),"Women":safe_int(w),"Third_Gender":0,"Total":safe_int(t)}

            es = re.findall(r"SERVICE\s+(\d+)\s+(\d+)\s+(\d+)", text)
            if es:
                m,w,t = es[0]
                entry["Electors"]["Service"] = {"Men": safe_int(m),"Women":safe_int(w),"Third_Gender":0,"Total":safe_int(t)}

            et = re.findall(r"TOTAL\s+(\d+)\s+(\d+)\s+(\d+)", text)
            if et:
                m,w,t = et[0]
                entry["Electors"]["Total"] = {"Men": safe_int(m),"Women":safe_int(w),"Third_Gender":0,"Total":safe_int(t)}

            vg = re.findall(r"ELECTORS WHO VOTED.*?GENERAL\s+(\d+)\s+(\d+)\s+(\d+)", text, re.S)
            if vg:
                m,w,t = vg[0]
                entry["Voters"]["General"] = {"Men": safe_int(m),"Women":safe_int(w),"Third_Gender":0,"Total":safe_int(t)}

            vp = re.findall(r"POSTAL\s+(\d+)", text)
            if vp:
                entry["Voters"]["Postal"]["Total"] = safe_int(vp[0])

            vt = re.findall(r"TOTAL\s+(\d+)", text)
            if vt:
                entry["Voters"]["Total"]["Total"] = safe_int(vt[-1])

            pp = re.findall(r"POLL(?:ING)? PERCENTAGE\s*[: ]\s*([\d\.]+)", text)
            if pp:
                entry["Voters"]["POLLING PERCENTAGE"]["Total"] = safe_float(pp[0])

            pol = re.search(r"POLLED\s+(\d+)", text)
            if pol:
                entry["Votes"]["Total Votes Polled On EVM"] = safe_int(pol.group(1))

            val = re.search(r"VALID\s+(\d+)", text)
            if val:
                entry["Votes"]["Total Valid Votes Polled"] = safe_int(val.group(1))

            rej = re.search(r"REJECTED\s+(\d+)", text)
            if rej:
                entry["Votes"]["Postal Votes Deducted"] = safe_int(rej.group(1))

            tend = re.search(r"TENDERED\s+(\d+)", text)
            if tend:
                entry["Votes"]["Tendered Votes"] = safe_int(tend.group(1))

            ps = re.search(r"NUMBER\s*:\s*(\d+)", text)
            if ps:
                entry["Polling_Station"]["Number"] = safe_int(ps.group(1))

            avg = re.search(r"AVERAGE ELECTORS PER POLLING STATION\s*[: ]\s*(\d+)", text)
            if avg:
                entry["Polling_Station"]["Average Electors Per Polling"] = safe_int(avg.group(1))

            entry["Dates"] = re.findall(r"(\d{2}-\d{2}-\d{4})", text)

            win = re.search(r"Winner.*?\n([A-Z]+)\s+(.+?)\s+(\d+)", text)
            if win:
                entry["Result"]["Winner"] = {
                    "Party": win.group(1),
                    "Candidates": cap(win.group(2)),
                    "Votes": safe_int(win.group(3))
                }

            ru = re.search(r"Runner.*?\n([A-Z]+)\s+(.+?)\s+(\d+)", text)
            if ru:
                entry["Result"]["Runner-Up"] = {
                    "Party": ru.group(1),
                    "Candidates": cap(ru.group(2)),
                    "Votes": safe_int(ru.group(3))
                }

            mr = re.search(r"MARGIN\s*:\s*(\d+)", text)
            if mr:
                entry["Result"]["Margin"] = safe_int(mr.group(1))

            items.append(entry)

    return items

# ============================================================
# DETAILED PARSER FOR ALL YEARS < 2004
# ============================================================

def parse_detailed_pre2004(path):
    data = {}

    cand_re = re.compile(
        r"^\s*(\d+)\s*\.\s+(.+?)\s+(M|F)\s+([A-Z0-9\-\(\)\.]+)\s+(\d+)\s+([\d\.]+)%$"
    )

    head_re = re.compile(r"Constituency\s*:\s*(\d+)\s*\.\s*(.+)", re.I)

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()

            if not text:
                continue

            heads = head_re.findall(text)
            if not heads:
                continue

            for no,_ in heads:
                cid = f"S01-{no}"
                if cid not in data:
                    data[cid] = []

            for ln in text.split("\n"):
                ln = ln.strip()
                m = cand_re.match(ln)

                if m:
                    sno,name,sex,party,votes,pct = m.groups()

                    c = {
                        "Candidate Name": cap(name),
                        "Gender": "MALE" if sex=="M" else "FEMALE",
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

                    last_id = f"S01-{heads[-1][0]}"
                    data[last_id].append(c)

    return data

# ============================================================
# 2004 PARSER (different structure)
# ============================================================

def parse_detailed_2004(path):
    data = {}

    cand_re = re.compile(
        r"^\s*(\d+)\.\s+(.+?)\s+(M|F)\s+(\d+)\s+([A-Z]+)\s+(\d+)\s+(\d+)\s+(\d+)$"
    )

    head_re = re.compile(r"Constituency\s*:\s*(\d+)\s*\.\s*(.+)", re.I)

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            tx = page.extract_text()
            if not tx:
                continue

            heads = head_re.findall(tx)
            if not heads:
                continue

            for no,_ in heads:
                cid = f"S01-{no}"
                if cid not in data:
                    data[cid] = []

            for ln in tx.split("\n"):
                ln = ln.strip()
                m = cand_re.match(ln)
                if m:
                    sno,name,sex,age,cat,gv,pv,tv = m.groups()

                    c = {
                        "Candidate Name": cap(name),
                        "Gender": "MALE" if sex=="M" else "FEMALE",
                        "Age": safe_int(age),
                        "Category": cat,
                        "Party Name": cat,
                        "Party Symbol": None,
                        "Total Votes Polled In The Constituency": 0,
                        "Valid Votes": 0,
                        "Votes Secured": {
                            "General": safe_int(gv),
                            "Postal": safe_int(pv),
                            "Total": safe_int(tv)
                        },
                        "% of Votes Secured": {
                            "Over Total Electors In Constituency": 0.0,
                            "Over Total Votes Polled In Constituency": 0.0
                        },
                        "Over Total Valid Votes Polled In Constituency": 0.0,
                        "Total Electors": 0
                    }

                    last_id = f"S01-{heads[-1][0]}"
                    data[last_id].append(c)

    return data

# ============================================================
# MERGE FOR ALL YEARS
# ============================================================

def merge(summary, detailed):
    final = []

    for s in summary:
        cid = s["ID"]

        if cid in detailed:
            s["Candidates"] = detailed[cid]

            tv = s["Votes"]["Total Valid Votes Polled"]
            te = s["Electors"]["Total"]["Total"]

            for c in s["Candidates"]:
                v = c["Votes Secured"]["Total"]
                c["Valid Votes"] = tv
                c["Total Electors"] = te
                if tv > 0:
                    c["Over Total Valid Votes Polled In Constituency"] = round((v / tv)*100,2)

            sorted_c = sorted(s["Candidates"], key=lambda x: x["Votes Secured"]["Total"], reverse=True)

            if sorted_c:
                s["Result"]["Winner"] = {
                    "Party": sorted_c[0]["Party Name"],
                    "Candidates": sorted_c[0]["Candidate Name"],
                    "Votes": sorted_c[0]["Votes Secured"]["Total"]
                }

            if len(sorted_c) > 1:
                s["Result"]["Runner-Up"] = {
                    "Party": sorted_c[1]["Party Name"],
                    "Candidates": sorted_c[1]["Candidate Name"],
                    "Votes": sorted_c[1]["Votes Secured"]["Total"]
                }
                s["Result"]["Margin"] = sorted_c[0]["Votes Secured"]["Total"] - sorted_c[1]["Votes Secured"]["Total"]

        final.append(s)
    return final

# ============================================================
# MASTER RUN FUNCTION
# ============================================================

def run_year(year, summary_path, detailed_path, output_path):
    print(f"\nProcessing: {year}")

    if year == 2004:
        summary = parse_summary_pre2004(summary_path)
        detailed = parse_detailed_2004(detailed_path)
    else:
        summary = parse_summary_pre2004(summary_path)
        detailed = parse_detailed_pre2004(detailed_path)

    merged = merge(summary, detailed)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=4)

    print("Saved:", output_path)


# ============================================================
# CALL FOR ALL YOUR YEARS
# ============================================================

run_year(1971, "/mnt/d/IIT_B_Project/SL_NON GIT/pdf_before 2009/summary/1971_summary_trimmed.pdf", "/mnt/d/IIT_B_Project/SL_NON GIT/pdf_before 2009/detailed/1971_detailed.pdf", "allParsed/1971.json")
run_year(1977, "/mnt/d/IIT_B_Project/SL_NON GIT/pdf_before 2009/summary/1977_summary_trimmed.pdf", "/mnt/d/IIT_B_Project/SL_NON GIT/pdf_before 2009/detailed/1977_detailed.pdf", "allParsed/1977.json")
run_year(1980, "/mnt/d/IIT_B_Project/SL_NON GIT/pdf_before 2009/summary/1980_summary_trimmed.pdf", "/mnt/d/IIT_B_Project/SL_NON GIT/pdf_before 2009/detailed/1980_detailed.pdf", "allParsed/1980.json")
run_year(1984, "/mnt/d/IIT_B_Project/SL_NON GIT/pdf_before 2009/summary/1984_summary_trimmed.pdf", "/mnt/d/IIT_B_Project/SL_NON GIT/pdf_before 2009/detailed/1984_detailed.pdf", "allParsed/1984.json")
run_year(1989, "/mnt/d/IIT_B_Project/SL_NON GIT/pdf_before 2009/summary/1989_summary_trimmed.pdf", "/mnt/d/IIT_B_Project/SL_NON GIT/pdf_before 2009/detailed/1989_detailed.pdf", "allParsed/1989.json")
run_year(1991, "/mnt/d/IIT_B_Project/SL_NON GIT/pdf_before 2009/summary/1991_summary_trimmed.pdf", "/mnt/d/IIT_B_Project/SL_NON GIT/pdf_before 2009/detailed/1991_detailed.pdf", "allParsed/1991.json")
run_year(1996, "/mnt/d/IIT_B_Project/SL_NON GIT/pdf_before 2009/summary/1996_summary_trimmed.pdf", "/mnt/d/IIT_B_Project/SL_NON GIT/pdf_before 2009/detailed/1996_detailed.pdf", "allParsed/1996.json")
run_year(1998, "/mnt/d/IIT_B_Project/SL_NON GIT/pdf_before 2009/summary/1998_summary_trimmed.pdf", "/mnt/d/IIT_B_Project/SL_NON GIT/pdf_before 2009/detailed/1998-detailed.pdf", "allParsed/1998.json")
run_year(1999, "/mnt/d/IIT_B_Project/SL_NON GIT/pdf_before 2009/summary/1999_summary_trimmed.pdf", "/mnt/d/IIT_B_Project/SL_NON GIT/pdf_before 2009/detailed/1999_detailed.pdf", "allParsed/1999.json")
run_year(2004, "/mnt/d/IIT_B_Project/SL_NON GIT/pdf_before 2009/summary/2004_summary_trimmed.pdf", "/mnt/d/IIT_B_Project/SL_NON GIT/pdf_before 2009/detailed/2004_detailed.pdf", "allParsed/2004.json")
