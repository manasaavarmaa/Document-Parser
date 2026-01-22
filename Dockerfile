FROM python:3.11

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    libzbar0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY Parser/ .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:$PORT"]
