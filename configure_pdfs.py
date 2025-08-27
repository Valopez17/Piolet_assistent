#!/usr/bin/env python3
"""
Script de configuración para personalizar la ingesta de PDFs
Permite configurar qué PDFs procesar y sus parámetros
"""

import os
import json
from pathlib import Path

def create_pdf_config():
    """Crea archivo de configuración para PDFs"""
    
    config = {
        "pdfs": [
            {
                "path": "PIOLET-chatbot-pdf.pdf",
                "doc_type": "kb",
                "doc_id": "kb_v8_2025-08-22",
                "title": "PIOLET Master KB v8",
                "locale": "es",
                "base_url": None,
                "use_ocr": False,
                "max_chars": 1200,
                "overlap": 150,
                "description": "Base de conocimientos principal de PIOLET"
            },
            {
                "path": "Guía práctica Piolet(5).pdf",
                "doc_type": "guide",
                "doc_id": "guide_practica_v5",
                "title": "Guía práctica PIOLET",
                "locale": "es",
                "base_url": None,
                "use_ocr": False,
                "max_chars": 1200,
                "overlap": 150,
                "description": "Guía práctica de uso de PIOLET"
            }
        ],
        "settings": {
            "batch_size": 80,
            "embed_model": "text-embedding-3-small",
            "default_locale": "es",
            "default_max_chars": 1200,
            "default_overlap": 150
        }
    }
    
    config_path = Path("pdf_config.json")
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Configuración creada en: {config_path}")
    print("📝 Edita este archivo para personalizar los PDFs a procesar")
    
    return config_path

def validate_pdf_files(config_path):
    """Valida que los archivos PDF existan"""
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    missing_files = []
    
    for pdf in config["pdfs"]:
        if not os.path.exists(pdf["path"]):
            missing_files.append(pdf["path"])
    
    if missing_files:
        print("⚠️  Archivos PDF no encontrados:")
        for file in missing_files:
            print(f"   - {file}")
        print("\n📁 Coloca los archivos PDF en el directorio backend/ o actualiza las rutas en pdf_config.json")
        return False
    else:
        print("✅ Todos los archivos PDF encontrados")
        return True

def show_pdf_info(config_path):
    """Muestra información de los PDFs configurados"""
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    print("\n📚 PDFs configurados para ingesta:")
    print("=" * 60)
    
    for i, pdf in enumerate(config["pdfs"], 1):
        print(f"\n{i}. {pdf['title']}")
        print(f"   📄 Archivo: {pdf['path']}")
        print(f"   🏷️  Tipo: {pdf['doc_type']}")
        print(f"   🆔 ID: {pdf['doc_id']}")
        print(f"   🌍 Idioma: {pdf['locale']}")
        print(f"   🔍 OCR: {'Sí' if pdf['use_ocr'] else 'No'}")
        print(f"   📝 Descripción: {pdf['description']}")
    
    print(f"\n⚙️  Configuración general:")
    print(f"   📦 Tamaño de lote: {config['settings']['batch_size']}")
    print(f"   🤖 Modelo de embedding: {config['settings']['embed_model']}")

def main():
    """Función principal"""
    print("🚀 Configurador de PDFs para Piolet Assistant")
    print("=" * 50)
    
    config_path = Path("pdf_config.json")
    
    if config_path.exists():
        print(f"📋 Archivo de configuración encontrado: {config_path}")
        choice = input("¿Deseas recrear la configuración? (s/N): ").lower()
        
        if choice == 's':
            config_path = create_pdf_config()
        else:
            print("✅ Usando configuración existente")
    else:
        config_path = create_pdf_config()
    
    # Validar archivos
    if validate_pdf_files(config_path):
        show_pdf_info(config_path)
        
        print("\n🎯 Para procesar los PDFs, ejecuta:")
        print("   docker compose exec api python sync_pdfs.py")
        
        print("\n🔧 Para personalizar la configuración:")
        print("   1. Edita pdf_config.json")
        print("   2. Ejecuta: python configure_pdfs.py")
    else:
        print("\n❌ Corrige los archivos faltantes antes de continuar")

if __name__ == "__main__":
    main() 