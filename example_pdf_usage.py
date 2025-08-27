#!/usr/bin/env python3
"""
Ejemplo de uso de la funcionalidad de PDFs en Piolet Assistant
Muestra diferentes formas de procesar e ingerir PDFs
"""

import os
import sys
from sync_pdfs import ingest_pdf, extract_text_from_pdf, chunk_text

def example_basic_usage():
    """Ejemplo básico de ingesta de PDFs"""
    print("📚 Ejemplo 1: Ingesta básica de PDF")
    print("=" * 50)
    
    # Verificar que el archivo existe
    pdf_path = "PIOLET-chatbot-pdf.pdf"
    if not os.path.exists(pdf_path):
        print(f"⚠️  Archivo no encontrado: {pdf_path}")
        print("   Coloca el archivo PDF en el directorio backend/")
        return
    
    try:
        # Ingesta básica
        chunks_processed = ingest_pdf(
            pdf_path=pdf_path,
            doc_type="kb",
            doc_id="kb_v8_2025-08-22",
            title="PIOLET Master KB v8",
            locale="es",
            use_ocr=False
        )
        
        print(f"✅ PDF procesado exitosamente: {chunks_processed} chunks")
        
    except Exception as e:
        print(f"❌ Error procesando PDF: {e}")

def example_custom_chunking():
    """Ejemplo de chunking personalizado"""
    print("\n🔪 Ejemplo 2: Chunking personalizado")
    print("=" * 50)
    
    sample_text = """
    Este es un texto de ejemplo que vamos a chunkear. 
    El chunking es importante para el RAG porque permite
    dividir documentos largos en piezas manejables.
    Cada chunk debe tener suficiente contexto para ser útil
    pero no ser demasiado largo para los embeddings.
    El overlap entre chunks ayuda a mantener la continuidad
    del contexto entre diferentes piezas del documento.
    """
    
    # Chunking con parámetros personalizados
    chunks = chunk_text(sample_text, max_chars=100, overlap=20)
    
    print(f"Texto original: {len(sample_text)} caracteres")
    print(f"Chunks generados: {len(chunks)}")
    
    for i, chunk in enumerate(chunks):
        print(f"  Chunk {i+1}: {len(chunk)} chars - '{chunk[:50]}...'")

def example_text_extraction():
    """Ejemplo de extracción de texto de PDF"""
    print("\n📖 Ejemplo 3: Extracción de texto")
    print("=" * 50)
    
    pdf_path = "Guía práctica Piolet(5).pdf"
    if not os.path.exists(pdf_path):
        print(f"⚠️  Archivo no encontrado: {pdf_path}")
        return
    
    try:
        # Extraer texto sin procesar
        pages_data = extract_text_from_pdf(pdf_path)
        
        print(f"📄 PDF procesado: {len(pages_data)} páginas")
        
        # Mostrar información de las primeras páginas
        for i, page in enumerate(pages_data[:3]):  # Solo primeras 3 páginas
            if page['has_text']:
                text_preview = page['text'][:100] + "..." if len(page['text']) > 100 else page['text']
                print(f"  Página {page['page_number']}: {len(page['text'])} chars - '{text_preview}'")
            else:
                print(f"  Página {page['page_number']}: Sin texto extraíble")
                
    except Exception as e:
        print(f"❌ Error extrayendo texto: {e}")

def example_batch_processing():
    """Ejemplo de procesamiento por lotes"""
    print("\n📦 Ejemplo 4: Procesamiento por lotes")
    print("=" * 50)
    
    # Lista de PDFs a procesar
    pdfs_to_process = [
        {
            "path": "PIOLET-chatbot-pdf.pdf",
            "doc_type": "kb",
            "doc_id": "kb_v8_2025-08-22",
            "title": "PIOLET Master KB v8"
        },
        {
            "path": "Guía práctica Piolet(5).pdf",
            "doc_type": "guide",
            "doc_id": "guide_practica_v5",
            "title": "Guía práctica PIOLET"
        }
    ]
    
    total_chunks = 0
    
    for pdf_config in pdfs_to_process:
        if not os.path.exists(pdf_config["path"]):
            print(f"⚠️  Saltando {pdf_config['path']} - archivo no encontrado")
            continue
            
        try:
            print(f"🔄 Procesando: {pdf_config['title']}")
            
            chunks = ingest_pdf(
                pdf_path=pdf_config["path"],
                doc_type=pdf_config["doc_type"],
                doc_id=pdf_config["doc_id"],
                title=pdf_config["title"],
                locale="es"
            )
            
            total_chunks += chunks
            print(f"   ✅ Completado: {chunks} chunks")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n🎯 Total de chunks procesados: {total_chunks}")

def example_ocr_detection():
    """Ejemplo de detección automática de OCR"""
    print("\n🔍 Ejemplo 5: Detección automática de OCR")
    print("=" * 50)
    
    pdf_path = "PIOLET-chatbot-pdf.pdf"
    if not os.path.exists(pdf_path):
        print(f"⚠️  Archivo no encontrado: {pdf_path}")
        return
    
    try:
        # Intentar extracción normal primero
        pages_data = extract_text_from_pdf(pdf_path)
        
        # Verificar si hay páginas sin texto (posible PDF escaneado)
        pages_without_text = [p for p in pages_data if not p['has_text']]
        
        if pages_without_text:
            print(f"📊 {len(pages_without_text)} páginas sin texto extraíble")
            print("   Considerando usar OCR para este PDF")
            
            # Procesar con OCR
            chunks = ingest_pdf(
                pdf_path=pdf_path,
                doc_type="kb",
                doc_id="kb_v8_2025-08-22",
                title="PIOLET Master KB v8 (OCR)",
                locale="es",
                use_ocr=True
            )
            
            print(f"   ✅ OCR completado: {chunks} chunks")
        else:
            print("✅ PDF de texto - OCR no necesario")
            
    except Exception as e:
        print(f"❌ Error en detección OCR: {e}")

def main():
    """Función principal con menú de ejemplos"""
    print("🚀 Ejemplos de uso de PDFs en Piolet Assistant")
    print("=" * 60)
    
    examples = [
        ("Uso básico", example_basic_usage),
        ("Chunking personalizado", example_custom_chunking),
        ("Extracción de texto", example_text_extraction),
        ("Procesamiento por lotes", example_batch_processing),
        ("Detección automática OCR", example_ocr_detection)
    ]
    
    while True:
        print("\n📋 Ejemplos disponibles:")
        for i, (name, _) in enumerate(examples, 1):
            print(f"  {i}. {name}")
        print("  0. Salir")
        
        try:
            choice = input("\n🎯 Selecciona un ejemplo (0-5): ").strip()
            
            if choice == "0":
                print("👋 ¡Hasta luego!")
                break
            elif choice.isdigit() and 1 <= int(choice) <= len(examples):
                idx = int(choice) - 1
                name, func = examples[idx]
                print(f"\n{'='*20} {name} {'='*20}")
                func()
            else:
                print("❌ Opción inválida. Intenta de nuevo.")
                
        except KeyboardInterrupt:
            print("\n\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 