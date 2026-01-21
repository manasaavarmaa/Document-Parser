from lxml import etree
from datetime import datetime
import base64

def parse_aadhaar_xml(xml_string):
    root = etree.fromstring(xml_string.encode())

    uid = root.attrib.get("uid", "")
    name = root.attrib.get("name", "")
    gender = root.attrib.get("gender", "")
    yob = root.attrib.get("yob", "")
    dob = root.attrib.get("dob", "")

    address_parts = [
        root.attrib.get("house", ""),
        root.attrib.get("street", ""),
        root.attrib.get("lm", ""),
        root.attrib.get("loc", ""),
        root.attrib.get("vtc", ""),
        root.attrib.get("po", ""),
        root.attrib.get("dist", ""),
        root.attrib.get("state", ""),
        root.attrib.get("pc", "")
    ]

    address = ", ".join([p for p in address_parts if p])

    photo = root.attrib.get("photo", "")

    age = ""
    if yob:
        age = str(datetime.now().year - int(yob))

    return {
        "name": name,
        "gender": "Male" if gender == "M" else "Female",
        "dob": dob if dob else yob,
        "age": age,
        "id_number": uid,
        "address": address,
        "photo": photo
    }
