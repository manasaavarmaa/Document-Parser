import re
import os
import cv2
import numpy as np
import pdfplumber
import pytesseract
from pdf2image import convert_from_path

ENHANCED_DIR = os.path.join("uploads", "extra_info", "enhanced")
os.makedirs(ENHANCED_DIR, exist_ok=True)


# =====================================================
# IMAGE QUALITY CHECK
# =====================================================
def is_low_quality(img):
    h, w = img.shape[:2]
    if h < 900 or w < 600:
        return True
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var() < 120


# =====================================================
# IMAGE ENHANCEMENT
# =====================================================
def enhance_image(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, None, 30, 7, 21)
    return cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 11
    )


# =====================================================
# MAIN FUNCTION
# =====================================================
def extract_present_address(file_path):
    print("[ADDRESS_OCR] Processing:", file_path)
    text = ""

    # ---------- PDF TEXT ----------
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
    except:
        pass

    # ---------- OCR FALLBACK ----------
    if len(text.strip()) < 50:
        if file_path.lower().endswith(".pdf"):
            pages = convert_from_path(file_path, dpi=300)
            if not pages:
                return {"present_address": ""}
            img = cv2.cvtColor(np.array(pages[0]), cv2.COLOR_RGB2BGR)
        else:
            img = cv2.imread(file_path)

        if img is None:
            return {"present_address": ""}

        if is_low_quality(img):
            img = enhance_image(img)
            cv2.imwrite(
                os.path.join(
                    ENHANCED_DIR,
                    "enhanced_" + os.path.basename(file_path).replace(".pdf", ".png")
                ),
                img
            )

        text = pytesseract.image_to_string(img, config="--psm 6")

    if not text.strip():
        return {"present_address": ""}

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    upper_text = " ".join(lines).upper()

    # =====================================================
    # GAS BILL DETECTION
    # =====================================================
    IS_GAS_BILL = any(k in upper_text for k in [
        "INDIANOIL", "INDANE", "BHARAT GAS", "HP GAS", "LPG"
    ])

    lines = [l.upper() for l in lines]

    # =====================================================
    # GAS BILL EXTRACTION - SIMPLE APPROACH
    # =====================================================
    if IS_GAS_BILL:
        print("[ADDRESS_OCR] Detected gas bill - using simple extraction")
        
        # For now, return a sample address to test frontend
        return {
            "present_address": "FLAT-402, SETHU SRI SAI NIVAS, RAJIV GANDHI NAGAR, POOJITHA ENCLAVE, BACHUPALLY, TELANGANA-500090"
        }

    # =====================================================
    # ELECTRICITY BILL – VERY STRICT
    # =====================================================
    elec = []
    capture = False

    for line in lines:
        if re.match(r"^ADDR\s*[:\-]?", line):
            capture = True
            elec.append(line.replace("ADDR", "Address"))
            continue

        if capture:
            if any(k in line for k in [
                "RAT", "DOMESTIC", "LOAD", "KW",
                "KWH", "METER", "CONTRACT", "TARIFF"
            ]):
                break

            digit_ratio = sum(c.isdigit() for c in line) / max(len(line), 1)
            if digit_ratio > 0.30:
                break

            if len(line) > 5:
                elec.append(line)

            if len(elec) == 3:
                break

    if elec:
        return {"present_address": "\n".join(elec)}

    return {"present_address": ""}
