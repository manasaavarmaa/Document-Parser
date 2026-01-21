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


def ocr_driving_license(file_path):
    data = {}

    # ----------------------------------
    # ENHANCED TEXT EXTRACTION
    # ----------------------------------
    full_text = extract_text_enhanced(file_path)
    text = re.sub(r"\s+", " ", full_text)

    # ----------------------------------
    # DL NUMBER
    # ----------------------------------
    dl = re.search(r"License No\.?\s*:\s*([A-Z0-9]+)", text, re.I)
    if dl:
        data["dl_number"] = dl.group(1)

    # ----------------------------------
    # NAME
    # ----------------------------------
    name = re.search(r"Name\s*:\s*([A-Za-z ]+)", text)
    if name:
        nm = name.group(1).strip()
        # Remove any trailing words that look like field labels
        nm = re.sub(r"\b(DOB|Date|Birth|S/W/D|Father|Mother|Address)\b.*$", "", nm, flags=re.I).strip()
        data["name"] = nm.title()

    # ----------------------------------
    # DATE OF BIRTH
    # ----------------------------------
    # First try: Look for "DOB :" pattern
    dob = re.search(r"DOB\s*:\s*(\d{2}-\d{2}-\d{4})", text)
    if dob:
        data["dob"] = dob.group(1).replace('-', '/')
    
    # Second try: Look for "Date of Birth" on one line, date on next line
    if "dob" not in data:
        lines = full_text.split('\n')
        for i, line in enumerate(lines):
            if re.search(r'Date\s*of\s*Birth', line, re.I):
                # Check next few lines for date
                for j in range(i+1, min(i+4, len(lines))):
                    next_line = lines[j].strip()
                    # Look for date pattern in next line
                    date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})', next_line)
                    if date_match:
                        dob_date = date_match.group(1).replace('-', '/')
                        data["dob"] = dob_date
                        break
                if "dob" in data:
                    break
    
    # Third try: Look for any date that could be DOB
    if "dob" not in data:
        all_dates = re.findall(r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})', text)
        for date_str in all_dates:
            try:
                from datetime import datetime
                # Try to parse and validate as birth date
                test_date = datetime.strptime(date_str.replace('-', '/'), '%d/%m/%Y')
                if 1950 <= test_date.year <= 2010:  # Reasonable birth year range
                    data["dob"] = date_str.replace('-', '/')
                    break
            except:
                continue
    
    # Calculate age if DOB found
    if "dob" in data:
        try:
            from datetime import datetime
            birth_date = datetime.strptime(data["dob"], "%d/%m/%Y")
            today = datetime.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            data["age"] = str(age)
        except:
            pass

    # ----------------------------------
    # ISSUE & EXPIRY (OPTIONAL)
    # ----------------------------------
    issue = re.search(r"Date of Issue\s*:\s*(\d{2}-\d{2}-\d{4})", text)
    expiry = re.search(r"Date of Expiry\s*:\s*(\d{2}-\d{2}-\d{4})", text)
    if issue:
        data["issue_date"] = issue.group(1)
    if expiry:
        data["expiry_date"] = expiry.group(1)

    # ----------------------------------
    # FATHER / HUSBAND NAME
    # ----------------------------------
    parent = re.search(r"S/W/D\s*:\s*([A-Za-z ]+)", text)
    if parent:
        data["parent_name"] = parent.group(1).strip().title()

    # ----------------------------------
    # ADDRESS (PERMANENT ADDRESS BLOCK)
    # ----------------------------------
    # Try multiple address patterns
    address = None
    
    # Pattern 1: Look for "Permanent Address :"
    addr_match = re.search(r"Permanent\s*Address\s*:\s*([^\n]*(?:\n[^\n]*)*?)(?=\s*(?:Digitally|Note:|Date\s*of\s*Issue|$))", full_text, re.I | re.S)
    if addr_match:
        address = addr_match.group(1).strip()
    
    # Pattern 2: Look for just "Address :"
    if not address:
        addr_match = re.search(r"Address\s*:\s*([^\n]*(?:\n[^\n]*)*?)(?=\s*(?:Digitally|Note:|Date\s*of\s*Issue|$))", full_text, re.I | re.S)
        if addr_match:
            address = addr_match.group(1).strip()
    
    # Pattern 3: Simple line-by-line approach
    if not address:
        lines = full_text.split('\n')
        collecting = False
        addr_lines = []
        
        for line in lines:
            line = line.strip()
            if re.match(r".*Permanent\s*Address\s*:", line, re.I):
                collecting = True
                # Extract address part from this line
                addr_part = re.sub(r".*Permanent\s*Address\s*:\s*", "", line, flags=re.I)
                if addr_part:
                    addr_lines.append(addr_part)
                continue
            
            if collecting:
                if re.match(r".*(Digitally|Note:|Date\s*of\s*Issue)", line, re.I):
                    break
                if line:
                    addr_lines.append(line)
        
        if addr_lines:
            address = " ".join(addr_lines)

    if address:
        # Clean up the address
        address = re.sub(r"\s+", " ", address)
        
        # Remove duplicate address - split on "Permanent :" and take first part
        if "Permanent :" in address:
            address = address.split("Permanent :")[0].strip()
        
        # Remove duplicate "Address" word
        address = re.sub(r"\s+Address\s+", " ", address, flags=re.I)
        
        # Remove trailing unwanted text
        address = re.sub(r"\s*(Digitally\s*signed.*|Note:.*|Date\s*of\s*Issue.*|Date\s*of\s*Expiry.*|License.*)$", "", address, flags=re.I).strip()
        
        if address:
            data["address"] = address

            # PIN
            pin = re.search(r"\b\d{6}\b", address)
            if pin:
                data["pincode"] = pin.group(0)

            # CITY (KNOWN FROM PDF)
            addr_upper = address.upper()
            if "KUKATPALLY" in addr_upper or "KPHB" in addr_upper:
                data["city"] = "Kukatpally"
            elif "HYDERABAD" in addr_upper:
                data["city"] = "Hyderabad"
            elif "SECUNDERABAD" in addr_upper:
                data["city"] = "Secunderabad"

            # STATE (DL is Telangana)
            if "TELANGANA" in addr_upper:
                data["state"] = "Telangana"

    # ----------------------------------
    # COUNTRY
    # ----------------------------------
    data["country"] = "India"

    print(f"[DL_OCR] Final extracted data: {data}")
    return data
