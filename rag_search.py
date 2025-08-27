import os
import psycopg2
from psycopg2.extras import RealDictCursor
from openai import OpenAI
from typing import List, Dict, Any, Optional

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_db_connection():
    """Obtiene conexión a la base de datos"""
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def get_embedding(text: str) -> List[float]:
    """Obtiene embedding del texto usando OpenAI"""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def search_context(query: str, k: int = 6, locale: str = "es", prefer_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Búsqueda híbrida: combina búsqueda vectorial con búsqueda de texto
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Obtener embedding de la consulta
        query_embedding = get_embedding(query)
        
        # Construir filtros
        filters = []
        params = []
        
        if locale:
            filters.append("locale = %s")
            params.append(locale)
        
        if prefer_types:
            placeholders = ','.join(['%s'] * len(prefer_types))
            filters.append(f"doc_type IN ({placeholders})")
            params.extend(prefer_types)
        
        where_clause = " AND ".join(filters) if filters else "1=1"
        
        # Búsqueda vectorial
        vector_query = f"""
            SELECT 
                doc_type, doc_id, title, url, text, chunk_index,
                1 - (embedding <=> %s) as similarity
            FROM rag_chunks 
            WHERE {where_clause}
            ORDER BY embedding <=> %s
            LIMIT %s
        """
        
        params_with_embedding = params + [query_embedding, query_embedding, k]
        cur.execute(vector_query, params_with_embedding)
        vector_results = cur.fetchall()
        
        # Búsqueda de texto (trigram)
        text_query = f"""
            SELECT 
                doc_type, doc_id, title, url, text, chunk_index,
                similarity(text, %s) as similarity
            FROM rag_chunks 
            WHERE {where_clause}
            ORDER BY text <-> %s
            LIMIT %s
        """
        
        params_with_text = params + [query, query, k]
        cur.execute(text_query, params_with_text)
        text_results = cur.fetchall()
        
        # Combinar y ordenar resultados
        all_results = []
        seen_ids = set()
        
        # Agregar resultados vectoriales
        for result in vector_results:
            result_id = f"{result['doc_id']}_{result['chunk_index']}"
            if result_id not in seen_ids:
                all_results.append(dict(result))
                seen_ids.add(result_id)
        
        # Agregar resultados de texto que no estén ya incluidos
        for result in text_results:
            result_id = f"{result['doc_id']}_{result['chunk_index']}"
            if result_id not in seen_ids:
                all_results.append(dict(result))
                seen_ids.add(result_id)
        
        # Ordenar por similitud y tomar los mejores k
        all_results.sort(key=lambda x: x['similarity'], reverse=True)
        
        return all_results[:k]
        
    except Exception as e:
        print(f"Error en búsqueda: {e}")
        return []
    finally:
        cur.close()
        conn.close() 