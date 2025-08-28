#!/usr/bin/env python3
"""
Recuperación RAG para Piolet Assistant
Adaptado al esquema: id (uuid), doc_type, doc_id, title, url, locale, chunk_index, text, embedding, updated_at
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from openai import OpenAI
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import json


# Configuración
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Configuración de base de datos
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "piolet_rag"),
    "user": os.getenv("DB_USER", "piolet"),
    "password": os.getenv("DB_PASSWORD", "superseguro")
}

def get_db_connection():
    """Obtiene conexión a la base de datos"""
    return psycopg2.connect(**DB_CONFIG)

def get_embedding(text: str) -> List[float]:
    """Genera embedding usando OpenAI"""
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generando embedding: {e}")
        raise

def retrieve_context(question: str, top_k: int = 5, locale: str = "es") -> List[Dict[str, Any]]:
    """
    Recupera contexto relevante usando búsqueda vectorial
    
    Args:
        question: Pregunta del usuario
        top_k: Número de chunks a recuperar
        locale: Idioma preferido
    
    Returns:
        Lista de chunks con información relevante
    """
    try:
        # Generar embedding de la pregunta
        question_embedding = get_embedding(question)
        
        # Buscar chunks similares
        conn = get_db_connection()
        with conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    id,
                    doc_type,
                    doc_id,
                    title,
                    url,
                    locale,
                    chunk_index,
                    text,
                    1 - (embedding <=> %s) AS similarity
                FROM rag_chunks 
                WHERE locale = %s OR locale IS NULL
                ORDER BY embedding <=> %s
                LIMIT %s
            """, (question_embedding, locale, question_embedding, top_k))
            
            results = cur.fetchall()
            
            # Convertir a diccionarios
            chunks = []
            for row in results:
                chunks.append({
                    'id': row['id'],
                    'doc_type': row['doc_type'],
                    'doc_id': row['doc_id'],
                    'title': row['title'],
                    'url': row['url'],
                    'locale': row['locale'],
                    'chunk_index': row['chunk_index'],
                    'text': row['text'],
                    'similarity': float(row['similarity'])
                })
            
            return chunks
            
    except Exception as e:
        logger.error(f"Error en recuperación: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def generate_response(question: str, context_chunks: List[Dict[str, Any]]) -> str:
    """
    Genera respuesta usando OpenAI con el contexto recuperado
    
    Args:
        question: Pregunta del usuario
        context_chunks: Chunks de contexto recuperados
    
    Returns:
        Respuesta generada
    """
    if not context_chunks:
        return "No tengo información suficiente para responder tu pregunta. Por favor, intenta reformularla o pregunta sobre otro tema."
    
    # Construir prompt con contexto
    context_text = "\n\n".join([
        f"[Fuente: {chunk['title']}]\n{chunk['text']}"
        for chunk in context_chunks
    ])
    
    system_prompt =  system_prompt = system_prompt = """
Eres el asistente de Piolet, un amigo buena onda que responde corto y práctico.
Usa bullets siempre que haya más de un punto (máximo 4 bullets).
Cada bullet = 1 idea sin párrafos largos solo con la info relevante.
Usa emojis solo si ayudan a hacerlo más ligero.

Cuando menciones productos, incluye el link en formato HTML (<a href="URL" target="_blank">Texto</a>) para que se pueda abrir directo.
Ejemplo: 👉 <a href="https://thepiolet.com/products/polar-s" target="_blank">Polar S</a>

Solo si no tienes toda la info, dilo de forma honesta y sugiere preguntar al equipo de Piolet.

Tono: relajado y de confianza, como platicando con un amigo.
"""

    user_prompt = f"""Contexto disponible:

{context_text}

Pregunta: {question}

Responde basándote únicamente en la información del contexto anterior. Si no puedes responder completamente con la información disponible, dilo claramente."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=600
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error generando respuesta: {e}")
        return f"Error generando respuesta: {str(e)}"

def answer_with_context(question: str, top_k: int = 5, locale: str = "es"):
    """Hace retrieval en Postgres y construye la respuesta con contexto"""

    # 1. Embedding de la pregunta
    emb = client.embeddings.create(
        model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"),
        input=question
    ).data[0].embedding

    # 2. Recuperar chunks desde Postgres (sin filtro de distancia)
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()
    cur.execute("""
        SELECT doc_id, chunk_index, text, embedding <-> %s::vector AS dist
        FROM rag_chunks
        ORDER BY dist ASC
        LIMIT %s;
    """, (emb, top_k))
    rows = cur.fetchall()
    cur.close(); conn.close()

    if not rows:
        return {
            "reply": "No tengo información suficiente para responder tu pregunta.",
            "sources": []
        }

    # 3. Construir contexto con los textos recuperados
    context = "\n\n".join([r[2] for r in rows])
    sources = [r[0] for r in rows]

    # 4. Construir prompt    
    system_prompt =  system_prompt = """
Eres el asistente de Piolet, un amigo buena onda que responde corto y práctico.
Usa bullets siempre que haya más de un punto (máximo 4 bullets).
Cada bullet = 1 idea sin párrafos largos solo con la info relevante.
Usa emojis solo si ayudan a hacerlo más ligero.

Cuando menciones productos, incluye el link en formato HTML (<a href="URL" target="_blank">Texto</a>) para que se pueda abrir directo.
Ejemplo: 👉 <a href="https://thepiolet.com/products/polar-s" target="_blank">Polar S</a>

Solo si no tienes toda la info, dilo de forma honesta y sugiere preguntar al equipo de Piolet.

Tono: relajado y de confianza, como platicando con un amigo.
"""
    
    user_prompt = f"""Usa la siguiente información para responder la pregunta:

Contexto:
{context}

Pregunta: {question}
Respuesta:"""

    # 5. Llamar al LLM
    chat = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    answer = chat.choices[0].message.content

    return {"reply": answer, "sources": sources}

def test_retrieval():
    """Función de prueba para verificar que la recuperación funciona"""
    logger.info("Probando recuperación RAG...")
    
    # Verificar conexión a base de datos
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM rag_chunks")
            count = cur.fetchone()[0]
            logger.info(f"Total de chunks en la base de datos: {count}")
        
        if count == 0:
            logger.warning("No hay chunks en la base de datos. Ejecuta la ingesta primero.")
            return
        
        # Probar recuperación
        test_question = "¿Qué es Piolet?"
        result = answer_with_context(test_question, top_k=3)
        
        logger.info("Respuesta generada:")
        logger.info(f"Pregunta: {test_question}")
        logger.info(f"Respuesta: {result['reply']}")
        logger.info(f"Fuentes: {len(result['sources'])} encontradas")
        
        for i, source in enumerate(result['sources']):
            logger.info(f"  Fuente {i+1}: {source['title']} (similitud: {source['similarity']:.3f})")
            
    except Exception as e:
        logger.error(f"Error en prueba: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Modo de línea de comandos
        question = " ".join(sys.argv[1:])
        result = answer_with_context(question)
        print(f"\nPregunta: {question}")
        print(f"\nRespuesta: {result['reply']}")
        print(f"\nFuentes: {len(result['sources'])} encontradas")
        for i, source in enumerate(result['sources']):
            print(f"  {i+1}. {source['title']} (similitud: {source['similarity']:.3f})")
    else:
        # Modo de prueba
        test_retrieval() 