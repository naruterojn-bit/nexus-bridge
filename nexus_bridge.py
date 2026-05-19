# nexus_bridge.py
# Puente entre WhatsApp (via n8n) y NexusNetflixBot usando cuenta personal de Telegram
# Instalar: pip install telethon

import asyncio
import logging
import os
import re
import aiohttp
from telethon import TelegramClient, events
from telethon.sessions import StringSession

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════
#  CONFIGURACIÓN — variables de entorno en Railway
# ══════════════════════════════════════════════
API_ID         = int(os.environ.get("API_ID", "32612495"))
API_HASH       = os.environ.get("API_HASH", "678d81b676317cf854133c9f5dfd9cbb")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

GRUPO_ID           = int(os.environ.get("GRUPO_ID", "-5282560412"))
NEXUS_BOT_USERNAME = os.environ.get("NEXUS_BOT_USERNAME", "NexusNetflixBot")
BRIDGE_BOT_ID      = int(os.environ.get("BRIDGE_BOT_ID", "8567373005"))

# ══════════════════════════════════════════════
#  CLIENTE TELETHON (cuenta personal)
# ══════════════════════════════════════════════
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# Diccionario para rastrear: mensaje_id_en_bot → numero_wa_cliente
sesiones_pendientes = {}

# ══════════════════════════════════════════════
#  ESCUCHA MENSAJES DEL BOT PUENTE EN EL GRUPO
# ══════════════════════════════════════════════
@client.on(events.NewMessage(chats=GRUPO_ID))
async def handler_grupo(event):
    sender = await event.get_sender()

    # Solo procesar mensajes del NexusBridgeBot
    if sender.id != BRIDGE_BOT_ID:
        return

    text = event.raw_text.strip()
    logger.info(f"Mensaje de NexusBridgeBot: {text}")

    nexus_bot = await client.get_entity(NEXUS_BOT_USERNAME)

    # ── Caso 1: SOPORTE:51XXXXXXXXX o /ayuda 51XXXXXXXXX ──────────────────
    match = re.match(r"(?:SOPORTE:|/ayuda\s+)(\d+)", text)
    if match:
        numero_wa = match.group(1)
        logger.info(f"Procesando soporte/ayuda para WA: {numero_wa}")
        msg_enviado = await client.send_message(nexus_bot, f"/ayuda {numero_wa}")
        sesiones_pendientes[msg_enviado.id] = numero_wa
        logger.info(f"Comando /ayuda enviado. msg_id={msg_enviado.id}, wa={numero_wa}")
        return

    # ── Caso 2: /respuestawa 51XXXXXXXXX <texto> ── NUEVO ─────────────────
    match_rwa = re.match(r"(/respuestawa\s+\S+.*)", text, re.IGNORECASE)
    if match_rwa:
        comando_completo = match_rwa.group(1)
        partes = text.split()
        numero_wa = partes[1] if len(partes) > 1 else "desconocido"
        logger.info(f"Reenviando /respuestawa para WA: {numero_wa}")
        msg_enviado = await client.send_message(nexus_bot, comando_completo)
        sesiones_pendientes[msg_enviado.id] = numero_wa
        logger.info(f"Comando /respuestawa enviado. msg_id={msg_enviado.id}, wa={numero_wa}")
        return

# ══════════════════════════════════════════════
#  ESCUCHA RESPUESTA DEL NEXUSNETFLIXBOT (chat privado)
# ══════════════════════════════════════════════
@client.on(events.NewMessage(from_users=NEXUS_BOT_USERNAME))
async def handler_respuesta_bot(event):
    text = event.raw_text.strip()
    logger.info(f"Respuesta de NexusNetflixBot: {text[:100]}...")

    if not text.startswith("WA:"):
        return

    lines = text.split("\n")
    numero_wa = lines[0].replace("WA:", "").strip()
    respuesta_cliente = "\n".join(lines[1:]).strip()

    logger.info(f"Reenviando respuesta al grupo para WA: {numero_wa}")

    await client.send_message(
        GRUPO_ID,
        f"📱 Respuesta para {numero_wa}:\n\n{respuesta_cliente}"
    )

    # Avisar a n8n con la respuesta
    async with aiohttp.ClientSession() as session:
        await session.post(
            "https://primary-production-1a10a.up.railway.app/webhook/nexus-wa-bot",
            json={
                "numero_wa": numero_wa,
                "mensaje":   respuesta_cliente
            }
        )

# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════
async def main():
    logger.info("🚀 NexusBridge iniciando...")
    await client.start()
    me = await client.get_me()
    logger.info(f"✅ Conectado como: {me.first_name} (@{me.username})")
    logger.info(f"👂 Escuchando grupo: {GRUPO_ID}")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
