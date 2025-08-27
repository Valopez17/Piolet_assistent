import os
import requests
from rag_store import upsert_docs
from bs4 import BeautifulSoup

# Configuración de Shopify Admin API
ADMIN = f"https://{os.getenv('SHOPIFY_STORE_DOMAIN')}/admin/api/2024-07"
TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN")

def clean_html_content(html_content):
    """Limpia el contenido HTML usando BeautifulSoup"""
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    # Remover scripts y estilos
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Obtener texto limpio
    text = soup.get_text()
    
    # Limpiar espacios extra
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = ' '.join(chunk for chunk in chunks if chunk)
    
    return text

def fetch_pages():
    """Obtiene todas las páginas de Shopify"""
    headers = {"X-Shopify-Access-Token": TOKEN}
    
    try:
        response = requests.get(f"{ADMIN}/pages.json", headers=headers)
        response.raise_for_status()
        
        pages = response.json().get("pages", [])
        docs = []
        
        for page in pages:
            # Limpiar contenido HTML
            clean_text = clean_html_content(page.get("body_html", ""))
            
            if clean_text.strip():  # Solo procesar si hay contenido
                docs.append({
                    "doc_type": "page",
                    "doc_id": str(page["id"]),
                    "title": page["title"],
                    "url": f"https://{os.getenv('SHOPIFY_STORE_DOMAIN')}/pages/{page['handle']}",
                    "locale": "es",
                    "text": clean_text
                })
        
        print(f"Encontradas {len(docs)} páginas con contenido")
        return docs
        
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener páginas: {e}")
        return []

def fetch_policies():
    """Obtiene las políticas de la tienda"""
    headers = {"X-Shopify-Access-Token": TOKEN}
    
    try:
        response = requests.get(f"{ADMIN}/policies.json", headers=headers)
        response.raise_for_status()
        
        policies = response.json().get("policies", [])
        docs = []
        
        for policy in policies:
            clean_text = clean_html_content(policy.get("body", ""))
            
            if clean_text.strip():
                docs.append({
                    "doc_type": "policy",
                    "doc_id": f"policy_{policy['type']}",
                    "title": f"Política de {policy['type']}",
                    "url": f"https://{os.getenv('SHOPIFY_STORE_DOMAIN')}/policies/{policy['type']}",
                    "locale": "es",
                    "text": clean_text
                })
        
        print(f"Encontradas {len(docs)} políticas")
        return docs
        
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener políticas: {e}")
        return []

if __name__ == "__main__":
    print("Sincronizando páginas y políticas de Shopify...")
    
    # Obtener páginas
    pages_docs = fetch_pages()
    
    # Obtener políticas
    policies_docs = fetch_policies()
    
    # Combinar todos los documentos
    all_docs = pages_docs + policies_docs
    
    if all_docs:
        upsert_docs(all_docs)
        print(f"Sincronización completada: {len(all_docs)} documentos procesados")
    else:
        print("No se encontraron documentos para sincronizar") 