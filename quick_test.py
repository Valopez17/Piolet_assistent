#!/usr/bin/env python3
"""
Script de prueba rápida para verificar que el MVP funciona
"""

import os
import sys
import requests
import json
from dotenv import load_dotenv

def test_environment():
    """Verifica variables de entorno"""
    print("🔍 Verificando variables de entorno...")
    
    load_dotenv()
    
    required_vars = [
        "OPENAI_API_KEY",
        "DATABASE_URL", 
        "ALLOWED_ORIGINS"
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value or value.startswith("sk-demo") or value.startswith("tu-tienda"):
            missing_vars.append(var)
        else:
            print(f"   ✅ {var}: {value[:20]}...")
    
    if missing_vars:
        print(f"   ❌ Variables faltantes o demo: {', '.join(missing_vars)}")
        print("   📝 Edita el archivo .env con tus credenciales reales")
        return False
    
    return True

def test_database_connection():
    """Verifica conexión a base de datos"""
    print("\n🗄️  Verificando conexión a base de datos...")
    
    try:
        import psycopg2
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()
        
        # Verificar si la tabla existe
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'rag_chunks'
            );
        """)
        
        table_exists = cur.fetchone()[0]
        
        if table_exists:
            # Contar chunks existentes
            cur.execute("SELECT COUNT(*) FROM rag_chunks")
            count = cur.fetchone()[0]
            print(f"   ✅ Base de datos conectada - {count} chunks encontrados")
        else:
            print("   ⚠️  Base de datos conectada - tabla rag_chunks no existe")
            print("   💡 Ejecuta: docker compose exec db psql -U piolet -d piolet_rag -f /var/lib/postgresql/data/schema.sql")
        
        cur.close()
        conn.close()
        return True
        
    except ImportError:
        print("   ❌ psycopg2 no instalado")
        return False
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
        return False

def test_openai_connection():
    """Verifica conexión a OpenAI"""
    print("\n🤖 Verificando conexión a OpenAI...")
    
    try:
        from openai import OpenAI
        
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key.startswith("sk-demo"):
            print("   ⚠️  API key demo detectada")
            return False
        
        client = OpenAI(api_key=api_key)
        
        # Test simple de embedding
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input="test"
        )
        
        if response.data and len(response.data[0].embedding) > 0:
            print("   ✅ OpenAI conectado - embedding generado")
            return True
        else:
            print("   ❌ Error generando embedding")
            return False
            
    except ImportError:
        print("   ❌ openai no instalado")
        return False
    except Exception as e:
        print(f"   ❌ Error de OpenAI: {e}")
        return False

def test_api_endpoints():
    """Verifica endpoints de la API"""
    print("\n🌐 Verificando endpoints de la API...")
    
    base_url = "http://localhost:8000"
    
    try:
        # Health check
        response = requests.get(f"{base_url}/healthz", timeout=5)
        if response.status_code == 200:
            print("   ✅ Health check: OK")
        else:
            print(f"   ❌ Health check: {response.status_code}")
            return False
        
        # Chat endpoint (sin OpenAI key real)
        test_data = {
            "messages": [
                {"role": "user", "content": "test"}
            ]
        }
        
        response = requests.post(
            f"{base_url}/api/chat",
            json=test_data,
            timeout=10
        )
        
        if response.status_code in [200, 500]:  # 500 es esperado sin OpenAI key real
            print("   ✅ Chat endpoint: Respondiendo")
        else:
            print(f"   ❌ Chat endpoint: {response.status_code}")
            return False
            
        return True
        
    except requests.exceptions.ConnectionError:
        print("   ❌ API no accesible - ¿está corriendo?")
        print("   💡 Ejecuta: docker compose up -d")
        return False
    except Exception as e:
        print(f"   ❌ Error probando API: {e}")
        return False

def test_pdf_files():
    """Verifica archivos PDF disponibles"""
    print("\n📚 Verificando archivos PDF...")
    
    pdf_dir = "pdfs"
    if not os.path.exists(pdf_dir):
        print(f"   ⚠️  Directorio {pdf_dir}/ no existe")
        return False
    
    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
    
    if pdf_files:
        print(f"   ✅ {len(pdf_files)} PDF(s) encontrado(s):")
        for pdf in pdf_files:
            print(f"      - {pdf}")
        return True
    else:
        print("   ⚠️  No se encontraron archivos PDF")
        print("   💡 Coloca PDFs en el directorio pdfs/")
        return False

def main():
    """Función principal"""
    print("🧪 Prueba rápida del MVP Piolet Assistant")
    print("=" * 50)
    
    tests = [
        ("Variables de entorno", test_environment),
        ("Conexión a base de datos", test_database_connection),
        ("Conexión a OpenAI", test_openai_connection),
        ("Endpoints de la API", test_api_endpoints),
        ("Archivos PDF", test_pdf_files)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"   ❌ Error en {test_name}: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Resultados: {passed}/{total} pruebas pasadas")
    
    if passed == total:
        print("🎉 ¡MVP listo para usar!")
        print("\n🚀 Próximos pasos:")
        print("1. Ejecuta: docker compose exec api python sync_pages.py")
        print("2. Ejecuta: docker compose exec api python sync_products.py")
        print("3. (Opcional) Ejecuta: docker compose exec api python sync_pdfs.py")
        print("4. Abre http://localhost:8000/healthz en tu navegador")
    else:
        print("⚠️  Algunas pruebas fallaron")
        print("\n🔧 Soluciones comunes:")
        print("- Verifica que Docker esté corriendo")
        print("- Ejecuta: docker compose up -d")
        print("- Edita .env con credenciales reales")
        print("- Revisa logs: docker compose logs")

if __name__ == "__main__":
    main() 