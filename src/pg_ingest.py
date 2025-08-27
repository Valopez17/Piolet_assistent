#!/usr/bin/env python3
"""
Ingesta de PDFs, Markdown y TXT para Piolet Assistant
"""
import os
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
from openai import OpenAI
import logging
from typing import List, Dict, Any
import pdfplumber
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
import glob
import pathlib
import hashlib

# Configuración
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DATABASE_URL = os.getenv("DATABASE_URL")

def get_embedding(text: str) -> List[float]:
    response = client.embeddings.create(model="text-embedding-3-small", input=text)
    return response.data[0].embedding

def clean_text(text: str) -> str:
    if not text:
        return ""
    lines = text.split('\n')
    cleaned_lines = [line.strip() for line in lines if line.strip() and len(line.strip()) > 3]
    return '\n'.join(cleaned_lines)

def split_text_into_chunks(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """Divide texto en chunks usando RecursiveCharacterTextSplitter"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    return splitter.split_text(text)

def extract_text_from_pdf(pdf_path: str) -> str:
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text_parts = []
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return clean_text('\n'.join(text_parts))
    except Exception as e:
        logger.error(f"Error extrayendo texto de {pdf_path}: {e}")
        return ""

def extract_text_from_file(file_path: str) -> str:
    """Extrae texto de PDF, Markdown o TXT"""
    suffix = pathlib.Path(file_path).suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(file_path)
    else:  # Markdown o TXT
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            return clean_text(text)
        except Exception as e:
            logger.error(f"Error leyendo {file_path}: {e}")
            return ""

def process_file(file_path: str) -> List[Dict[str, Any]]:
    logger.info(f"Procesando archivo: {file_path}")
    
    text = extract_text_from_file(file_path)
    if not text.strip():
        logger.warning(f"Archivo vacío: {file_path}")
        return []
    
    chunks = split_text_into_chunks(text)
    logger.info(f"Texto dividido en {len(chunks)} chunks")
    
    file_chunks = []
    for i, chunk in enumerate(chunks):   # ✅ cambiamos a `chunk`
        if not chunk.strip():
            continue
        
        embedding = get_embedding(chunk)
        if not embedding:
            continue
        
        suffix = pathlib.Path(file_path).suffix.lower()
        doc_type = "pdf" if suffix == ".pdf" else "document"
        
        chunk_data = {
            "id": str(uuid.uuid4()),
            "doc_type": doc_type,
            "doc_id": os.path.basename(file_path),
            "title": os.path.basename(file_path).replace(suffix, ''),
            "url": f"file://{file_path}",
            "locale": "es",
            "chunk_index": i,
            "text": chunk,   # ✅ ahora usamos `chunk`
            "embedding": embedding
        }
        file_chunks.append(chunk_data)
    
    return file_chunks

def upsert_chunks(chunks: List[Dict[str, Any]]):
    if not chunks:
        return
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        for chunk in chunks:
            cur.execute("""
                INSERT INTO rag_chunks
                (id, doc_type, doc_id, title, url, locale, chunk_index, text, embedding, updated_at)
                VALUES (%(id)s, %(doc_type)s, %(doc_id)s, %(title)s, %(url)s, %(locale)s,
                        %(chunk_index)s, %(text)s, %(embedding)s::vector, NOW())
                ON CONFLICT (id) DO UPDATE
                  SET text = EXCLUDED.text,
                      embedding = EXCLUDED.embedding,
                      title = EXCLUDED.title,
                      url = EXCLUDED.url,
                      locale = EXCLUDED.locale,
                      updated_at = NOW();
            """, chunk)
        
        conn.commit()
        logger.info(f"Insertados/actualizados {len(chunks)} chunks en la base de datos")
        
    except Exception as e:
        logger.error(f"Error en base de datos: {e}")
        if conn: conn.rollback()
    finally:
        if cur: cur.close()
        if conn: conn.close()

def discover_files(data_dir: str = "data"):
    """Descubre PDFs, Markdown y TXT automáticamente"""
    exts = ("*.pdf", "*.md", "*.txt")
    files = []
    for ext in exts:
        files.extend(glob.glob(os.path.join(data_dir, ext)))
    return sorted(files)

def main():
    logger.info("Iniciando ingesta de archivos...")
    
    files = discover_files()
    if not files:
        logger.error("No se encontraron archivos en el directorio 'data'")
        return
    
    logger.info(f"Encontrados {len(files)} archivos: {[os.path.basename(f) for f in files]}")
    
    total_chunks = 0
    for file_path in files:
        try:
            chunks = process_file(file_path)
            if chunks:
                upsert_chunks(chunks)
                total_chunks += len(chunks)
                logger.info(f"Archivo {os.path.basename(file_path)} procesado: {len(chunks)} chunks")
            else:
                logger.warning(f"No se generaron chunks para {file_path}")
        except Exception as e:
            logger.error(f"Error procesando {file_path}: {e}")
            continue
    
    logger.info(f"Proceso completado. Total de chunks procesados: {total_chunks}")

if __name__ == "__main__":
    main()
