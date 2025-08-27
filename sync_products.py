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

def fetch_products():
    """Obtiene todos los productos de Shopify"""
    headers = {"X-Shopify-Access-Token": TOKEN}
    docs = []
    page_info = None
    
    try:
        while True:
            # Construir URL con paginación
            url = f"{ADMIN}/products.json?limit=250"
            if page_info:
                url += f"&page_info={page_info}"
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            products = data.get("products", [])
            
            if not products:
                break
            
            for product in products:
                # Limpiar descripción HTML
                clean_description = clean_html_content(product.get("body_html", ""))
                
                # Preparar texto del producto
                product_text_parts = [product["title"]]
                
                if clean_description:
                    product_text_parts.append(clean_description)
                
                # Agregar tags si existen
                if product.get("tags"):
                    tags_text = f"Tags: {product['tags']}"
                    product_text_parts.append(tags_text)
                
                # Agregar tipo de producto si existe
                if product.get("product_type"):
                    type_text = f"Tipo: {product['product_type']}"
                    product_text_parts.append(type_text)
                
                # Agregar vendor si existe
                if product.get("vendor"):
                    vendor_text = f"Fabricante: {product['vendor']}"
                    product_text_parts.append(vendor_text)
                
                # Combinar todo el texto
                product_text = "\n".join(product_text_parts)
                
                if product_text.strip():
                    docs.append({
                        "doc_type": "product",
                        "doc_id": str(product["id"]),
                        "title": product["title"],
                        "url": f"https://{os.getenv('SHOPIFY_STORE_DOMAIN')}/products/{product['handle']}",
                        "locale": "es",
                        "text": product_text
                    })
            
            # Verificar si hay más páginas
            link_header = response.headers.get("Link", "")
            if "next" in link_header:
                # Extraer page_info del header Link
                import re
                next_match = re.search(r'page_info=([^&>]+)', link_header)
                if next_match:
                    page_info = next_match.group(1)
                else:
                    break
            else:
                break
        
        print(f"Encontrados {len(docs)} productos")
        return docs
        
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener productos: {e}")
        return []

if __name__ == "__main__":
    print("Sincronizando productos de Shopify...")
    
    products_docs = fetch_products()
    
    if products_docs:
        upsert_docs(products_docs)
        print(f"Sincronización completada: {len(products_docs)} productos procesados")
    else:
        print("No se encontraron productos para sincronizar") 