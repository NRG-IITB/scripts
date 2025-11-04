"""
Script to parse 2009 constituency-wise data reports (PDF format).
This script uses regex-based parsing with pdfplumber and produces JSON output
matching the 2024 format used in ECI datasets.

[MODIFIED to output 2024-compliant JSON structure directly and fix data errors]
"""

import json
from enum import Enum
import string
import sys
import re

try:
    import pdfplumber
except ImportError:
    print("Error: 'pdfplumber' not found. Install via: pip install pdfplumber")
    sys.exit(1)

# --------------------------------------------------------------------------
# STATE/UT CODE MAP (2009)
# --------------------------------------------------------------------------
STATE_UT_MAP = {
    "S01": "Andhra Pradesh",
    "S02": "Arunachal Pradesh",
    "S03": "Assam",
    "S04": "Bihar",
    "S05": "Goa",
    "S06": "Gujarat",
    "S07": "Haryana",
    "S08": "Himachal Pradesh",
    "S09": "Jammu & Kashmir",
    "S10": "Karnataka",
    "S11": "Kerala",
    "S12": "Madhya Pradesh",
    "S13": "Maharashtra",
    "S14": "Manipur",
    "S15": "Meghalaya",
    "S16": "Mizoram",
    "S17": "Nagaland",
    "S18": "Orissa",
    "S19": "Punjab",
    "S20": "Rajasthan",
    "S21": "Sikkim",
    "S22": "Tamil Nadu",
    "S23": "Tripura",
    "S24": "Uttar Pradesh",
    "S25": "West Bengal",
    "S26": "Chhattisgarh",
    "S27": "Jharkhand",
    "S28": "Uttarakhand",
    "U01": "Andaman & Nicobar Islands",
    "U02": "Chandigarh",
    "U03": "Dadra & Nagar Haveli",
    "U04": "Daman & Diu",
    "U05": "National Capital Territory of Delhi",
    "U06": "Lakshadweep",
    "U07": "Puducherry",
}

# --------------------------------------------------------------------------
# ENUM (for reference, not heavily used here)
# --------------------------------------------------------------------------
class CurrentSection(Enum):
    NONE = "None"

# --------------------------------------------------------------------------
# HELPERS
# --------------------------------------------------------------------------
def format_constituency_name(name):
    if not name:
        return ""
    name = re.sub(r"^\s*[\d\s-]+\s*", "", name)
    name = re.sub(r"\s*\((SC|ST)\)\s*$", "", name, flags=re.I)
    parts = name.split('-')
    parts = [string.capwords(part.strip()) for part in parts]
    return '-'.join(parts).replace('&', 'and')


def safe_int(value):
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        value = value.strip().replace(',', '').replace('-', '0').replace('N/A', '0')
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def safe_float(value):
    if isinstance(value, (float, int)):
        return float(value)
    if isinstance(value, str):
        value = value.strip().replace('-', '0.0').replace('N/A', '0.0')
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

# --------------------------------------------------------------------------
# 2024-Compliant Template Helpers
# --------------------------------------------------------------------------
def get_empty_gender_obj(default_val=0):
    """Creates a standard gender object, using 0 for electors and None for voters."""
    val = 0 if default_val == 0 else None
    # 2009 data has no third gender, so it is always 0.
    return {"Men": val, "Women": val, "Third_Gender": 0, "Total": default_val}

def get_2024_voters_template():
    """Creates a blank, 2024-compliant Voters object."""
    return {
        "General": get_empty_gender_obj(0),
        "OverSeas": get_empty_gender_obj(0),
        "Proxy": get_empty_gender_obj(0),
        "Postal": get_empty_gender_obj(0),
        "Total": get_empty_gender_obj(0),
        "Votes Not Counted From CU(s) as Per ECI Instructions": get_empty_gender_obj(0),
        "POLLING PERCENTAGE": {"Men": None, "Women": None, "Third_Gender": None, "Total": 0.0}
    }

def get_2024_electors_template():
    """Creates a blank, 2024-compliant Electors object."""
    return {
        "General": get_empty_gender_obj(0),
        "OverSeas": get_empty_gender_obj(0), # Add 'OverSeas'
        "Service": get_empty_gender_obj(0),
        "Total": get_empty_gender_obj(0)
    }

def get_2024_votes_template():
    """Creates a blank, 2024-compliant Votes object."""
    return {
        "Total Votes Polled On EVM": 0,
        "Total Deducted Votes From EVM": 0,
        "Total Valid Votes polled on EVM": 0,
        "Postal Votes Counted": 0,
        "Postal Votes Deducted": 0,
        "Valid Postal Votes": 0,
        "Total Valid Votes Polled": 0,
        "Test Votes polled On EVM": 0,
        "Votes Polled for 'NOTA'(Including Postal)": 0, # 2009 had no NOTA
        "Tendered Votes": 0,
    }


# --------------------------------------------------------------------------
# SUMMARY PDF PARSER (Report 32)
# --------------------------------------------------------------------------
def parse_2009_summary_pdf(pdf_path):
    print("\n--- Parsing Summary PDF (Report 32) ---")
    if pdfplumber is None:
        print("Error: 'pdfplumber' is required for PDF parsing.")
        return []

    all_constituency_data = []

    # Pre-compile a few core regex patterns
    state_re = re.compile(r"State/UT\s*:\s*([A-Z\d]+)", re.I)
    const_re = re.compile(r"Constituency\s*:\s*([^\n\(]+)", re.I)
    id_re = re.compile(r"No\.\s*:\s*(\d+)", re.I)
    
    # --- All other regexes for summary parsing (as in your script) ---
    cand_nominated_re = re.compile(r"1\.\s*NOMINATED\s+([\d-]+)\s+([\d-]+)\s+([\d-]+)", re.I)
    cand_rejected_re = re.compile(r"2\.\s*NOMINATION REJECTED\s+([\d-]+)\s+([\d-]+)\s+([\d-]+)", re.I)
    cand_withdrawn_re = re.compile(r"3\.\s*WITHDRAWN\s+([\d-]+)\s+([\d-]+)\s+([\d-]+)", re.I)
    cand_contested_re = re.compile(r"4\.\s*CONTESTED\s+([\d-]+)\s+([\d-]+)\s+([\d-]+)", re.I)
    cand_forfeited_re = re.compile(r"5\.\s*FORFEITED DEPOSIT\s+([\d-]+)\s+([\d-]+)\s+([\d-]+)", re.I)
    elec_general_re = re.compile(r"II\.\s*ELECTORS\s*1\.\s*GENERAL\s+([\d-]+)\s+([\d-]+)\s+([\d-]+)", re.I | re.DOTALL)
    elec_service_re = re.compile(r"2\.\s*SERVICE\s+([\d-]+)\s+([\d-]+)\s+([\d-]+)", re.I)
    elec_total_re = re.compile(r"3\.\s*TOTAL\s+([\d-]+)\s+([\d-]+)\s+([\d-]+)", re.I)
    voters_general_re = re.compile(r"III\.\s*VOTERS\s*1\.\s*GENERAL\s+([\d-]+)\s+([\d-]+)\s+([\d-]+)", re.I | re.DOTALL)
    voters_proxy_re = re.compile(r"2\.\s*PROXY\s+([\d-]+)", re.I)
    voters_postal_re = re.compile(r"3\.\s*POSTAL\s+([\d-]+)", re.I)
    voters_total_re = re.compile(r"4\.\s*TOTAL\s+([\d-]+)", re.I)
    polling_percent_re = re.compile(r"III\(A\)\.\s*POLLING PERCENTAGE\s*([\d\.]+)", re.I)
    votes_rejected_re = re.compile(r"1\.\s*REJECTED VOTES \(POSTAL\)\s*([\d-]+)", re.I) # This field name is misleading in the PDF
    votes_not_retrieved_re = re.compile(r"2\.\s*VOTES NOT RETREIVED FROM EVM\s*([\d-]+)", re.I)
    votes_valid_re = re.compile(r"3\.\s*TOTAL VALID VOTES POLLED\s*([\d-]+)", re.I)
    votes_tendered_re = re.compile(r"4\. \s*TENDERED VOTES\s*([\d-]+)", re.I)
    ps_number_re = re.compile(r"V\.\s*POLLING STATIONS\s*NUMBER\s*(\d+)", re.I | re.DOTALL)
    ps_avg_re = re.compile(r"AVERAGE ELECTORS PER POLLING STATION\s*(\d+)", re.I)
    dates_polling_re = re.compile(r"POLLING\s+([\d-]+)", re.I)
    dates_counting_re = re.compile(r"COUNTING\s+([\d-]+)", re.I)
    dates_decl_re = re.compile(r"DECLARATION\s+([\d-]+)", re.I)

    # Helper to find pattern and return groups or default
    def find_groups(regex, text, num_groups=1):
        match = regex.search(text)
        default = ["0"] * num_groups
        if not match:
            return default
        return [match.group(i+1).strip() for i in range(num_groups)]

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text(x_tolerance=1, y_tolerance=3)
            if not text:
                continue

            # --- [SCHEMA FIX] ---
            # Create the 2024-compliant data structure
            data = {
                "ID": None,
                "Constituency": None,
                "State_UT": None,
                "Category": None,
                "Candidates": [], # To be filled by detailed parser
                "Summary_Candidate_Stats": {}, # Will be removed at the end
                "Electors": get_2024_electors_template(),
                "Voters": get_2024_voters_template(),
                "Votes": get_2024_votes_template(), # Use the 2024 template
                "Polling_Station": {"Number": 0, "Average Electors Per Polling": 0},
                "Dates": [],
                "Result": {
                    "Winner": {"Party": None, "Candidates": None, "Votes": 0},
                    "Runner-Up": {"Party": None, "Candidates": None, "Votes": 0},
                    "Margin": 0,
                },
            }
            # --- [END SCHEMA FIX] ---

            state_match = state_re.search(text)
            const_match = const_re.search(text)
            id_match = id_re.search(text)

            if state_match and const_match and id_match:
                state_code = state_match.group(1).strip().upper()
                data["State_UT"] = STATE_UT_MAP.get(state_code, state_code)
                data["ID"] = f"{state_code}-{id_match.group(1).strip()}"
                constituency_full = const_match.group(1).strip()
                cat_match = re.search(r"\((ST|SC)\)", text, re.I)
                data["Category"] = cat_match.group(1).upper() if cat_match else "GENERAL"
                data["Constituency"] = format_constituency_name(constituency_full)
                
                # --- Parse all other fields ---
                nom = find_groups(cand_nominated_re, text, 3)
                rej = find_groups(cand_rejected_re, text, 3)
                wd = find_groups(cand_withdrawn_re, text, 3)
                con = find_groups(cand_contested_re, text, 3)
                forf = find_groups(cand_forfeited_re, text, 3)
                data["Summary_Candidate_Stats"]["Nominated"] = {"Men": safe_int(nom[0]), "Women": safe_int(nom[1]), "Third_Gender": 0, "Total": safe_int(nom[2])}
                data["Summary_Candidate_Stats"]["Nomination Rejected"] = {"Men": safe_int(rej[0]), "Women": safe_int(rej[1]), "Third_Gender": 0, "Total": safe_int(rej[2])}
                data["Summary_Candidate_Stats"]["Withdrawn"] = {"Men": safe_int(wd[0]), "Women": safe_int(wd[1]), "Third_Gender": 0, "Total": safe_int(wd[2])}
                data["Summary_Candidate_Stats"]["Contested"] = {"Men": safe_int(con[0]), "Women": safe_int(con[1]), "Third_Gender": 0, "Total": safe_int(con[2])}
                data["Summary_Candidate_Stats"]["Forfeited Deposit"] = {"Men": safe_int(forf[0]), "Women": safe_int(forf[1]), "Third_Gender": 0, "Total": safe_int(forf[2])}
                
                gen_e = find_groups(elec_general_re, text, 3)
                ser_e = find_groups(elec_service_re, text, 3)
                tot_e = find_groups(elec_total_re, text, 3)
                data["Electors"]["General"] = {"Men": safe_int(gen_e[0]), "Women": safe_int(gen_e[1]), "Third_Gender": 0, "Total": safe_int(gen_e[2])}
                data["Electors"]["Service"] = {"Men": safe_int(ser_e[0]), "Women": safe_int(ser_e[1]), "Third_Gender": 0, "Total": safe_int(ser_e[2])}
                data["Electors"]["Total"] = {"Men": safe_int(tot_e[0]), "Women": safe_int(tot_e[1]), "Third_Gender": 0, "Total": safe_int(tot_e[2])}

                gen_v = find_groups(voters_general_re, text, 3)
                prox_v = find_groups(voters_proxy_re, text, 1)
                post_v = find_groups(voters_postal_re, text, 1)
                tot_v = find_groups(voters_total_re, text, 1)
                poll_pct = find_groups(polling_percent_re, text, 1)
                data["Voters"]["General"] = {"Men": safe_int(gen_v[0]), "Women": safe_int(gen_v[1]), "Third_Gender": 0, "Total": safe_int(gen_v[2])}
                data["Voters"]["Proxy"]["Total"] = safe_int(prox_v[0])
                data["Voters"]["Postal"]["Total"] = safe_int(post_v[0])
                data["Voters"]["Total"]["Total"] = safe_int(tot_v[0])
                # --- [SCHEMA FIX] ---
                data["Voters"]["POLLING PERCENTAGE"]["Total"] = safe_float(poll_pct[0])
                # --- [END SCHEMA FIX] ---
                
                rej_v_postal_text = find_groups(votes_rejected_re, text, 1) # This is likely TOTAL rejected
                not_ret_v = find_groups(votes_not_retrieved_re, text, 1)
                valid_v = find_groups(votes_valid_re, text, 1)
                tend_v = find_groups(votes_tendered_re, text, 1)

                # --- [DATA/SCHEMA FIX for Votes] ---
                # This logic handles the S01-1 case where Rejected Postal (584) > Total Postal (251)
                
                total_rejected_votes = safe_int(rej_v_postal_text[0])
                total_votes_polled = safe_int(tot_v[0])
                total_valid_votes = safe_int(valid_v[0])
                
                # S01-1: 863581 (polled) - 862997 (valid) = 584 (matches total_rejected_votes)
                if total_votes_polled - total_valid_votes != total_rejected_votes:
                    print(f"Warning for {data['ID']}: Vote math inconsistent. {total_votes_polled} - {total_valid_votes} != {total_rejected_votes}")
                    # Use the calculated total rejected if explicit one is wrong
                    total_rejected_votes = total_votes_polled - total_valid_votes
                
                data["Votes"]["Postal Votes Counted"] = safe_int(post_v[0])
                data["Votes"]["Total Votes Polled On EVM"] = safe_int(tot_v[0]) - safe_int(post_v[0])
                data["Votes"]["Total Valid Votes Polled"] = total_valid_votes
                data["Votes"]["Tendered Votes"] = safe_int(tend_v[0])
                
                # Handle contradictory PDF data (like S01-1)
                data["Votes"]["Total Deducted Votes From EVM"] = safe_int(not_ret_v[0])
                
                # Calculate remaining rejections, assume they are postal
                postal_deducted = total_rejected_votes - data["Votes"]["Total Deducted Votes From EVM"]
                
                if postal_deducted < 0:
                    postal_deducted = 0 # Should not happen, but as a safeguard
                
                # *THE FIX for negative votes*:
                if postal_deducted > data["Votes"]["Postal Votes Counted"]:
                    # This is the S01-1 case (584 > 251)
                    print(f"Warning for {data['ID']}: PDF data is contradictory. Calculated Postal Rejected ({postal_deducted}) > Postal Polled ({data['Votes']['Postal Votes Counted']}).")
                    # Sane fallback: Assign all rejections to EVM and assume 0 postal rejections
                    data["Votes"]["Total Deducted Votes From EVM"] = total_rejected_votes
                    data["Votes"]["Postal Votes Deducted"] = 0
                else:
                    # Data is consistent
                    data["Votes"]["Postal Votes Deducted"] = postal_deducted
                
                # Final 2024-compliant calculations
                data["Votes"]["Valid Postal Votes"] = data["Votes"]["Postal Votes Counted"] - data["Votes"]["Postal Votes Deducted"]
                data["Votes"]["Total Valid Votes polled on EVM"] = data["Votes"]["Total Votes Polled On EVM"] - data["Votes"]["Total Deducted Votes From EVM"]
                
                # Final integrity check
                if data["Votes"]["Total Valid Votes polled on EVM"] < 0:
                    data["Votes"]["Total Valid Votes polled on EVM"] = 0
                
                # Double-check main calculation
                if data["Votes"]["Total Valid Votes polled on EVM"] + data["Votes"]["Valid Postal Votes"] != data["Votes"]["Total Valid Votes Polled"]:
                     # Fallback to preserve the PDF's total valid votes, adjust EVM valid votes
                     data["Votes"]["Total Valid Votes polled on EVM"] = data["Votes"]["Total Valid Votes Polled"] - data["Votes"]["Valid Postal Votes"]
                # --- [END DATA/SCHEMA FIX] ---

                ps_num = find_groups(ps_number_re, text, 1)
                ps_a = find_groups(ps_avg_re, text, 1)
                data["Polling_Station"]["Number"] = safe_int(ps_num[0])
                data["Polling_Station"]["Average Electors Per Polling"] = safe_int(ps_a[0])

                # --- [SCHEMA FIX] ---
                # Match 2024 format: [Polling Date, Declaration Date]
                poll_d = find_groups(dates_polling_re, text, 1)
                decl_d = find_groups(dates_decl_re, text, 1)
                if poll_d[0] != "0": data["Dates"].append(poll_d[0])
                if decl_d[0] != "0": data["Dates"].append(decl_d[0])
                # --- [END SCHEMA FIX] ---

                # --- [DATA NOTE] ---
                # Result block is parsed but will be RECALCULATED after merging
                data["Result"]["Winner"] = {"Party": None, "Candidates": None, "Votes": 0}
                data["Result"]["Runner-Up"] = {"Party": None, "Candidates": None, "Votes": 0}
                data["Result"]["Margin"] = 0
                # --- [END DATA NOTE] ---

                all_constituency_data.append(data)
            else:
                pass 

    print(f"--- Summary PDF parsing complete. Found {len(all_constituency_data)} entries. ---")
    return all_constituency_data

# --------------------------------------------------------------------------
# DETAILED PDF PARSER (Report 33)
# --------------------------------------------------------------------------
def parse_2009_detailed_pdf(pdf_path, ids_map):
    """
    Parse 2009 Detailed Results PDF (Report 33)
    with STATE-AWARE, dual-direction constituency name detection
    and a SINGLE-PASS STATE MACHINE.
    """
    print("\n--- Parsing Detailed PDF (Report 33) ---")
    if pdfplumber is None:
        print("Error: 'pdfplumber' is required for PDF parsing.")
        return {}

    # --- Build a NESTED reverse map: {STATE: {CONSTITUENCY: ID}} ---
    state_to_const_map = {}
    for full_id, details in ids_map.items():
        state_upper = details["State_UT"].upper()
        const_upper = details["Constituency"].upper()
        if state_upper not in state_to_const_map:
            state_to_const_map[state_upper] = {}
        state_to_const_map[state_upper][const_upper] = full_id
    print(f"Building nested state-aware map... {len(state_to_const_map)} states.")

    candidates_by_constituency = {}
    current_constituency_id = None
    current_total_electors = 0
    current_category = "GENERAL"
    
    # --- State tracking variables ---
    current_state_name = None # This will be the CANONICAL name
    
    # --- [FIX] Create an ALIAS MAP for state names ---
    # This maps names found in the PDF (key) to the canonical names from the summary (value)
    alternate_state_name_map = {
        # PDF Name : Canonical Name
        "DELHI": "NATIONAL CAPITAL TERRITORY OF DELHI",
        "NCT OF DELHI": "NATIONAL CAPITAL TERRITORY OF DELHI",
        
        # --- Add all common misspellings for Chhattisgarh ---
        "CHHATTISGARH": "CHHATTISGARH", # Correct spelling
        "CHATTISGARH": "CHHATTISGARH",  # Missing 'H'
        "CHHATISGARH": "CHHATTISGARH",  # Missing 'T'
    }
    # Add all correct names to the map as well
    for name in STATE_UT_MAP.values():
        alternate_state_name_map[name.upper()] = name.upper()
    # --- [END FIX] ---

    # Candidate data anchor
    anchor_regex = re.compile(r"([MF])\s+(\d+)\s+([A-Z]{2,3})", re.I)

    # --- Stricter Header Regexes (require 3+ name characters) ---
    normal_const_regex = re.compile(
        r"CONSTITUENCY\s*:\s*(\d+)?\s*\.?\s*([A-Za-z&\-\s]{3,}[^\(]*?)(?:\((ST|SC)\))?",
        re.IGNORECASE
    )
    reverse_const_regex = re.compile(
        r"([A-Za-z&\-\s]{3,})\s+CONSTITUENCY\s*:",
        re.IGNORECASE
    )

    def normalize_name(name: str) -> str:
        if not name:
            return ""
        name = re.sub(r"\s+", " ", name.strip())
        name = re.sub(r"[^A-Za-z&\-\s]", "", name)
        name = name.replace("’", "'")
        name = name.replace("NAGARH", "NAGAR")    # OCR fix
        name = name.replace("UDHAMSINGH", "UDHAMSINGH NAGAR") # OCR fix
        name = name.replace("NAGA", "NAGAR") # Fix from user logs
        name = name.replace("ISLAND", "ISLANDS") # Fix from user logs
        return format_constituency_name(name)

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            
            text = page.extract_text(x_tolerance=1, y_tolerance=3)
            if not text:
                print(f"Warning: No text found on page {page_num}")
                continue
            
            lines = [re.sub(r"\s+", " ", ln.strip()) for ln in text.split("\n") if ln.strip()]

            # --- Single-pass state machine logic ---
            for i, line in enumerate(lines):
                line_upper_stripped = line.strip().upper()
                
                # --- 1. Check for State Header using ALIAS MAP ---
                if line_upper_stripped in alternate_state_name_map:
                    # Get the CANONICAL name (from summary file)
                    canonical_name = alternate_state_name_map[line_upper_stripped]
                    current_state_name = canonical_name # Use the canonical name for lookups
                    print(f"  [Detail] SETTING STATE: {current_state_name} (Found '{line.strip()}' on page {page_num})")
                    current_constituency_id = None # Unset constituency
                    continue

                # 2. Check for Constituency Header
                const_match = normal_const_regex.search(line)
                is_reversed = False
                
                if not const_match:
                    const_match = reverse_const_regex.search(line)
                    is_reversed = True

                # If it is a header, set state and continue
                if const_match:
                    const_name = ""
                    cat = "GENERAL"
                    
                    try:
                        if is_reversed:
                            const_name = normalize_name(const_match.group(1))
                            cat_match = re.search(r"\((ST|SC)\)", line, re.I)
                            cat = cat_match.group(1).upper() if cat_match else "GENERAL"
                        else:
                            const_name = normalize_name(const_match.group(2))
                            cat = const_match.group(3).upper() if const_match.group(3) else "GENERAL"
                    except Exception as e:
                        print(f"Warning: Error parsing header, may be a false positive: {line}. Error: {e}")
                        continue

                    if not const_name:
                        continue

                    # --- [DATA FIX] ---
                    # Extract total electors from detailed PDF
                    total_electors = 0
                    for j in range(1, 4):
                        if i + j < len(lines):
                            # Regex is brittle, but it's the only source in this PDF
                            m = re.search(r"\(Total Electors\s*([\d,]+)\)", lines[i + j], re.I)
                            if m:
                                total_electors = safe_int(m.group(1))
                                break
                    # --- [END DATA FIX] ---
                    
                    # --- State-Aware ID Matching ---
                    found_id = None
                    const_upper = const_name.upper()

                    if not current_state_name:
                        print(f"  [Detail] Warning: Found constituency '{const_name}' but no state is set. Skipping.")
                        continue
                    
                    state_upper = current_state_name.upper() # This is now the canonical name

                    if state_upper in state_to_const_map and const_upper in state_to_const_map[state_upper]:
                        found_id = state_to_const_map[state_upper][const_upper]
                    else:
                        # Fallback for partial names
                        if state_upper in state_to_const_map:
                            for known_name, full_id in state_to_const_map[state_upper].items():
                                if const_upper and known_name and len(const_upper) >= 4 and (known_name.startswith(const_upper[:4]) or const_upper.startswith(known_name[:4])):
                                    found_id = full_id
                                    print(f"  [Detail] Found constituency by PARTIAL NAME: {const_upper} -> {known_name} (ID: {full_id})")
                                    break

                    if not found_id:
                        print(f"  [Detail] Warning: PDF constituency (Name: {const_name}, State: {current_state_name}) not found in summary data.")
                        current_constituency_id = None # Unset state
                        continue

                    # --- SET STATE ---
                    current_constituency_id = found_id
                    current_total_electors = total_electors # Store the value found by regex
                    current_category = cat
                    print(f"  [Detail] SETTING CONSTITUENCY: {const_name} (ID: {current_constituency_id})")

                    if found_id not in candidates_by_constituency:
                        candidates_by_constituency[found_id] = {
                            "Candidates": [],
                            "Category": current_category
                        }
                    continue

                # 3. If not a header, check for candidate
                if not current_constituency_id:
                    continue # Skip lines until a header is found

                anchor_match = anchor_regex.search(line)
                if not anchor_match:
                    continue # Not a candidate line

                # 4. Process candidate line
                try:
                    sex = anchor_match.group(1).strip().upper()
                    age = safe_int(anchor_match.group(2))
                    category = anchor_match.group(3).strip().upper()
                    before = line[:anchor_match.start()]
                    after = line[anchor_match.end():]

                    before_match = re.match(r"^\s*(\d+)\s+(.+?)\s*$", before)
                    if not before_match:
                        continue

                    candidate = before_match.group(2).strip()
                    after_match = re.match(
                        r"^\s*(.+?)\s+([\d-]+)\s+([\d-]+)\s+([\d-]+)\s+([\d\.-]+)\s+([\d\.-]+)\s*$",
                        after
                    )
                    if not after_match:
                        continue

                    party = after_match.group(1).strip()
                    gen_votes = safe_int(after_match.group(2))
                    post_votes = safe_int(after_match.group(3))
                    total_votes = safe_int(after_match.group(4))
                    pct_electors = safe_float(after_match.group(5))
                    pct_polled = safe_float(after_match.group(6))

                    # --- [SCHEMA/FORMAT FIX] ---
                    # Build candidate object in 2024 format
                    candidate_data = {
                        "Candidate Name": candidate,
                        "Gender": "MALE" if sex == "M" else "FEMALE",
                        "Age": age,
                        "Category": category,
                        "Party Name": party,
                        "Party Symbol": None, # 2009 PDF has no symbols
                        "Total Votes Polled In The Constituency": 0, # Placeholder
                        "Valid Votes": 0, # Placeholder
                        "Votes Secured": {
                            "General": gen_votes,
                            "Postal": post_votes,
                            "Total": total_votes
                        },
                        "% of Votes Secured": {
                            "Over Total Electors In Constituency": round(pct_electors, 2),
                            "Over Total Votes Polled In Constituency": round(pct_polled, 2),
                        },
                        "Over Total Valid Votes Polled In Constituency": 0.0, # Placeholder
                        "Total Electors": current_total_electors # [DATA FIX]: Use parsed value
                        
                    }
                    # --- [END SCHEMA/FORMAT FIX] ---
                    
                    candidates_by_constituency[current_constituency_id]["Candidates"].append(candidate_data)

                except Exception as e:
                    print(f"Error processing candidate row: {line}. Error: {e}")

    print(f"--- Detailed PDF parsing complete. Found data for {len(candidates_by_constituency)} constituencies. ---")
    return candidates_by_constituency


# --------------------------------------------------------------------------
# MAIN DRIVER
# --------------------------------------------------------------------------
def run_2009_parse():
    # --- [PATH FIX] ---
    # Restored your original file paths
    PDF_PATHS = {
        "summary": "/mnt/c/Users/dell/scripts/converted_xlsx_reports/Summary_details/Constituency Data Summary.pdf",
        "detailed": "/mnt/c/Users/dell/scripts/converted_xlsx_reports/Summary_details/Constituency Wise Detailed Result.pdf",
        "output": "/mnt/c/Users/dell/scripts/parsed2009/9.json",
    }
    # --- [END PATH FIX] ---

    # Allow command-line overrides (optional)
    if len(sys.argv) == 4:
        PDF_PATHS["summary"] = sys.argv[1]
        PDF_PATHS["detailed"] = sys.argv[2]
        PDF_PATHS["output"] = sys.argv[3]

    try:
        print("Starting 2009 PDF parsing process...")
        print(f"  Summary file: {PDF_PATHS['summary']}")
        print(f"  Detailed file: {PDF_PATHS['detailed']}")
        print(f"  Output file: {PDF_PATHS['output']}")

        parsed_summary = parse_2009_summary_pdf(PDF_PATHS["summary"])
        
        if not parsed_summary:
            print("Error: No data parsed from summary PDF.")
            return

        print(f"Successfully parsed {len(parsed_summary)} constituency summaries.")
        ids = {c["ID"]: {"State_UT": c["State_UT"], "Constituency": c["Constituency"]} for c in parsed_summary if c["ID"]}

        candidates_map = parse_2009_detailed_pdf(PDF_PATHS["detailed"], ids)
        print(f"Successfully parsed candidate data for {len(candidates_map)} constituencies.")

        print("\n--- Merging Summary and Detailed Data ---")
        merged_count = 0
        for c in parsed_summary:
            full_id = c["ID"]
            if full_id in candidates_map:
                cand_data = candidates_map[full_id]
                total_polled = c.get("Voters", {}).get("Total", {}).get("Total", 0)
                valid_votes = c.get("Votes", {}).get("Total Valid Votes Polled", 0)
                
                # --- [DATA FIX for Total Electors] ---
                # Get the correct total electors from the SUMMARY data
                total_electors = c.get("Electors", {}).get("Total", {}).get("Total", 0)
                # --- [END DATA FIX] ---
                
                # Update category from detailed parser (it's more reliable)
                c["Category"] = cand_data.get("Category", c.get("Category", "GENERAL"))

                for cand in cand_data["Candidates"]:
                    cand["Total Votes Polled In The Constituency"] = total_polled
                    cand["Valid Votes"] = valid_votes
                    
                    # --- [DATA FIX for Total Electors] ---
                    # Update the Total Electors for the candidate
                    # Use summary data if detailed parser found 0
                    if cand["Total Electors"] == 0:
                        cand["Total Electors"] = total_electors
                    # --- [END DATA FIX] ---
                    
                    # We can now calculate the final percentage
                    if valid_votes > 0:
                        cand["Over Total Valid Votes Polled In Constituency"] = round(
                            (cand["Votes Secured"]["Total"] / valid_votes) * 100, 2
                        )
                    else:
                        cand["Over Total Valid Votes Polled In Constituency"] = 0.0
                
                c["Candidates"] = cand_data["Candidates"]

                # --- [DATA FIX for Result Block] ---
                # Re-calculate Winner/Runner-Up from the detailed candidate list
                if c["Candidates"]:
                    try:
                        sorted_candidates = sorted(
                            c["Candidates"], 
                            key=lambda x: x["Votes Secured"]["Total"], 
                            reverse=True
                        )
                        
                        # Update Winner
                        if len(sorted_candidates) > 0:
                            winner = sorted_candidates[0]
                            c["Result"]["Winner"] = {
                                "Party": winner["Party Name"],
                                "Candidates": winner["Candidate Name"],
                                "Votes": winner["Votes Secured"]["Total"]
                            }
                        
                        # Update Runner-Up and Margin
                        if len(sorted_candidates) > 1:
                            runner_up = sorted_candidates[1]
                            c["Result"]["Runner-Up"] = {
                                "Party": runner_up["Party Name"],
                                "Candidates": runner_up["Candidate Name"],
                                "Votes": runner_up["Votes Secured"]["Total"]
                            }
                            c["Result"]["Margin"] = (
                                winner["Votes Secured"]["Total"] - runner_up["Votes Secured"]["Total"]
                            )
                        elif len(sorted_candidates) > 0: # Only a winner
                            c["Result"]["Runner-Up"] = {"Party": None, "Candidates": None, "Votes": 0}
                            c["Result"]["Margin"] = winner["Votes Secured"]["Total"]

                    except Exception as e:
                        print(f"Error calculating winner for {full_id}: {e}")
                # --- [END DATA FIX] ---

                merged_count += 1
            else:
                print(f"Warning: No detailed candidate data found for {c.get('Constituency')} (ID: {full_id})")
            
            # --- [SCHEMA FIX] ---
            # Clean up the temp key
            if "Summary_Candidate_Stats" in c:
                del c["Summary_Candidate_Stats"]
            # --- [END SCHEMA FIX] ---

        print(f"Merged detailed candidate data for {merged_count} constituencies.")
        
        # Final check
        if merged_count == len(parsed_summary):
             print(f"\nSuccess! Parsed and merged all {merged_count} constituencies.")
        else:
             print(f"\nWarning: Mismatched count! Parsed {len(parsed_summary)} summaries but merged {merged_count} candidate lists.")


        print(f"\nWriting final merged data to: {PDF_PATHS['output']}")
        with open(PDF_PATHS["output"], "w") as f:
            json.dump(parsed_summary, f, indent=4)
        print("JSON file written successfully.")

    except FileNotFoundError as e:
        print(f"Error: File not found. Make sure this file exists:")
        print(f"   {e.filename}")
    except Exception as e:
        print(f"An unexpected error occurred during 2009 parsing: {e}")
        import traceback
        traceback.print_exc()

# --------------------------------------------------------------------------
if _name_ == "_main_":
    run_2009_parse()
