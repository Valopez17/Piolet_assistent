#!/usr/bin/env python3
"""
Configuración mínima para MVP local de Piolet Assistant
"""

import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de la base de datos
DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "piolet_rag",
    "user": "piolet",
    "password": "superseguro"
}

# Configuración de la API
API_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "debug": True
}

# Configuración de OpenAI
OPENAI_CONFIG = {
    "model": "gpt-4o-mini",
    "embedding_model": "text-embedding-3-small",
    "temperature": 0.4,
    "max_tokens": 600
}

# Configuración de RAG
RAG_CONFIG = {
    "default_chunk_size": 1200,
    "default_overlap": 150,
    "default_k": 6,
    "batch_size": 80
}

# Configuración de Shopify (para MVP local)
SHOPIFY_CONFIG = {
    "store_domain": os.getenv("SHOPIFY_STORE_DOMAIN", "demo-store.myshopify.com"),
    "admin_token": os.getenv("SHOPIFY_ADMIN_TOKEN", "demo-token"),
    "storefront_token": os.getenv("STOREFRONT_API_TOKEN", "demo-storefront-token")
}

# Configuración de CORS para desarrollo local
CORS_CONFIG = {
    "origins": [
        "http://localhost:3000",  # React/Next.js
        "http://localhost:8000",  # API local
        "http://localhost:8080",  # Otros puertos comunes
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000"
    ]
}

def get_database_url():
    """Construye la URL de la base de datos"""
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")
    
    # URL local por defecto
    return f"postgres://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"

def is_local_development():
    """Verifica si estamos en desarrollo local"""
    return os.getenv("ENVIRONMENT", "local") == "local"

def get_allowed_origins():
    """Obtiene orígenes permitidos para CORS"""
    env_origins = os.getenv("ALLOWED_ORIGINS")
    if env_origins:
        return env_origins.split(",")
    return CORS_CONFIG["origins"]

def print_config():
    """Imprime la configuración actual"""
    print("🔧 Configuración del MVP Piolet Assistant")
    print("=" * 50)
    
    print(f"🌍 Entorno: {'Local' if is_local_development() else 'Producción'}")
    print(f"🗄️  Base de datos: {get_database_url()}")
    print(f"🤖 Modelo OpenAI: {OPENAI_CONFIG['model']}")
    print(f"🔍 Embedding model: {OPENAI_CONFIG['embedding_model']}")
    print(f"📊 Chunk size: {RAG_CONFIG['default_chunk_size']}")
    print(f"🔄 Overlap: {RAG_CONFIG['default_overlap']}")
    print(f"🎯 K chunks: {RAG_CONFIG['default_k']}")
    
    print(f"\n🌐 Orígenes CORS permitidos:")
    for origin in get_allowed_origins():
        print(f"   - {origin}")
    
    print(f"\n🏪 Configuración Shopify:")
    print(f"   - Dominio: {SHOPIFY_CONFIG['store_domain']}")
    print(f"   - Admin token: {'Configurado' if SHOPIFY_CONFIG['admin_token'] != 'demo-token' else 'Demo'}")
    
    print(f"\n📝 Variables de entorno requeridas:")
    required_vars = ["OPENAI_API_KEY", "SHOPIFY_STORE_DOMAIN", "SHOPIFY_ADMIN_TOKEN"]
    for var in required_vars:
        value = os.getenv(var)
        if value and not value.startswith("demo") and not value.startswith("tu-tienda"):
            print(f"   ✅ {var}: Configurado")
        else:
            print(f"   ❌ {var}: No configurado o demo")

if __name__ == "__main__":
    print_config() 