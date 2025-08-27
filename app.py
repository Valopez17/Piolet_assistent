import os
import json
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
    try:
        data = request.get_json(force=True)

        if not data or "messages" not in data:
            return jsonify({"error": "Se requieren mensajes"}), 400

        user_msg = data["messages"][-1]["content"]

        if not user_msg.strip():
            return jsonify({"error": "El mensaje no puede estar vacío"}), 400

        result = answer_with_context(
            question=user_msg,
            top_k=5,
            locale="es"
        )

        response = {
            "reply": result["reply"],
            "sources": result["sources"]
        }

        return app.response_class(
            response=json.dumps(response, ensure_ascii=False),  # 👈 evita \u00ed
            status=200,
            mimetype="application/json; charset=utf-8"
        )

    except Exception as e:
        print(f"Error en chat endpoint: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True) 