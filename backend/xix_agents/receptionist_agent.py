"""Recepcionista virtual de XIX Estudio Jurídico.

Agente conversacional que recibe a las personas, informa sobre el despacho, toma
sus datos, agenda citas y deja recados. No brinda asesoría legal: su función es la
de una recepción. Usa herramientas (tools) que Claude invoca y el agente ejecuta,
guardando citas y mensajes en archivos JSON locales.
"""

from __future__ import annotations

import json
import pathlib
import uuid
from datetime import datetime, timezone
from typing import Any

import anthropic

from . import config

# Carpeta donde se guardan citas y mensajes (backend/data/).
DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"


# ---------------------------------------------------------------------- #
# Persistencia sencilla en archivos JSON
# ---------------------------------------------------------------------- #
def _append_record(filename: str, record: dict[str, Any]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / filename
    items: list[dict[str, Any]] = []
    if path.exists():
        items = json.loads(path.read_text(encoding="utf-8"))
    items.append(record)
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _confirmation_code() -> str:
    return "XIX-" + uuid.uuid4().hex[:6].upper()


# ---------------------------------------------------------------------- #
# Definición de las herramientas (esquema que ve el modelo)
# ---------------------------------------------------------------------- #
TOOL_DEFS: list[dict[str, Any]] = [
    {
        "name": "agendar_cita",
        "description": (
            "Agenda una cita del cliente con el despacho. Úsala solo después de "
            "haber confirmado con la persona su nombre, un contacto y el motivo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre_cliente": {"type": "string", "description": "Nombre completo"},
                "contacto": {
                    "type": "string",
                    "description": "Teléfono o correo electrónico del cliente",
                },
                "area": {
                    "type": "string",
                    "description": "Área jurídica del caso (laboral, civil, penal, etc.)",
                },
                "motivo": {
                    "type": "string",
                    "description": "Descripción breve del motivo de la consulta",
                },
                "fecha_hora_preferida": {
                    "type": "string",
                    "description": "Fecha y hora que prefiere el cliente, en texto libre",
                },
                "urgencia": {
                    "type": "string",
                    "enum": ["normal", "alta"],
                    "description": "Nivel de urgencia del caso",
                },
            },
            "required": ["nombre_cliente", "contacto", "area", "motivo"],
        },
    },
    {
        "name": "dejar_mensaje",
        "description": (
            "Registra un recado cuando la persona no desea agendar una cita en el "
            "momento pero quiere que el despacho la contacte."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre_cliente": {"type": "string", "description": "Nombre completo"},
                "contacto": {
                    "type": "string",
                    "description": "Teléfono o correo electrónico del cliente",
                },
                "mensaje": {"type": "string", "description": "Contenido del recado"},
                "urgencia": {
                    "type": "string",
                    "enum": ["normal", "alta"],
                    "description": "Nivel de urgencia",
                },
            },
            "required": ["nombre_cliente", "contacto", "mensaje"],
        },
    },
]


class ReceptionistAgent:
    """Recepcionista virtual conversacional del despacho.

    Uso::

        agent = ReceptionistAgent()
        messages = []
        texto, messages = agent.chat("Hola, necesito ayuda con un despido", messages)
        print(texto)
        # ... siguiente turno reutilizando `messages` para mantener el contexto
    """

    def __init__(
        self,
        client: anthropic.Anthropic | None = None,
        model: str = config.MODEL,
        max_tokens: int = config.RECEPTIONIST_MAX_TOKENS,
        despacho_info: dict | None = None,
    ) -> None:
        self.client = client or anthropic.Anthropic()
        self.model = model
        self.max_tokens = max_tokens
        self.system_prompt = config.build_receptionist_prompt(
            despacho_info or config.DESPACHO_INFO
        )

    def chat(
        self, user_message: str, messages: list[dict[str, Any]] | None = None
    ) -> tuple[str, list[dict[str, Any]]]:
        """Procesa un turno del usuario y devuelve (respuesta, historial_actualizado).

        Ejecuta el bucle de herramientas: si Claude decide agendar una cita o dejar
        un mensaje, el agente ejecuta la acción y le devuelve el resultado, hasta
        que Claude produce su respuesta final para la persona.
        """
        messages = list(messages or [])
        messages.append({"role": "user", "content": user_message})

        response = None
        while True:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self.system_prompt,
                # Tarea simple y conversacional: esfuerzo bajo para ser rápido y barato.
                output_config={"effort": "low"},
                tools=TOOL_DEFS,
                messages=messages,
            )
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                break

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    output = self._execute_tool(block.name, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": output,
                        }
                    )
            messages.append({"role": "user", "content": tool_results})

        text = "".join(b.text for b in response.content if b.type == "text").strip()
        return text, messages

    # ------------------------------------------------------------------ #
    # Ejecución de las herramientas
    # ------------------------------------------------------------------ #
    def _execute_tool(self, name: str, tool_input: dict[str, Any]) -> str:
        if name == "agendar_cita":
            code = _confirmation_code()
            _append_record(
                "citas.json",
                {"codigo": code, "creado": _now_iso(), **tool_input},
            )
            return json.dumps(
                {
                    "estado": "agendada",
                    "codigo": code,
                    "nota": "Un abogado del área confirmará la cita.",
                },
                ensure_ascii=False,
            )

        if name == "dejar_mensaje":
            code = _confirmation_code()
            _append_record(
                "mensajes.json",
                {"codigo": code, "creado": _now_iso(), **tool_input},
            )
            return json.dumps(
                {"estado": "registrado", "codigo": code}, ensure_ascii=False
            )

        return json.dumps({"error": f"herramienta desconocida: {name}"}, ensure_ascii=False)
