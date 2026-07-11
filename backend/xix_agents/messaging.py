"""Cliente para enviar mensajes a través de la API de Meta (Graph API).

Un mismo estudio puede atender por WhatsApp Business, Messenger (Facebook) e
Instagram. WhatsApp usa su propio endpoint; Messenger e Instagram comparten el
endpoint de mensajes de la página de Facebook conectada.
"""

from __future__ import annotations

import os

import httpx

# Versión de la Graph API de Meta.
GRAPH_URL = "https://graph.facebook.com/v21.0"


class GraphClient:
    """Envía mensajes de texto a WhatsApp, Messenger e Instagram vía Meta."""

    def __init__(self) -> None:
        # Credenciales (se leen del entorno / archivo .env).
        self.whatsapp_token = os.environ.get("WHATSAPP_TOKEN", "")
        self.whatsapp_phone_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
        # Token de la página de Facebook (sirve para Messenger e Instagram).
        self.page_token = os.environ.get("PAGE_ACCESS_TOKEN", "")

    # ------------------------------------------------------------------ #
    # WhatsApp Business (WhatsApp Cloud API)
    # ------------------------------------------------------------------ #
    def send_whatsapp(self, to: str, text: str) -> None:
        url = f"{GRAPH_URL}/{self.whatsapp_phone_id}/messages"
        headers = {"Authorization": f"Bearer {self.whatsapp_token}"}
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text[:4096]},
        }
        resp = httpx.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()

    # ------------------------------------------------------------------ #
    # Messenger (Facebook) e Instagram — mismo endpoint de la página
    # ------------------------------------------------------------------ #
    def send_page_message(self, recipient_id: str, text: str) -> None:
        url = f"{GRAPH_URL}/me/messages"
        params = {"access_token": self.page_token}
        payload = {
            "recipient": {"id": recipient_id},
            "messaging_type": "RESPONSE",
            "message": {"text": text[:2000]},
        }
        resp = httpx.post(url, params=params, json=payload, timeout=30)
        resp.raise_for_status()

    # ------------------------------------------------------------------ #
    # Despacho por plataforma
    # ------------------------------------------------------------------ #
    def send(self, platform: str, recipient_id: str, text: str) -> None:
        """Envía por el canal correcto según la plataforma de origen."""
        if platform == "whatsapp":
            self.send_whatsapp(recipient_id, text)
        else:  # "messenger" o "instagram"
            self.send_page_message(recipient_id, text)
