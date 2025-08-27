#!/bin/bash

echo "🚀 Setup rápido para Piolet Assistant MVP local"
echo "================================================"

# Verificar si Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado. Instálalo primero:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose no está instalado. Instálalo primero:"
    echo "   https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker y Docker Compose encontrados"

# Crear archivo .env si no existe
if [ ! -f .env ]; then
    echo "📝 Creando archivo .env..."
    cat > .env << EOF
# Configuración para MVP local
OPENAI_API_KEY=sk-demo-key-change-me
DATABASE_URL=postgres://piolet:superseguro@db:5432/piolet_rag
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
SHOPIFY_STORE_DOMAIN=tu-tienda.myshopify.com
SHOPIFY_ADMIN_TOKEN=shpat_demo-token-change-me
STOREFRONT_API_TOKEN=shpat_demo-storefront-change-me
EMBED_MODEL=text-embedding-3-small
EOF
    echo "⚠️  IMPORTANTE: Edita .env con tus credenciales reales antes de continuar"
    echo "   - OPENAI_API_KEY: Tu API key de OpenAI"
    echo "   - SHOPIFY_STORE_DOMAIN: Tu dominio de Shopify"
    echo "   - SHOPIFY_ADMIN_TOKEN: Tu token de Admin API"
    echo ""
    read -p "¿Quieres continuar con credenciales demo? (s/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        echo "📝 Edita el archivo .env y ejecuta este script nuevamente"
        exit 0
    fi
else
    echo "✅ Archivo .env encontrado"
fi

# Crear directorio para PDFs si no existe
mkdir -p pdfs
echo "📁 Directorio pdfs/ creado"

# Crear archivo de configuración de PDFs si no existe
if [ ! -f pdf_config.json ]; then
    echo "📝 Creando configuración de PDFs..."
    cat > pdf_config.json << EOF
{
  "pdfs": [
    {
      "path": "pdfs/ejemplo.pdf",
      "doc_type": "demo",
      "doc_id": "demo_v1",
      "title": "Documento de Ejemplo",
      "locale": "es",
      "use_ocr": false,
      "max_chars": 1200,
      "overlap": 150
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
EOF
    echo "⚠️  Coloca tus PDFs en el directorio pdfs/ y actualiza pdf_config.json"
fi

echo ""
echo "🎯 Para continuar con el MVP:"
echo "1. Edita .env con tus credenciales reales"
echo "2. Coloca PDFs en pdfs/ (opcional)"
echo "3. Ejecuta: docker compose up -d"
echo "4. Verifica: docker compose ps"
echo ""
echo "🚀 ¿Listo para continuar?" 