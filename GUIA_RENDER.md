# Guía: publicar la recepcionista en Render (gratis, 24/7)

Render corre el servidor en la nube, siempre encendido, con una URL pública.
No necesitás instalar nada en tu computadora.

## Requisitos
- El código ya está en GitHub (rama `main`).
- Una clave gratuita de Google Gemini: <https://aistudio.google.com/> → *Get API key*.

## Pasos

1. Creá una cuenta gratuita en <https://render.com/> (podés entrar con tu cuenta
   de GitHub).
2. En el panel de Render: **New +** → **Blueprint**.
3. Conectá tu repositorio **`comunidad-de-abogados`** (autorizá a Render a ver tu
   GitHub si te lo pide). Render detecta el archivo `render.yaml` solo.
4. Te va a pedir el valor de **`GEMINI_API_KEY`** → pegá tu clave de Gemini.
5. Clic en **Apply** / **Create**. Render instala todo y despliega (tarda unos
   minutos la primera vez).
6. Cuando termine, Render te da una **URL pública** tipo
   `https://xix-recepcionista.onrender.com`.
7. Probá que esté viva abriendo en el navegador:
   `https://TU-URL.onrender.com/api/health` → debe mostrar `{"status":"ok"}`.

## Conectar WhatsApp

Tu webhook para Meta será: `https://TU-URL.onrender.com/webhook`
y el *Verify token*: `xix-verify-token`.

Cuando tengas las credenciales de Meta (ver `backend/GUIA_WHATSAPP.md`),
agregalas en Render: **el servicio → Environment → Add Environment Variable**:
`WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `PAGE_ACCESS_TOKEN`,
`META_APP_SECRET`. Render redepliega solo al guardarlas.

## Notas
- **Plan gratuito:** el servicio se "duerme" tras ~15 min sin uso y tarda unos
  segundos en despertar con el primer mensaje. Para WhatsApp de bajo volumen es
  suficiente (Meta reintenta el envío).
- Cada vez que se actualice el código en `main`, Render vuelve a desplegar solo.
