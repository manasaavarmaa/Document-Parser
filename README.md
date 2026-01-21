# OCR Document Processing Service

## Overview
This project is an OCR-based document processing application designed to extract text and structured information from document images. It combines image enhancement, OCR (both traditional and deep-learning-based), and post-processing logic to produce clean, usable outputs.

The system is built as a lightweight web service with a clear separation between preprocessing, OCR execution, and data mapping, making it easy to maintain and extend.

---

## Features
- Image enhancement and preprocessing for better OCR accuracy  
- Text extraction using multiple OCR approaches  
- Structured field mapping from raw OCR output  
- Photo and region extraction from documents  
- Web-based interface for document upload and processing  

---

## Tech Stack
- **Python**
- **Flask** (web service)
- **OCR Engines** (traditional and DL-based)
- **OpenCV / Image Processing**
- **HTML, CSS, JavaScript** (basic frontend)

---

## Project Structure
```
Parser/
├── app.py # Main Flask application
├── processing/
│ ├── ocr.py # Traditional OCR logic
│ ├── ocr_dl.py # Deep learning based OCR
│ ├── enhance.py # Image preprocessing & enhancement
│ ├── field_mapper.py # Mapping extracted text to fields
│ ├── photo_extract.py # Photo/region extraction
│ └── extra_info/ # Supporting processing utilities
├── static/
│ ├── styles.css # Frontend styling
│ └── js/ # Frontend scripts
├── templates/ # HTML templates
├── requirements.txt # Python dependencies
└── README.md

```
---

## Workflow
1. Document image is uploaded through the web interface  
2. Image enhancement and preprocessing are applied  
3. OCR engine extracts raw text from the document  
4. Post-processing cleans and structures the text  
5. Field mapping generates organized output  

---

## Setup Instructions
```bash
pip install -r requirements.txt
Run Application
python app.py
The service will start locally and expose endpoints for document processing.

Notes
Uses sample or synthetic documents only

Core logic is included; sensitive configurations are excluded

Designed to demonstrate OCR pipeline architecture and processing flow

Future Improvements
Multi-language OCR support

Improved accuracy using model fine-tuning

Export results in structured formats (JSON, CSV)

API-based integration support
