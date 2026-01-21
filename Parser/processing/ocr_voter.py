import re
import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path
import pdfplumber
from datetime import datetime


# ================= IMAGE ENHANCEMENT =================
def enhance_image_quality(img):
    """Enhanced image preprocessing for better OCR"""
    h, w = img.shape[:2]
    
    # Upscale if too small
    if h < 900 or w < 600:
        scale_factor = max(900/h, 600/w)
        new_h, new_w = int(h * scale_factor), int(w * scale_factor)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Denoise
    gray = cv2.fastNlMeansDenoising(gray, None, 30, 7, 21)
    
    # Enhance contrast
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    
    # Adaptive threshold
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 11
    )
    
    return thresh


def extract_text_enhanced(file_path):
    """Extract text with image enhancement"""
    text = ""
    
    try:
        # Try PDF text extraction first
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
    except:
        pass
    
    # If PDF text extraction failed or insufficient, use OCR
    if len(text.strip()) < 50:
        try:
            if file_path.lower().endswith('.pdf'):
                pages = convert_from_path(file_path, dpi=300)
                for page in pages:
                    img = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
                    enhanced_img = enhance_image_quality(img)
                    text += pytesseract.image_to_string(enhanced_img, config="--psm 6") + "\n"
            else:
                img = cv2.imread(file_path)
                if img is not None:
                    enhanced_img = enhance_image_quality(img)
                    text = pytesseract.image_to_string(enhanced_img, config="--psm 6")
        except Exception as e:
            print(f"OCR failed: {e}")
    
    return text


def clean_address_tokens(text: str) -> str:
    """
    Removes OCR garbage tokens while preserving legitimate address components.
    """
    tokens = text.split()
    clean_tokens = []

    for t in tokens:
        t_clean = t.strip(",.-")

        # Skip empty tokens
        if not t_clean:
            continue

        # Keep numbers (house numbers, pin codes)
        if t_clean.isdigit():
            clean_tokens.append(t)
            continue

        # Keep mixed alphanumeric (like "123A", "H-456")
        if re.search(r'\d', t_clean) and re.search(r'[A-Za-z]', t_clean):
            clean_tokens.append(t)
            continue

        # Drop OCR artifacts: single letters or 2-letter combinations that are clearly broken words
        if len(t_clean) <= 2 and t_clean.isupper():
            continue

        # Keep legitimate words (3+ chars or mixed case)
        clean_tokens.append(t)

    return " ".join(clean_tokens)


def ocr_voter_id(file_path):
    data = {}

    # ----------------------------------
    # ENHANCED TEXT EXTRACTION
    # ----------------------------------
    full_text = extract_text_enhanced(file_path)
    clean_text = re.sub(r"\s+", " ", full_text)

    # ----------------------------------
    # EPIC NUMBER
    # ----------------------------------
    epic = re.search(r"\b([A-Z]{3}\d{7})\b", clean_text)
    if epic:
        data["id_number"] = epic.group(1)

    # ----------------------------------
    # NAME (STRICT)
    # ----------------------------------
    name = re.search(r"Name\s*:\s*([A-Za-z ]+)", clean_text)
    if name:
        nm = name.group(1)
        nm = re.sub(r"\b[A-Z]{3,}\b.*$", "", nm).strip()
        data["name"] = nm

    # ----------------------------------
    # GENDER
    # ----------------------------------
    gender = re.search(r"\b(Male|Female|Transgender)\b", clean_text)
    if gender:
        data["gender"] = gender.group(1)

    # ----------------------------------
    # DOB & AGE (STRICT – VOTER ID SAFE)
    # ----------------------------------
    dob_match = re.search(
        r"Date of Birth\s*/\s*Age\s*:\s*(\d{2}-\d{2}-\d{4})",
        clean_text,
        re.I
    )

    if dob_match:
        dob_str = dob_match.group(1)

    # store DOB in frontend-compatible key
    data["dob"] = dob_str.replace("-", "/")

    try:
        birth_date = datetime.strptime(dob_str, "%d-%m-%Y")
        today = datetime.today()
        age = today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )
        data["age"] = str(age)
    except Exception:
        pass
    # ==================================================
    # ADDRESS — MULTI-LINE SAFE EXTRACTION (VOTER PDF)
    # ==================================================
    address_lines = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

        lines = text.split("\n")
        collecting = False

        for line in lines:
            line = line.strip()
            if re.match(r"Address\s*:", line, re.I):
                collecting = True
                line = re.sub(r"Address\s*:", "", line, flags=re.I).strip()

            # Stop when next section starts
            if collecting and re.match(
                r"(Name|Father|Mother|Gender|Age|DOB|Date of Birth|Electoral|EPIC|Scan|Download)",
                line,
                re.I
            ):
                collecting = False
                break

            if collecting and line:
                address_lines.append(line)

            if address_lines:
                break


# --------------------------------------------------
# CLEAN + NORMALIZE ADDRESS
# --------------------------------------------------
    if address_lines:
        addr = ", ".join(address_lines)

    # Remove EPIC number if leaked
        addr = re.sub(r"\b[A-Z]{3}\d{7}\b", "", addr)

    # 🔥 REMOVE TELUGU / NON-ENGLISH TEXT
        addr = re.sub(r"[^\x00-\x7F]+", " ", addr)

    # Fix common OCR word breaks
        addr = re.sub(r"\bLNA\b", "LANE", addr, flags=re.I)
        addr = re.sub(r"\bEDCHAL\b", "MEDCHAL", addr, flags=re.I)
        addr = re.sub(r"\bATP\b", "AT POST", addr, flags=re.I)

    # Normalize spaces & commas
        addr = re.sub(r"\s+", " ", addr)
        addr = re.sub(r",\s*,", ",", addr)

        data["address"] = addr.strip(" ,")

    # ----------------------------------
    # CITY (FROM ADDRESS)
    # ----------------------------------
        addr_upper = addr.upper()

        if "KPHB" in addr_upper or "KUKATPALLY" in addr_upper:
            data["city"] = "Kukatpally"
        elif "BALNAGAR" in addr_upper:
            data["city"] = "Balnagar"
        elif "HYDERABAD" in addr_upper:
            data["city"] = "Hyderabad"

        # ----------------------------------
        # STATE (FROM ADDRESS)
        # ----------------------------------
        if "TELANGANA" in addr_upper:
            data["state"] = "Telangana"

    print(f"[VOTER_OCR] Final extracted data: {data}")
    return data

