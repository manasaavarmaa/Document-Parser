import cv2
import pytesseract
import re
import numpy as np
import os
from pdf2image import convert_from_path
from datetime import datetime
import pdfplumber

from processing.extra_info.address_ocr import enhance_image


# ==============================
# Main OCR function
# ==============================
def ocr_passport(pdf_path):
    text = ""

    os.makedirs("uploads/enhanced_pdf", exist_ok=True)

    # -------- Try text-based PDF --------
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
    except:
        pass

    # -------- OCR fallback (scanned PDFs) --------
    if len(text.strip()) < 50:
        pages = convert_from_path(pdf_path, dpi=300)

        for idx, page in enumerate(pages):
            img_np = np.array(page)

            save_path = os.path.join(
                "uploads/enhanced_pdf",
                f"passport_page_{idx + 1}.png"
            )

            img_final = enhance_image(img_np)
            cv2.imwrite(save_path, img_final)

            text += pytesseract.image_to_string(
                img_final,
                config="--psm 6"
            ) + "\n"

    return parse_passport_text(text)


# ==============================
# Parse passport text
# ==============================
def parse_passport_text(text):
    data = {}
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # ------------------------------------------------
    # PASSPORT NUMBER (FIXED FOR 8-DIGIT FORMAT)
    # ------------------------------------------------
    # Method 1: Look for "Passport no" pattern
    for i, line in enumerate(lines):
        if re.search(r"PASSPORT\s*NO", line.upper()):
            # Check same line after colon or space
            after_passport = re.split(r"PASSPORT\s*NO\s*:?\s*", line, flags=re.I)
            if len(after_passport) > 1 and after_passport[1].strip():
                passport_match = re.search(r"([A-Z]\d{7,8})", after_passport[1])
                if passport_match:
                    data["id_number"] = passport_match.group(1)
                    break
            
            # Check next line
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                passport_match = re.search(r"([A-Z]\d{7,8})", next_line)
                if passport_match:
                    data["id_number"] = passport_match.group(1)
                    break
    
    # Method 2: Look for any valid passport number pattern
    if "id_number" not in data:
        for line in lines:
            matches = re.findall(r"\b([A-Z]\d{7,8})\b", line)
            for match in matches:
                # Skip if surrounded by many letters (likely a name)
                if not re.search(rf"[A-Z]{{4,}}\s*{match}|{match}\s*[A-Z]{{4,}}", line):
                    data["id_number"] = match
                    break
            if "id_number" in data:
                break
    
    # Method 3: Broader search for passport patterns
    if "id_number" not in data:
        # Look for patterns like Z7994266 (1 letter + 7-8 digits)
        all_text = " ".join(lines)
        passport_patterns = re.findall(r"\b([A-Z]\d{7,8})\b", all_text)
        print(f"[DEBUG] Found passport patterns: {passport_patterns}")
        if passport_patterns:
            data["id_number"] = passport_patterns[0]  # Take first match


    # ------------------------------------------------
    # NAME (MRZ – UNCHANGED)
    # ------------------------------------------------
    for line in lines:
        if line.startswith("P<IND") and "<<" in line:
            parts = line.replace("P<IND", "").split("<<")
            surname = parts[0].replace("<", " ").strip()
            given = parts[1].replace("<", " ").strip()
            data["name"] = f"{given} {surname}".upper()
            break

    # ------------------------------------------------
    # DATE OF BIRTH (AVOID ISSUE/EXPIRY DATES)
    # ------------------------------------------------
    # Search all lines for date patterns but avoid issue/expiry dates
    for i, line in enumerate(lines):
        print(f"[DEBUG] Line {i}: '{line}'")
        # Look for any date pattern in any line
        dob_match = re.search(r"(\d{1,2}\s*[/-]\s*\d{1,2}\s*[/-]\d{4})", line)
        if dob_match:
            date_found = dob_match.group(1)
            print(f"[DEBUG] Found date pattern in line {i}: '{date_found}'")
            
            # Check if this is an issue/expiry date (skip if so)
            line_upper = line.upper()
            if any(keyword in line_upper for keyword in ["ISSUE", "EXPIRY", "VALID", "EXPIRE"]):
                print(f"[DEBUG] Skipping issue/expiry date: {date_found}")
                continue
            
            # Check year - birth dates should be older (before 2010)
            year = int(date_found.split('/')[-1].strip())
            if year > 2010:
                print(f"[DEBUG] Skipping recent date (likely issue/expiry): {date_found}")
                continue
            
            # Check if this line or nearby lines mention birth
            context_lines = []
            for j in range(max(0, i-2), min(len(lines), i+3)):
                context_lines.append(lines[j].upper())
            
            context_text = " ".join(context_lines)
            if "BIRTH" in context_text:
                dob_str = date_found.replace('-', '/').replace(' ', '')
                parts = dob_str.split('/')
                if len(parts) == 3:
                    data["dob"] = f"{parts[0].zfill(2)}/{parts[1].zfill(2)}/{parts[2]}"
                    print(f"[DEBUG] Set DOB: {data['dob']}")
                    
                    # Calculate age
                    try:
                        birth_date = datetime.strptime(data["dob"], "%d/%m/%Y")
                        today = datetime.today()
                        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                        data["age"] = age
                        print(f"[DEBUG] Calculated age: {age}")
                    except:
                        pass
                    break
    # ------------------------------------------------
    # YEAR OF BIRTH (FALLBACK)
    # ------------------------------------------------
    if "dob" not in data:
        all_text = " ".join(lines).upper()
        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", all_text)
        if year_match:
            data["year_of_birth"] = year_match.group(1)
            # Calculate approximate age from year
            try:
                birth_year = int(year_match.group(1))
                current_year = datetime.now().year
                data["age"] = current_year - birth_year
            except:
                pass

    # ------------------------------------------------
    # GENDER (FIXED FOR SEX + F FORMAT)
    # ------------------------------------------------
    for i, line in enumerate(lines):
        line_clean = line.strip().upper()
        
        # Look for "SEX" line
        if "SEX" in line_clean:
            print(f"[DEBUG] Found SEX in line {i}: '{line_clean}'")
            
            # Check next line for F/M
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip().upper()
                print(f"[DEBUG] Next line {i+1}: '{next_line}'")
                
                if "F" in next_line:
                    data["gender"] = "Female"
                    print(f"[DEBUG] Set gender to Female")
                    break
                elif "M" in next_line:
                    data["gender"] = "Male"
                    print(f"[DEBUG] Set gender to Male")
                    break
            
            # Also check same line for F/M after SEX
            if "F" in line_clean and "SEX" in line_clean:
                data["gender"] = "Female"
                break
            elif "M" in line_clean and "SEX" in line_clean:
                data["gender"] = "Male"
                break

    
    # ------------------------------------------------
    # ADDRESS (UNCHANGED – PIN ANCHORED)
    # ------------------------------------------------
    full_text = " ".join(lines).upper()
    full_text = re.sub(r"[^A-Z0-9 ]", " ", full_text)
    full_text = re.sub(r"\s+", " ", full_text)
    
    pin_match = re.search(r"\bPIN\s*([0-9]{6})\b", full_text)
    if pin_match:
        pin = pin_match.group(1)
        before_pin = full_text[:pin_match.start()]

        addr_match = re.search(
            r"(MIG\s*\d+|FLAT\s*NO\s*\d+|HOUSE\s*NO\s*\d+|D\s*NO\s*\d+).*?$",
            before_pin
        )

        if addr_match:
            address = addr_match.group()

            address = re.sub(
                r"\b(SEEM|ST|ME|ND|IA|HES|KAS|PD|FH|PR|EE|AE|GE|SE|ORS|TT|UY|OE|GT|ES|VOWS|Y|TEE|WE|ID|LY|EOS|E|DR|VE|OER|EO)\b",
                "",
                address
            )

            address = re.sub(r"\b(?!\d{6}\b)\d\b", "", address)
            address = re.sub(r"\s*,\s*", ", ", address)
            address = re.sub(r"\s+", " ", address).strip()

            address = f"{address}, PIN {pin}"
            data["address"] = address.title()

            if "TELANGANA" in full_text:
                data["state"] = "Telangana"

            if any(c in full_text for c in ["KUKATPALLY", "MEDCHAL", "HYDERABAD"]):
                data["city"] = "Hyderabad"

    # ------------------------------------------------
    # COUNTRY
    # ------------------------------------------------
    data["country"] = "India"

    print(f"[PASSPORT_OCR] Final extracted data: {data}")
    return data


# ==============================
# TEST
# ==============================
if __name__ == "__main__":
    print(ocr_passport("any_name.pdf"))
