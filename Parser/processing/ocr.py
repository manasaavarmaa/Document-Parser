import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import re
from datetime import datetime
import spacy

nlp = spacy.load("en_core_web_trf")

# ================= IMAGE PREPROCESSING =================
def preprocess_image(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    gray = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 2
    )
    return gray

# ================= TEXT EXTRACTION =================
def extract_text(file_path):
    text = ""
    images = convert_from_path(file_path, dpi=300) if file_path.lower().endswith(".pdf") else [Image.open(file_path)]
    for img in images:
        img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        img = preprocess_image(img)
        text += pytesseract.image_to_string(img, lang="eng")
    return text

# ================= AGE =================
def calculate_age(dob):
    try:
        dob_dt = datetime.strptime(dob, "%d/%m/%Y")
        today = datetime.today()
        return today.year - dob_dt.year - ((today.month, today.day) < (dob_dt.month, dob_dt.day))
    except:
        return ""

# ================= NAME =================
def extract_name(text):
    blacklist = [
        "government","india","uidai","aadhaar","address","dob",
        "male","female","vid","authority","download","year",
        "state","district","pin","pincode"
    ]

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    candidates = []

    for i, line in enumerate(lines):
        clean = re.sub(r"[^A-Za-z ]", "", line).strip()
        low = clean.lower()

        if len(clean.split()) < 2 or len(clean.split()) > 4:
            continue
        if any(b in low for b in blacklist):
            continue
        if not re.search(r"[aeiou]", low):
            continue

        score = len(clean.split())
        for j in range(max(0, i-3), min(len(lines), i+3)):
            if re.search(r"(dob|male|female)", lines[j], re.I):
                score += 5
                break

        candidates.append((score, clean.title()))

    return max(candidates)[1] if candidates else ""

# ================= STATES =================
INDIAN_STATES = [
    "Andhra Pradesh","Arunachal Pradesh","Assam","Bihar","Chhattisgarh",
    "Delhi","Goa","Gujarat","Haryana","Himachal Pradesh","Jharkhand",
    "Karnataka","Kerala","Madhya Pradesh","Maharashtra","Odisha",
    "Punjab","Rajasthan","Tamil Nadu","Telangana",
    "Uttar Pradesh","West Bengal"
]

# ================= FULL ADDRESS EXTRACTION (FINAL) =================
def extract_full_address(text):
    parts = re.split(r'[\n,]', text)

    STOP_PHRASES = [
        "your aadhaar no",
        "aadhaar no",
        "uidai",
        "government of india",
        "your aadhaar",
        "downloaded on",
        "issue date",
        "qr code",
        "scan qr",
        "help@uidai",
        "www.uidai.gov.in"
    ]

    address = []
    started = False

    for part in parts:
        line = re.sub(r"\s+", " ", part).strip()
        low = line.lower()

        # 🔴 BLOCK Aadhaar junk
        if any(stop in low for stop in STOP_PHRASES):
            continue

        if len(line) < 4:
            continue

        # 🔹 START only at relation line
        if re.search(r'\b(d/o|s/o|c/o|w/o)\b', low):
            started = True

        if not started:
            continue

        # 🔹 STOP at Aadhaar disclaimer
        if "aadhaar is proof" in low:
            break

        # 🔹 HARD GARBAGE FILTER
        if (
            len(re.findall(r'[A-Z]', line)) > len(line) * 0.45 or
            not re.search(r'[a-z]{3,}', low)
        ):
            continue

        # 🔹 ACCEPT ONLY VALID ADDRESS CONTENT
        if (
            re.search(r'\b(d/o|s/o|c/o|w/o)\b', low) or
            re.search(r'\b\d+[-/]\d+\b', low) or
            re.search(r'\bplot\b|\bhouse\b|\bno\b', low) or
            re.search(r'\bnagar\b|\bcolony\b|\blayout\b', low) or
            re.search(r'\bnear\b|\bear\b|\btemple\b', low) or
            re.search(r'\bvtc\b|\bvillage\b', low) or
            re.search(r'\bdistrict\b', low) or
            re.search(r'\bstate\b', low) or
            re.search(r'\bpin\b', low)
        ):
            address.append(line)

    # 🔹 CLEAN + DEDUP (ORDER PRESERVED)
    final = []
    seen = set()

    for l in address:
        l = re.sub(r"[^\w\s,:/-]", "", l).strip(", ")
        if l.lower() not in seen:
            final.append(l)
            seen.add(l.lower())

    return ", ".join(final)

# ================= MOBILE =================
def extract_mobile(text):
    if not text:
        return ""

    # Normalize spaces and newlines
    text = re.sub(r"\s+", " ", text)

    # Look ONLY for Mobile: <number>
    match = re.search(
        r"mobile\s*[:\-]?\s*([0-9\s\-]{10,})",
        text,
        re.I
    )

    if match:
        digits = re.sub(r"\D", "", match.group(1))
        if len(digits) == 10:
            return digits

    return ""
# ================= AADHAAR NUMBER (BLOCK VID) =================
def extract_aadhaar_number(text):
    for m in re.finditer(r"\b\d{4}\s\d{4}\s\d{4}\b", text):
        ctx = text[max(0, m.start()-25):m.start()].lower()
        if "vid" not in ctx:
            return m.group()
    return ""

# ================= OCR AADHAAR =================
def ocr_aadhaar(file_path):
    raw_text = extract_text(file_path)
    data = {}

    data["name"] = extract_name(raw_text)

    dob = re.search(r"(DOB|Date of Birth)\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})", raw_text, re.I)
    if dob:
        data["dob"] = dob.group(2)
        data["age"] = calculate_age(dob.group(2))

    if re.search(r"\bFemale\b", raw_text, re.I):
        data["gender"] = "Female"
    elif re.search(r"\bMale\b", raw_text, re.I):
        data["gender"] = "Male"

    mobile = extract_mobile(raw_text)
    if mobile:
        data["mobile"] = mobile
        
    aadhaar = extract_aadhaar_number(raw_text)
    if aadhaar:
        data["aadhaar_number"] = aadhaar
    # 🔥 FULL ADDRESS FIRST
    address = extract_full_address(raw_text)

    if not address:
        components = extract_full_address(raw_text)
        address = extract_full_address(components)

    if address:
        data["address"] = address

    data["country"] = "India"
    data["state"] = "Telangana"
    INDIAN_CITIES = [
        "Hyderabad", "Secunderabad", "Kukatpally","Qutbullapur","Miyapur",
        "Ameerpet","Gachibowli","Madhapur","Uppal","LB Nagar","Dilsukhnagar",
        "Kompally","Nizampet","Bachupally","Manikonda","Kondapur","Jubilee Hills",
        "Malkajgiri","Hayathnagar","Nagole","Tolichowki","Patancheru","Shamshabad"
    ]
    for city in INDIAN_CITIES:
        if re.search(rf"\b{city}\b", address, re.I):
            data["city"] = city
            break

    print(f"[AADHAAR_OCR] Final extracted data: {data}")
    return data
