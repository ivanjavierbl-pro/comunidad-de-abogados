# Agentes de IA de XIX Estudio Jurídico

Backend en Python con agentes de inteligencia artificial (Claude) para
**XIX Estudio Jurídico**, orientados al derecho paraguayo.

## Agentes incluidos

### 🔎 Asistente de Investigación Jurídica

Responde consultas de **derecho paraguayo** verificando en fuentes oficiales de la
República del Paraguay (BACN, Gaceta Oficial, Corte Suprema de Justicia, leyes
nacionales) mediante búsqueda web, y devuelve la respuesta **con sus citas**.

- Modelo: **Claude Opus 4.8** (`claude-opus-4-8`)
- Herramienta: búsqueda web con citas (`web_search_20260209`)
- Pensamiento adaptativo + esfuerzo alto
- Respuesta en streaming (token por token)

### 🛎️ Recepcionista virtual

Atiende a las personas que contactan al estudio: saluda, informa horarios/áreas,
toma los datos de contacto y **agenda citas** o **deja recados**. No brinda
asesoría legal.

- Modelo: **Claude Opus 4.8** con herramientas (tool use)
- Agenda citas y recados guardándolos en `data/citas.json` y `data/mensajes.json`
- Conversacional y con memoria de contexto

## Instalación

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # y coloca tu ANTHROPIC_API_KEY
```

Obtén tu clave en <https://console.anthropic.com/>.

## Uso

### Investigación jurídica (línea de comandos)

```bash
# Consulta única
python cli.py "¿Qué requisitos exige el Código del Trabajo para el despido justificado?"

# Modo interactivo (mantiene el contexto de la conversación)
python cli.py
```

### Recepcionista virtual (línea de comandos)

```bash
python recepcion.py
```

Inicia una conversación de recepción; las citas y recados quedan guardados en
`backend/data/`.

### Como servidor web (para integrar con un sitio)

```bash
uvicorn server:app --reload
```

Endpoints del asistente de investigación:

| Método | Ruta                     | Descripción                             |
| ------ | ------------------------ | --------------------------------------- |
| GET    | `/api/health`            | Verificación de estado                  |
| POST   | `/api/research`          | Respuesta completa en JSON              |
| POST   | `/api/research/stream`   | Respuesta en streaming (SSE)            |

Ejemplo:

```bash
curl -X POST http://localhost:8000/api/research \
  -H "Content-Type: application/json" \
  -d '{"query": "¿Qué es la acción de inconstitucionalidad y cómo se tramita ante la Corte Suprema de Justicia?"}'
```

### Desde Python

```python
from xix_agents import LegalResearchAgent, ReceptionistAgent

# Investigación jurídica
research = LegalResearchAgent()
resultado = research.research("¿Qué garantías laborales establece el artículo 86 de la Constitución Nacional?")
print(resultado.answer)

# Recepcionista
recepcion = ReceptionistAgent()
texto, historial = recepcion.chat("Hola, necesito ayuda con un despido")
print(texto)
```

## Estructura

```
backend/
├── requirements.txt
├── .env.example
├── cli.py                        # CLI del asistente de investigación
├── recepcion.py                  # CLI de la recepcionista virtual
├── server.py                     # API FastAPI (JSON + SSE)
├── webhook.py                    # webhook de Meta (WhatsApp/Messenger/Instagram)
└── xix_agents/
    ├── __init__.py
    ├── config.py                 # modelo, prompts, datos del estudio
    ├── legal_research_agent.py   # agente de investigación jurídica
    ├── receptionist_agent.py     # agente recepcionista
    └── messaging.py              # envío de mensajes vía Graph API de Meta
```

## Conectar con WhatsApp Business, Messenger e Instagram

La recepcionista puede atender por **WhatsApp Business**, **Messenger (Facebook)** e
**Instagram** mediante la API de Meta. Los tres canales usan el mismo servidor de
webhook (`webhook.py`).

### Requisitos previos (en el panel de Meta)

1. Cuenta en **Meta for Developers** (<https://developers.facebook.com/>) y una app
   de tipo *Business*.
2. **WhatsApp:** agregar el producto *WhatsApp* a la app. Meta te dará un
   `WHATSAPP_PHONE_NUMBER_ID` y un token de acceso (`WHATSAPP_TOKEN`).
   > ⚠️ El número debe estar en la **WhatsApp Cloud API**, no en la app común de
   > WhatsApp Business. Si tu número ya está en la app, hay que migrarlo.
3. **Messenger e Instagram:** una **Página de Facebook** y una **cuenta de
   Instagram Business** vinculada a esa página. De ahí se obtiene el
   `PAGE_ACCESS_TOKEN`.
4. Copiar el **App Secret** (App Settings → Basic) a `META_APP_SECRET`.

### Poner el servidor en línea

El webhook necesita una URL pública HTTPS. Para pruebas puedes usar un túnel como
[ngrok](https://ngrok.com/):

```bash
uvicorn webhook:app --port 8000
# en otra terminal:
ngrok http 8000
```

ngrok te dará una URL como `https://xxxx.ngrok-free.app`. Tu webhook será
`https://xxxx.ngrok-free.app/webhook`.

### Configurar el webhook en Meta

En cada producto (WhatsApp, Messenger, Instagram) → *Configuración / Webhooks*:

- **Callback URL:** `https://TU-DOMINIO/webhook`
- **Verify token:** el mismo valor que pusiste en `META_VERIFY_TOKEN`
- **Suscribirse** a los campos de mensajes (`messages`).

Meta hará una petición `GET` de verificación; el servidor responde automáticamente
con el `challenge`. A partir de ahí, todo mensaje que reciba tu WhatsApp/página se
enviará al webhook y la recepcionista responderá por el mismo canal.

### Variables de entorno necesarias

Ver `.env.example`: `META_VERIFY_TOKEN`, `META_APP_SECRET`, `WHATSAPP_TOKEN`,
`WHATSAPP_PHONE_NUMBER_ID`, `PAGE_ACCESS_TOKEN` (además de `ANTHROPIC_API_KEY`).

> **Nota:** en esta primera versión el historial de conversación se guarda en
> memoria (se reinicia si reinicias el servidor). Para producción conviene un
> almacenamiento persistente (base de datos).

## Configuración del estudio

Los datos del estudio (nombre, horario, dirección, áreas, abogados) se editan en
`xix_agents/config.py`, en el diccionario `DESPACHO_INFO`.

## Advertencia

Estas son herramientas de **apoyo**. No sustituyen el criterio profesional ni
constituyen asesoría legal formal.
