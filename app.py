import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv

# Importar el nuevo sistema RAG
from src.pg_retrieve import answer_with_context

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": os.getenv("ALLOWED_ORIGINS","").split(",")}})
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """Eres el asistente de Piolet. Responde corto, claro y con enlaces a fuentes cuando existan."""

@app.route("/healthz")
def healthz():
    """Endpoint de health check"""
    return "ok", 200

@app.route("/api/chat", methods=["POST"])
def chat():
    """Endpoint principal de chat con RAG mejorado"""
    try:
        data = request.get_json(force=True)
        
        if not data or "messages" not in data:
            return jsonify({"error": "Se requieren mensajes"}), 400
        
        # Obtener el último mensaje del usuario
        user_msg = data["messages"][-1]["content"]
        
        if not user_msg.strip():
            return jsonify({"error": "El mensaje no puede estar vacío"}), 400
        
        # Usar el nuevo sistema RAG
        result = answer_with_context(
            question=user_msg,
            top_k=5,
            locale="es"
        )
        
        return jsonify({
            "reply": result["reply"],
            "sources": result["sources"]
        })
        
    except Exception as e:
        print(f"Error en chat endpoint: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True) 