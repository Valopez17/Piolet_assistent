FROM python:3.11-slim

# Instalar dependencias del sistema para OCR y PDFs
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

#CMD ["python", "app.py"] 
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:$PORT"]