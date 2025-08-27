#!/usr/bin/env python3
"""
Test RAG directo - Consulta embeddings y similitud
"""
from openai import OpenAI
import psycopg2
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Conectar a PostgreSQL
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

# Consulta de ejemplo
q = "¿Cuál es su política de devoluciones?"
print(f" Consulta: {q}")

# Generar embedding de la consulta
emb = client.embeddings.create(model="text-embedding-3-small", input=q).data[0].embedding
print(f"✅ Embedding generado: {len(emb)} dimensiones")

# Buscar chunks similares
cur.execute("""
    SELECT doc_id, chunk_index, left(text, 150), embedding <-> %s::vector AS dist
    FROM rag_chunks
    ORDER BY dist ASC
    LIMIT 3;
""", (emb,))

results = cur.fetchall()

print(f"\n📊 Resultados encontrados: {len(results)}")
print("=" * 80)

for i, (doc_id, chunk_index, text, distance) in enumerate(results, 1):
    print(f"\n{i}.  Documento: {doc_id}")
    print(f"   Chunk: {chunk_index}")
    print(f"   Distancia: {distance:.4f}")
    print(f"   Texto: {text}...")
    print("-" * 60)

# Cerrar conexiones
cur.close()
conn.close()

print(f"\n✅ Test RAG completado") 