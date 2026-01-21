import cv2
import os
import uuid
import numpy as np
from pdf2image import convert_from_path


def extract_photo(file_path, save_dir):
    """
    Extracts only the photo area from passport, excluding signature
    """

    os.makedirs(save_dir, exist_ok=True)

    # -----------------------------
    # LOAD IMAGE
    # -----------------------------
    if file_path.lower().endswith(".pdf"):
        pages = convert_from_path(file_path, dpi=300)
        if not pages:
            return None
        img = cv2.cvtColor(np.array(pages[0]), cv2.COLOR_RGB2BGR)
    else:
        img = cv2.imread(file_path)

    if img is None:
        return None

    # -----------------------------
    # PHOTO AREA DETECTION (EXCLUDING SIGNATURE)
    # -----------------------------
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = img.shape[:2]

    # Face detection to locate photo
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    faces = face_cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
    )

    if len(faces) > 0:
        # Use face to determine photo boundaries
        x, y, fw, fh = faces[0]
        
        # Photo area: face + reasonable padding (head to upper chest only)
        photo_x = max(0, x - fw//6)  # Small left padding
        photo_y = max(0, y - fh//4)  # Small top padding for hair
        photo_w = fw + fw//3         # Face width + 33% padding
        photo_h = fh + fh//2         # Face height + 50% for upper chest
        
        # Ensure we don't go beyond image boundaries
        photo_w = min(photo_w, w - photo_x)
        photo_h = min(photo_h, h - photo_y)
        
        photo_region = img[photo_y:photo_y + photo_h, photo_x:photo_x + photo_w]
    else:
        # Fallback: Extract standard passport photo area (top-left, smaller region)
        # Typical passport photo is about 2x2.5 inches, positioned top-left
        photo_w = min(w // 4, 200)  # Smaller width to avoid signature
        photo_h = min(h // 3, 250)  # Controlled height
        photo_x = w // 25           # Small left margin
        photo_y = h // 15           # Small top margin
        
        photo_region = img[photo_y:photo_y + photo_h, photo_x:photo_x + photo_w]

    # -----------------------------
    # SAVE PHOTO ONLY
    # -----------------------------
    filename = f"{uuid.uuid4().hex}_photo.jpg"
    save_path = os.path.join(save_dir, filename)
    cv2.imwrite(save_path, photo_region)

    return f"/uploads/photos/{filename}"
