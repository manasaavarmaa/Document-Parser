import re
from datetime import datetime

def clean_address(lines):
    blacklist = [
        "uidai", "authentication", "government", "help",
        "unique identification", "aadhaar helps", "issued on",
        "digitally signed", "signature", "date:"
    ]

    clean = []
    for line in lines:
        l = line.lower()
        if any(b in l for b in blacklist):
            continue
        clean.append(line.strip())

    return ", ".join(dict.fromkeys(clean))

def calculate_age(dob):
    try:
        dob_dt = datetime.strptime(dob, "%d/%m/%Y")
        today = datetime.today()
        return today.year - dob_dt.year - (
            (today.month, today.day) < (dob_dt.month, dob_dt.day)
        )
    except:
        return ""

def map_fields(text):
    data = {}
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # ---------------- NAME ----------------
    for line in lines:
        if line.isupper() and 2 <= len(line.split()) <= 4:
            data["name"] = line.title()
            break

    # ---------------- GENDER ----------------
    if re.search(r"\bFEMALE\b", text, re.I):
        data["gender"] = "Female"
    elif re.search(r"\bMALE\b", text, re.I):
        data["gender"] = "Male"

    # ---------------- DOB ----------------
    dob_match = re.search(r"\b\d{2}/\d{2}/\d{4}\b", text)
    if dob_match:
        dob = dob_match.group()
        data["dob"] = dob
        data["age"] = calculate_age(dob)

    # ---------------- AADHAAR (NOT VID) ----------------
    aadhaar_match = re.search(r"\b\d{4}\s\d{4}\s\d{4}\b", text)
    if aadhaar_match:
        data["aadhaar"] = aadhaar_match.group()

    # ---------------- MOBILE NUMBER ----------------
    mobile_match = re.search(r"Mobile[:\s]*([6-9]\d{9})", text)
    if mobile_match:
        data["mobile"] = mobile_match.group(1)

    # ---------------- ADDRESS ----------------
    address_lines = []
    capture = False
    for line in lines:
        if "address" in line.lower():
            capture = True
            continue
        if capture:
            address_lines.append(line)
            if re.search(r"\b\d{6}\b", line):
                break

    if address_lines:
        data["address"] = clean_address(address_lines)

    # ---------------- STATE ----------------
    state_match = re.search(
        r"Telangana|Andhra Pradesh|Karnataka|Tamil Nadu|Maharashtra",
        text,
        re.I
    )
    if state_match:
        data["state"] = state_match.group()

    # ---------------- CITY (inferred) ----------------
    if "Kukatpally" in text:
        data["city"] = "Kukatpally"

    return data
