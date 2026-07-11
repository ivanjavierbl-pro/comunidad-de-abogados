"""Webhook de Meta que conecta la recepcionista con WhatsApp, Messenger e Instagram.

Arranque local:
    cd backend
    uvicorn webhook:app --reload --port 8000

Meta (Facebook/WhatsApp) enviará los mensajes entrantes a la ruta /webhook.
Este servidor:
  1. Verifica el webhook (GET) con tu META_VERIFY_TOKEN.
  2. Recibe los mensajes (POST), llama a la recepcionista y responde por el
     mismo canal (WhatsApp, Messenger o Instagram).

Requiere las variables de entorno descritas en .env.example.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Request, Response

from xix_agents.messaging import GraphClient
from xix_agents.receptionist_agent import ReceptionistAgent

load_dotenv()

app = FastAPI(title="XIX Estudio Jurídico — Webhook de mensajería")

agent = ReceptionistAgent()
graph = GraphClient()

# Token que TÚ eliges y configuras igual en el panel de Meta para verificar el webhook.
VERIFY_TOKEN = os.environ.get("META_VERIFY_TOKEN", "xix-verify-token")
# Secreto de la app de Meta, para validar la firma de los eventos (opcional pero recomendado).
APP_SECRET = os.environ.get("META_APP_SECRET", "")

# Estado de conversación por usuario/plataforma (en memoria).
# Clave: "plataforma:id_usuario"  ->  historial de mensajes del agente.
SESSIONS: dict[str, list] = {}


# ---------------------------------------------------------------------- #
# Verificación del webhook (GET) — Meta la llama una sola vez al configurar
# ---------------------------------------------------------------------- #
@app.get("/webhook")
async def verify(request: Request) -> Response:
    params = request.query_params
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == VERIFY_TOKEN
    ):
        return Response(content=params.get("hub.challenge", ""), media_type="text/plain")
    return Response(status_code=403)


# ---------------------------------------------------------------------- #
# Recepción de mensajes (POST)
# ---------------------------------------------------------------------- #
@app.post("/webhook")
async def receive(request: Request, background: BackgroundTasks) -> Response:
    raw = await request.body()

    if APP_SECRET and not _valid_signature(raw, request.headers.get("x-hub-signature-256")):
        return Response(status_code=403)

    data = json.loads(raw or b"{}")
    # Respondemos 200 de inmediato y procesamos en segundo plano
    # (Meta reintenta si tardamos demasiado).
    background.add_task(process_event, data)
    return Response(status_code=200)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------- #
# Procesamiento de eventos entrantes
# ---------------------------------------------------------------------- #
def process_event(data: dict) -> None:
    obj = data.get("object")

    for entry in data.get("entry", []):
        # --- WhatsApp Business ---
        if obj == "whatsapp_business_account":
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg in value.get("messages", []):
                    if msg.get("type") != "text":
                        _respond(
                            "whatsapp",
                            msg.get("from", ""),
                            "Por ahora solo puedo leer mensajes de texto. "
                            "¿Podría escribir su consulta, por favor?",
                            skip_agent=True,
                        )
                        continue
                    _respond("whatsapp", msg["from"], msg["text"]["body"])

        # --- Messenger (Facebook) e Instagram ---
        elif obj in ("page", "instagram"):
            platform = "instagram" if obj == "instagram" else "messenger"
            for event in entry.get("messaging", []):
                message = event.get("message")
                if not message or message.get("is_echo"):
                    continue  # ignorar ecos y eventos que no son mensajes
                text = message.get("text")
                if not text:
                    _respond(
                        platform,
                        event.get("sender", {}).get("id", ""),
                        "Por ahora solo puedo leer mensajes de texto. "
                        "¿Podría escribir su consulta, por favor?",
                        skip_agent=True,
                    )
                    continue
                _respond(platform, event["sender"]["id"], text)


def _respond(platform: str, user_id: str, text: str, skip_agent: bool = False) -> None:
    if not user_id:
        return

    if skip_agent:
        reply = text
    else:
        key = f"{platform}:{user_id}"
        history = SESSIONS.get(key)
        try:
            reply, messages = agent.chat(text, history)
            SESSIONS[key] = messages
        except Exception as exc:  # noqa: BLE001 — no romper el webhook por un error puntual
            print(f"[error] fallo al procesar mensaje de {key}: {exc}")
            reply = (
                "Disculpe, tuvimos un inconveniente técnico. "
                "Por favor intente nuevamente en unos minutos."
            )

    try:
        graph.send(platform, user_id, reply)
    except Exception as exc:  # noqa: BLE001
        print(f"[error] no se pudo enviar la respuesta a {platform}:{user_id}: {exc}")


# ---------------------------------------------------------------------- #
# Seguridad: validar la firma del evento con el secreto de la app
# ---------------------------------------------------------------------- #
def _valid_signature(raw: bytes, header: str | None) -> bool:
    if not header:
        return False
    expected = "sha256=" + hmac.new(APP_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)
