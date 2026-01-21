from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import re

from processing.ocr import ocr_aadhaar
from processing.photo_extract import extract_photo
from werkzeug.utils import secure_filename

# ✅ NEW import (extra info OCR)
from processing.extra_info.address_ocr import extract_present_address

app = Flask(__name__)

# -----------------------------
# FOLDER CONFIG
# -----------------------------
UPLOAD_FOLDER = "uploads"
PHOTO_FOLDER = os.path.join("uploads", "photos")
EXTRA_INFO_FOLDER = os.path.join("uploads", "extra_info")  # ✅ NEW

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PHOTO_FOLDER, exist_ok=True)
os.makedirs(EXTRA_INFO_FOLDER, exist_ok=True)  # ✅ NEW


@app.route("/")
def index():
    return render_template("index.html")


# -----------------------------
# Helper: extract city from address
# -----------------------------
def extract_city_from_address(address):
    if not address:
        return ""

    city_keywords = [
        "Kukatpally", "Hyderabad", "Secunderabad"
    ]

    for city in city_keywords:
        if re.search(rf"\b{city}\b", address, re.IGNORECASE):
            return city

    return ""


# -----------------------------
# VISITOR ID OCR (UNCHANGED)
# -----------------------------
@app.route("/upload-id", methods=["POST"])
def upload_id():
    files = request.files.getlist("files")

    if not files:
        return jsonify({"error": "No file uploaded"}), 400

    visitor_file = files[0]
    filename = secure_filename(visitor_file.filename)
    visitor_path = os.path.join(UPLOAD_FOLDER, filename)
    visitor_file.save(visitor_path)2
    id_type = request.form.get("id_proof_type", "").strip()
    if id_type == "AADHAR CARD":
        data = ocr_aadhaar(visitor_path) or {}

    elif id_type == "VOTER ID":
        from processing.ocr_voter import ocr_voter_id
        data = ocr_voter_id(visitor_path) or {}

    elif id_type == "DRIVING LICENSE":
        from processing.ocr_dl import ocr_driving_license
        data = ocr_driving_license(visitor_path) or {}

    elif id_type == "PASSPORT":
        from processing.ocr_passport import ocr_passport
        data = ocr_passport(visitor_path) or {}

    else:
        data = {}

    photo_path = extract_photo(visitor_path, PHOTO_FOLDER)
    if photo_path:
        data["photo"] = photo_path

    if "address" in data:
        city = extract_city_from_address(data["address"])
        if city:
            data["city"] = city

    return jsonify(data)


# =====================================================
# ✅ EXTRA INFORMATION OCR (NEW & SEPARATE)
# =====================================================
@app.route("/ocr/extra-info", methods=["POST"])
def extra_info_ocr():
    file = request.files.get("address_proof")

    if not file or not file.filename:
        return jsonify({"error": "No file uploaded"}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(EXTRA_INFO_FOLDER, filename)
    file.save(save_path)

    data = extract_present_address(save_path)
    return jsonify(data)


# -----------------------------
# SAVE VISITOR DATA (UNCHANGED)
# -----------------------------
@app.route("/save-visitor", methods=["POST"])
def save_visitor():
    form_data = request.form.to_dict()
    saved_files = {}

    id_files = request.files.getlist("id_files")
    id_file_paths = []

    for f in id_files:
        if f and f.filename:
            filename = secure_filename(f.filename)
            path = os.path.join(UPLOAD_FOLDER, filename)
            f.save(path)
            id_file_paths.append(path)

    if id_file_paths:
        saved_files["id_files"] = id_file_paths

    photo = request.files.get("photo")
    if photo and photo.filename:
        photo_name = secure_filename(photo.filename)
        photo_path = os.path.join(PHOTO_FOLDER, photo_name)
        photo.save(photo_path)
        saved_files["photo"] = photo_path

    address_proof = request.files.get("present_address_file")
    if address_proof and address_proof.filename:
        addr_name = secure_filename(address_proof.filename)
        addr_path = os.path.join(EXTRA_INFO_FOLDER, addr_name)
        address_proof.save(addr_path)
        saved_files["address_proof"] = addr_path
        
        # ✅ AUTO-OCR the address proof
        try:
            address_data = extract_present_address(addr_path)
            if address_data.get("present_address"):
                form_data["extracted_present_address"] = address_data["present_address"]
                print(f"✅ Extracted address: {address_data['present_address']}")
        except Exception as e:
            print(f"❌ Address OCR failed: {e}")

    final_data = {
        "form_data": form_data,
        "files": saved_files
    }

    print("VISITOR DATA SAVED:")
    print(final_data)

    return "Data saved successfully"


# -----------------------------
# SERVE UPLOADED PHOTOS
# -----------------------------
@app.route("/uploads/photos/<filename>")
def uploaded_photo(filename):
    return send_from_directory(PHOTO_FOLDER, filename)


if __name__ == "__main__":
    app.run(debug=True)
