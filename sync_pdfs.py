#!/usr/bin/env python3
"""
Script para ingesta de PDFs en el sistema RAG de Piolet
Soporta PDFs de texto y escaneados (con OCR)
"""

import os
import uuid
import pdfplumber
import psycopg2
from psycopg2.extras import RealDictCursor
from openai import OpenAI
import logging
from typing import List, Dict, Any, Optional
import re

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuración
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_db_connection():
    """Obtiene conexión a la base de datos"""
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def clean_text(text: str) -> str:
    """Limpia y normaliza el texto extraído"""
    if not text:
        return ""
    
    # Remover caracteres extraños y normalizar espacios
    text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\[\]]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text

def chunk_text(txt: str, max_chars: int = 1200, overlap: int = 150) -> List[str]:
    """
    Divide el texto en chunks con overlap inteligente
    """
    txt = " ".join((txt or "").split())
    if len(txt) <= max_chars:
        return [txt] if txt.strip() else []
    
    chunks = []
    i = 0
    
    while i < len(txt):
        piece = txt[i:i + max_chars]
        
        # Si no es el final del texto, intenta cortar en un espacio
        if i + max_chars < len(txt):
            j = piece.rfind(" ")
            if j > 0:
                piece = piece[:j]
        
        if piece.strip():
            chunks.append(piece)
        
        # Avanzar considerando el overlap
        i += max(1, len(piece) - overlap)
    
    return chunks

def embed_batch(texts: List[str]) -> List[List[float]]:
    """Genera embeddings para un lote de textos"""
    try:
        response = client.embeddings.create(model=EMBED_MODEL, input=texts)
        return [d.embedding for d in response.data]
    except Exception as e:
        logger.error(f"Error generando embeddings: {e}")
        raise

def upsert_rows(rows: List[Dict[str, Any]]):
    """Inserta o actualiza chunks en la base de datos"""
    conn = get_db_connection()
    
    try:
        with conn, conn.cursor() as cur:
            for row in rows:
                cur.execute("""
                INSERT INTO rag_chunks
                (id, doc_type, doc_id, title, url, locale, chunk_index, text, embedding, updated_at)
                VALUES (%(id)s, %(doc_type)s, %(doc_id)s, %(title)s, %(url)s, %(locale)s, %(chunk_index)s, %(text)s, %(embedding)s::vector, NOW())
                ON CONFLICT (id) DO UPDATE
                  SET text = EXCLUDED.text, 
                      embedding = EXCLUDED.embedding, 
                      title = EXCLUDED.title,
                      url = EXCLUDED.url, 
                      locale = EXCLUDED.locale, 
                      updated_at = NOW();
                """, row)
        
        logger.info(f"Upsert completado para {len(rows)} chunks")
        
    except Exception as e:
        logger.error(f"Error en upsert: {e}")
        raise
    finally:
        conn.close()

def extract_text_from_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extrae texto de un PDF usando pdfplumber
    Retorna lista de páginas con texto y metadatos
    """
    pages_data = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            logger.info(f"Procesando PDF: {pdf_path} ({len(pdf.pages)} páginas)")
            
            for page_no, page in enumerate(pdf.pages, start=1):
                # Extraer texto
                text = page.extract_text()
                
                if text:
                    text = clean_text(text)
                    if text.strip():
                        pages_data.append({
                            'page_number': page_no,
                            'text': text,
                            'has_text': True
                        })
                    else:
                        pages_data.append({
                            'page_number': page_no,
                            'text': '',
                            'has_text': False
                        })
                else:
                    pages_data.append({
                        'page_number': page_no,
                        'text': '',
                        'has_text': False
                    })
                    
    except Exception as e:
        logger.error(f"Error procesando PDF {pdf_path}: {e}")
        raise
    
    return pages_data

def process_pdf_with_ocr(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Procesa PDF escaneado con OCR usando Tesseract
    Requiere: apt-get install tesseract-ocr tesseract-ocr-spa
    """
    try:
        import pytesseract
        from PIL import Image
        import fitz  # PyMuPDF para convertir PDF a imágenes
        
        logger.info(f"Procesando PDF escaneado con OCR: {pdf_path}")
        
        pages_data = []
        pdf_document = fitz.open(pdf_path)
        
        for page_no in range(len(pdf_document)):
            page = pdf_document[page_no]
            
            # Convertir página a imagen
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom para mejor OCR
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # OCR con Tesseract
            text = pytesseract.image_to_string(img, lang='spa+eng')
            text = clean_text(text)
            
            pages_data.append({
                'page_number': page_no + 1,
                'text': text,
                'has_text': bool(text.strip())
            })
        
        pdf_document.close()
        return pages_data
        
    except ImportError:
        logger.warning("PyMuPDF no disponible, usando método alternativo")
        return process_pdf_fallback(pdf_path)
    except Exception as e:
        logger.error(f"Error en OCR: {e}")
        return process_pdf_fallback(pdf_path)

def process_pdf_fallback(pdf_path: str) -> List[Dict[str, Any]]:
    """Método alternativo si OCR falla"""
    logger.info(f"Usando método alternativo para: {pdf_path}")
    return extract_text_from_pdf(pdf_path)

def ingest_pdf(pdf_path: str, doc_type: str, doc_id: str, title: str, 
                locale: str = "es", base_url: Optional[str] = None, 
                use_ocr: bool = False) -> int:
    """
    Procesa e ingiere un PDF completo en el sistema RAG
    
    Args:
        pdf_path: Ruta al archivo PDF
        doc_type: Tipo de documento (kb, guide, manual, etc.)
        doc_id: ID único del documento
        title: Título del documento
        locale: Idioma del documento
        base_url: URL base para enlaces a páginas específicas
        use_ocr: Si usar OCR para PDFs escaneados
    
    Returns:
        Número total de chunks procesados
    """
    if not os.path.exists(pdf_path):
        logger.error(f"Archivo no encontrado: {pdf_path}")
        return 0
    
    logger.info(f"Iniciando ingesta de: {pdf_path}")
    
    # Extraer texto del PDF
    if use_ocr:
        pages_data = process_pdf_with_ocr(pdf_path)
    else:
        pages_data = extract_text_from_pdf(pdf_path)
    
    # Preparar chunks para procesamiento
    all_chunks = []
    chunk_counter = 0
    
    for page_data in pages_data:
        if not page_data['has_text']:
            continue
            
        page_text = page_data['text']
        page_number = page_data['page_number']
        
        # Chunkear texto de la página
        chunks = chunk_text(page_text, max_chars=1200, overlap=150)
        
        for chunk_idx, chunk_text in enumerate(chunks):
            chunk_data = {
                "id": str(uuid.uuid4()),
                "doc_type": doc_type,
                "doc_id": doc_id,
                "title": f"{title} — p.{page_number}",
                "url": f"{base_url}#p={page_number}" if base_url else None,
                "locale": locale,
                "chunk_index": chunk_counter,
                "text": chunk_text,
                "embedding": None
            }
            all_chunks.append(chunk_data)
            chunk_counter += 1
    
    if not all_chunks:
        logger.warning(f"No se encontró texto procesable en: {pdf_path}")
        return 0
    
    logger.info(f"Generando embeddings para {len(all_chunks)} chunks...")
    
    # Generar embeddings por lotes
    batch_size = 80  # OpenAI recomienda máximo 100 por request
    total_processed = 0
    
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i + batch_size]
        
        try:
            # Generar embeddings para el lote
            embeddings = embed_batch([chunk["text"] for chunk in batch])
            
            # Asignar embeddings a los chunks
            for chunk, embedding in zip(batch, embeddings):
                chunk["embedding"] = embedding
            
            # Upsert del lote
            upsert_rows(batch)
            total_processed += len(batch)
            
            logger.info(f"Procesado lote {i//batch_size + 1}: {len(batch)} chunks")
            
        except Exception as e:
            logger.error(f"Error procesando lote {i//batch_size + 1}: {e}")
            continue
    
    logger.info(f"Ingesta completada: {total_processed} chunks procesados de {pdf_path}")
    return total_processed

def main():
    """Función principal para procesar PDFs"""
    logger.info("Iniciando ingesta de PDFs...")
    
    # Configurar PDFs a procesar
    pdfs_to_process = [
        {
            "path": "PIOLET-chatbot-pdf.pdf",
            "doc_type": "kb",
            "doc_id": "kb_v8_2025-08-22",
            "title": "PIOLET Master KB v8",
            "use_ocr": False
        },
        {
            "path": "Guía práctica Piolet(5).pdf",
            "doc_type": "guide",
            "doc_id": "guide_practica_v5",
            "title": "Guía práctica PIOLET",
            "use_ocr": False
        }
    ]
    
    total_chunks = 0
    
    for pdf_config in pdfs_to_process:
        try:
            chunks_processed = ingest_pdf(
                pdf_path=pdf_config["path"],
                doc_type=pdf_config["doc_type"],
                doc_id=pdf_config["doc_id"],
                title=pdf_config["title"],
                locale="es",
                base_url=None,
                use_ocr=pdf_config["use_ocr"]
            )
            total_chunks += chunks_processed
            
        except Exception as e:
            logger.error(f"Error procesando {pdf_config['path']}: {e}")
            continue
    
    logger.info(f"Proceso completado. Total de chunks procesados: {total_chunks}")

if __name__ == "__main__":
    main() 