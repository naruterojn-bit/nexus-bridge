# streaming_support_bot_v31.py
# VERSION 31 — Detección perfiles via falcorCache de /ManageProfiles (fuente directa con idioma exacto por perfil)
# pip install python-telegram-bot==20.7 requests gspread google-auth

import asyncio
import logging, re, os, json, requests, gspread
import urllib.parse
from datetime import datetime, date, timedelta, timezone
from google.oauth2.service_account import Credentials
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, filters, ContextTypes,
)

PERU_TZ = timezone(timedelta(hours=-5))

def now_peru():
    """Retorna la fecha/hora actual en zona horaria de Perú."""
    return datetime.now(PERU_TZ).strftime("%d/%m/%Y %H:%M:%S")

# ══════════════════════════════════════════════
#  CONFIGURACIÓN
# ══════════════════════════════════════════════
BOT_TOKEN         = os.environ.get("BOT_TOKEN")           
SHEET_ID_CLIENTES = "1i7yJClIADnZkRyFthFx3krLO-OXr_Rrd3R-Ry-n3VuE"
SHEET_ID_COOKIES  = "16qVQBrxx2wmh4clrPv1OdwXjaqhPwfymcWUJgPbBA5s"
ADMIN_ID = 6721733561
BRIDGE_BOT_ID = 8567373005
VIDEO_CELULAR     = "https://t.me/activartv"
VIDEO_PC          = "https://t.me/activarnetv"
WHATSAPP_LINK     = "https://wa.me/51925922801?text=Hola%20quiero%20comprar%20Netflix"
YAPE_NOMBRE       = "Juan Rimache"
QR_IMAGE_PATH     = "qr_yape.jpeg"
QR_BINANCE_PATH   = "qr_binance.jpeg"
QR_LEMON_PATH     = "qr_lemon.jpeg"
TASA_DOLAR        = 3.40   # Soles por dólar para conversión mayorista
COMISION_INT      = 0.50   # Comisión fija en USDT para pagos internacionales

BTN_PAGO_PERU       = "🇵🇪 Pago desde Perú"
BTN_PAGO_EXTRANJERO = "🌎 Pago desde el Extranjero"
BTN_PAGO_BINANCE    = "🟡 Binance Pay"
BTN_PAGO_LEMON      = "🍋 Lemon Cash"

PROMOCIONES = [
    "🔥 Renueva puntualmente tu servicio y obten *+3 días GRATIS*",
    "🎁 Invita 5 personas y gana *5 días GRATIS* si 1 compra",
    "🎁 Invita 5 personas y gana *100 likes/seguidores* en TikTok/FB/IG/otros GRATIS si 1 compra",
]

CODIGOS_ESPANOL = {"ES", "AR", "MX", "CO", "PE", "CL"}
NOMBRES_ESPANOL = {"Spain", "Argentina", "Mexico", "Colombia", "Peru", "Chile"}

PLANES_TV = {
    "📺 S/8/mes - Compartida random":   {"precio": 8,  "tipo": "random",   "dispositivo": "TV"},
    "📺 S/10/mes - Compartida español": {"precio": 10, "tipo": "espanol",  "dispositivo": "TV"},
    "🌟 S/15/mes - Perfil personal":    {"precio": 15, "tipo": "personal", "dispositivo": "PERSONAL"},
}
PLANES_CEL = {
    "📱 S/8/mes - Compartida random":   {"precio": 8,  "tipo": "random",  "dispositivo": "CEL"},
    "📱 S/10/mes - Compartida español": {"precio": 10, "tipo": "espanol", "dispositivo": "CEL"},
    "🌟 S/15/mes - Perfil personal":    {"precio": 15, "tipo": "personal", "dispositivo": "PERSONAL"},
}

# ══════════════════════════════════════════════
#  ESTADOS — orden alineado con handlers
# ══════════════════════════════════════════════
(
    MENU_PRINCIPAL,
    ESPERANDO_CELULAR,
    PREGUNTA_ACTIVAR_TV,
    PREGUNTA_DISPOSITIVO,
    VENTA_ELEGIR_CANAL,       
    VENTA_ELEGIR_DISPOSITIVO, 
    VENTA_ELEGIR_PLAN,        
    VENTA_CONFIRMAR_RAPIDO,   
    VENTA_PEDIR_NOMBRE,       
    VENTA_PEDIR_CELULAR,      
    VENTA_PEDIR_COMPROBANTE,  
    PERFIL_PEDIR_NOMBRE,      
    PERFIL_PEDIR_PIN,
    ESPERANDO_MOTIVO_TICKET,
    ESPERANDO_CODIGO_TV,
    # ── Mayoristas ──
    MAYOR_ELEGIR_CANTIDAD,
    MAYOR_CONFIRMAR_PAGO,
    MAYOR_PEDIR_COMPROBANTE,
    MAYOR_CANJEAR_ETIQUETA,
    MAYOR_ELEGIR_REGION,
    # ── Pagos internacionales ──
    VENTA_ELEGIR_ORIGEN,
    VENTA_ELEGIR_METODO_INT,
    # ── Mayoristas internacionales ──
    MAYOR_ELEGIR_ORIGEN,
    MAYOR_ELEGIR_METODO_INT,
) = range(24)

OPC_INCONVENIENTES = "inconvenientes"
OPC_DIAS           = "dias"

BTN_INCONVENIENTES    = "🔧 Tengo inconvenientes"
BTN_TICKET            = "🎫 Crear ticket"
BTN_DIAS              = "📅 ¿Cuántos días me quedan?"
BTN_PROMOCIONES       = "🎁 ¿Qué promociones hay?"
BTN_COMPRAR           = "💳 Comprar Netflix"
BTN_PLANES            = "💎 Ver planes"
BTN_SI_TV             = "✅ Sí, actívame en mi TV"
BTN_NO_TV             = "❌ No gracias, ya sé usar cookies"
BTN_ACTIVAR_TV_NUEVO  = "📺 Necesito activar TV de nuevo"
BTN_CELULAR_TUT       = "📱 Desde mi celular"
BTN_PC_TUT            = "💻 Desde mi computadora/laptop"
BTN_COMPRAR_TELEGRAM  = "🤖 Comprar aquí en Telegram"
BTN_COMPRAR_WHATSAPP  = "📱 Comprar por WhatsApp"
BTN_TIPO_TV           = "📺 TV / PC / Laptop"
BTN_TIPO_CEL          = "📱 Celular Xiaomi / Redmi"
BTN_TIPO_RAPIDO       = "⚡ Acceso rápido S/2.5"
BTN_CONFIRMAR         = "✅ Confirmar"
BTN_CANCELAR_VENTA    = "❌ Cancelar"
BTN_MENU              = "🏠 Menú principal"
BTN_REFERIDOS         = "👥 Mis referidos"
BTN_MAYORISTA         = "🏪 Soy Proveedor"
BTN_MAYOR_6           = "📦 Pack 6 créditos — S/24 (S/4 c/u)"
BTN_MAYOR_10          = "📦 Pack 10 créditos — S/37 (S/3.70 c/u)"
BTN_MAYOR_20          = "📦 Pack 20 créditos — S/70 (S/3.50 c/u)"
BTN_MAYOR_CANJEAR     = "🎟️ Canjear crédito (entregar cuenta)"
BTN_MAYOR_SALDO       = "💰 Ver mis créditos"
BTN_MAYOR_HISTORIAL   = "📋 Mi historial"
BTN_MAYOR_COMPRAR_MAS = "➕ Comprar más créditos"

# Almacén temporal para pagos mayoristas pendientes
pendientes_mayorista = {}

pendientes_venta = {}  

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════
#  GOOGLE SHEETS — CONEXIÓN
# ══════════════════════════════════════════════
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_json = os.environ.get("GOOGLE_CREDS")
    if creds_json:
        info = json.loads(creds_json)
    else:
        with open("bot-netflix-494823.json") as f:
            info = json.load(f)
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

# ══════════════════════════════════════════════
#  NORMALIZAR CELULAR
# ══════════════════════════════════════════════
def normalizar_celular(raw: str) -> str:
    cel = re.sub(r'\D', '', raw.strip())
    if cel.startswith("51") and len(cel) > 9:
        cel = cel[2:]
    return cel

# ══════════════════════════════════════════════
#  EXCEL — CLIENTES Y TICKETS
# ══════════════════════════════════════════════
def leer_cliente(celular_buscado: str):
    try:
        cel  = normalizar_celular(celular_buscado)
        gc   = get_gspread_client()
        ws   = gc.open_by_key(SHEET_ID_CLIENTES).worksheet("NETFLIX")
        rows = ws.get_all_values()
        for row_idx, row in enumerate(rows, start=1):
            if row_idx < 10:
                continue
            while len(row) < 13:
                row.append("")
            raw_cel = row[4]
            if not raw_cel:
                continue
            if normalizar_celular(str(raw_cel)) != cel:
                continue
            expiracion = row[10]
            dias_rest  = None
            if expiracion:
                for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
                    try:
                        exp_d     = datetime.strptime(str(expiracion).strip(), fmt).date()
                        dias_rest = (exp_d - date.today()).days
                        break
                    except ValueError:
                        continue
            try:
                precio_raw = str(row[9]).upper().replace("S/", "").replace(",", ".").strip()
                precio = float(precio_raw) if precio_raw else 0.0
            except (ValueError, AttributeError):
                precio = 0.0
            return {
                "row_idx":              row_idx,
                "nombre":               row[3].strip(),
                "celular":              cel,
                "cookie":               row[5].strip(),
                "precio":               precio,
                "dias_restantes":       dias_rest,
                "telegram_id_guardado": int(row[12]) if row[12] else None,
            }
        return None
    except Exception as e:
        logger.error(f"Error leer_cliente: {e}")
        return None

def buscar_cliente_por_numero(celular: str):
    """Busca un cliente en la hoja NETFLIX por número de celular."""
    try:
        gc   = get_gspread_client()
        ws   = gc.open_by_key(SHEET_ID_CLIENTES).worksheet("NETFLIX")
        rows = ws.get_all_values()
        celular_norm = normalizar_celular(celular)
        for row_idx, row in enumerate(rows, start=1):
            if row_idx < 10: continue
            while len(row) < 13: row.append("")
            if normalizar_celular(row[4]) == celular_norm:
                return {
                    "row_idx":    row_idx,
                    "nombre":     row[3].strip(),
                    "celular":    row[4].strip(),
                    "cookie":     row[5].strip(),
                    "precio":     float(row[9]) if row[9] else 0.0,
                    "telegram_id": row[12].strip() if len(row) > 12 else "",
                }
        return None
    except Exception as e:
        logger.error(f"Error buscar_cliente_por_numero: {e}")
        return None

def buscar_cliente_por_telegram_id(telegram_id: int):
    try:
        gc   = get_gspread_client()
        ws   = gc.open_by_key(SHEET_ID_CLIENTES).worksheet("NETFLIX")
        rows = ws.get_all_values()
        for row_idx, row in enumerate(rows, start=1):
            if row_idx < 10:
                continue
            while len(row) < 13:
                row.append("")
            if row[12] and str(row[12]).strip() == str(telegram_id):
                expiracion = row[10]
                dias_rest  = None
                if expiracion:
                    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
                        try:
                            exp_d     = datetime.strptime(str(expiracion).strip(), fmt).date()
                            dias_rest = (exp_d - date.today()).days
                            break
                        except ValueError:
                            continue
                return {
                    "row_idx":              row_idx,
                    "nombre":               row[3].strip(),
                    "celular":              row[4].strip(),
                    "cookie":               row[5].strip(),
                    "precio":               float(row[9]) if row[9] else 0.0,
                    "dias_restantes":       dias_rest,
                    "telegram_id_guardado": telegram_id,
                }
        return None
    except Exception as e:
        logger.error(f"Error buscar_cliente_por_telegram_id: {e}")
        return None

def guardar_telegram_id(row_idx: int, telegram_id: int):
    try:
        gc = get_gspread_client()
        ws = gc.open_by_key(SHEET_ID_CLIENTES).worksheet("NETFLIX")
        ws.update_cell(row_idx, 13, telegram_id)
    except Exception as e:
        logger.error(f"Error guardar_telegram_id: {e}")

def guardar_cookie_en_cliente(row_idx: int, cookie: str):
    try:
        gc = get_gspread_client()
        ws = gc.open_by_key(SHEET_ID_CLIENTES).worksheet("NETFLIX")
        ws.update_cell(row_idx, 6, cookie)
    except Exception as e:
        logger.error(f"Error guardar_cookie_en_cliente: {e}")

def agregar_cliente_nuevo(nombre: str, celular: str, precio: float, dispositivo: str, cookie: str = ""):
    try:
        gc  = get_gspread_client()
        ws  = gc.open_by_key(SHEET_ID_CLIENTES).worksheet("NETFLIX")
        exp = (date.today() + timedelta(days=30)).strftime("%d/%m/%Y")
        # table_range="C9" ancla desde C9 ignorando el banner visual del Sheet
        # Columnas desde C: dispositivo(C), nombre(D), celular(E), cookie(F), ..., precio(J), exp(K)
        ws.append_row([dispositivo, nombre, celular, cookie, "", "", "", precio, exp, "", ""], table_range="C9")
    except Exception as e:
        logger.error(f"Error agregar_cliente_nuevo: {e}")

def registrar_visita(telegram_id: int, nombre: str, username: str, accion: str):
    try:
        gc = get_gspread_client()
        ws = gc.open_by_key(SHEET_ID_CLIENTES).worksheet("VISITAS")
        ws.append_row([now_peru(), str(telegram_id), nombre, username or "", accion])
    except Exception as e:
        logger.error(f"Error registrar_visita: {e}")

def registrar_historial(celular, nombre, cookie, token_url):
    try:
        # Formatear cookie → NetflixId=... (URL-encoding preservado, sin urllib.parse.unquote)
        cookie_excel = formatear_cookie_msg(cookie) if cookie else cookie

        # Formatear token → https://netflix.com/?nftoken=...
        if token_url and "nftoken=" in token_url:
            token_raw   = token_url.split("nftoken=")[1]
            token_excel = f"https://netflix.com/?nftoken={token_raw}"
        else:
            token_excel = token_url

        gc = get_gspread_client()
        ws = gc.open_by_key(SHEET_ID_CLIENTES).worksheet("HISTORIAL")
        ws.append_row([now_peru(), celular, nombre, cookie_excel, token_excel])
    except Exception as e:
        logger.error(f"Error registrar_historial: {e}")

def registrar_ticket_sheets(cliente, motivo):
    try:
        gc = get_gspread_client()
        ws = gc.open_by_key(SHEET_ID_CLIENTES).worksheet("TICKETS")
        ticket_id = f"TK-{datetime.now().strftime('%d%H%M')}"
        ws.append_row([now_peru(), ticket_id, cliente["nombre"], cliente["celular"], motivo, "PENDIENTE", cliente.get("cookie", "")])
        return ticket_id
    except Exception as e:
        logger.error(f"Error registrar_ticket_sheets: {e}")
        return None

def resolver_ticket_sheets(ticket_id: str):
    """Busca el ticket por ID, lo marca RESUELTO y devuelve el celular del cliente."""
    try:
        gc = get_gspread_client()
        ws = gc.open_by_key(SHEET_ID_CLIENTES).worksheet("TICKETS")
        celdas = ws.findall(ticket_id)
        if not celdas:
            return None, None
        for celda in celdas:
            fila = ws.row_values(celda.row)
            # col B = ticket_id (índice 1)
            if len(fila) > 1 and fila[1] == ticket_id:
                ws.update_cell(celda.row, 6, "RESUELTO")  # col F = estado
                ws.update_cell(celda.row, 7, now_peru())  # col G = fecha resolución (opcional)
                celular = fila[3] if len(fila) > 3 else None
                nombre  = fila[2] if len(fila) > 2 else "Cliente"
                return celular, nombre
        return None, None
    except Exception as e:
        logger.error(f"Error resolver_ticket_sheets: {e}")
        return None, None

def registrar_venta_sheets(datos: dict, estado: str = "PENDIENTE"):
    try:
        gc = get_gspread_client()
        ws = gc.open_by_key(SHEET_ID_CLIENTES).worksheet("VENTAS")
        ws.append_row([
            now_peru(),
            datos.get("nombre", ""),
            datos.get("celular", ""),
            datos.get("plan", ""),
            f"S/{datos.get('precio', '')}",
            datos.get("dispositivo", ""),
            estado,
        ])
    except Exception as e:
        logger.error(f"Error registrar_venta_sheets: {e}")

def actualizar_estado_venta(celular: str, nuevo_estado: str):
    try:
        gc   = get_gspread_client()
        ws   = gc.open_by_key(SHEET_ID_CLIENTES).worksheet("VENTAS")
        rows = ws.get_all_values()
        for i, row in enumerate(rows, start=1):
            if len(row) > 6 and normalizar_celular(str(row[2])) == normalizar_celular(celular) and row[6] == "PENDIENTE":
                ws.update_cell(i, 7, nuevo_estado)
                return
    except Exception as e:
        logger.error(f"Error actualizar_estado_venta: {e}")

# ══════════════════════════════════════════════
#  REFERIDOS
# ══════════════════════════════════════════════
def generar_codigo_ref(telegram_id: int) -> str:
    import hashlib
    h = hashlib.md5(str(telegram_id).encode()).hexdigest()[:4].upper()
    return f"NEX-{h}"

def obtener_datos_referido(telegram_id: int) -> dict:
    try:
        gc   = get_gspread_client()
        ws   = gc.open_by_key(SHEET_ID_CLIENTES).worksheet("REFERIDOS")
        rows = ws.get_all_values()
        for row_idx, row in enumerate(rows, start=1):
            if len(row) > 1 and str(row[1]).strip() == str(telegram_id):
                return {
                    "row_idx":          row_idx,
                    "creditos":         int(row[3]) if row[3] else 0,
                    "referidos_hechos": int(row[4]) if row[4] else 0,
                    "codigo":           row[5] if len(row) > 5 else generar_codigo_ref(telegram_id),
                }
        return None
    except Exception as e:
        logger.error(f"Error obtener_datos_referido: {e}")
        return None

def registrar_nuevo_referido(telegram_id: int, nombre: str) -> dict:
    try:
        gc     = get_gspread_client()
        ws     = gc.open_by_key(SHEET_ID_CLIENTES).worksheet("REFERIDOS")
        codigo = generar_codigo_ref(telegram_id)
        fecha  = now_peru()
        ws.append_row([fecha, str(telegram_id), nombre, 1, 0, codigo])
        return {"creditos": 1, "referidos_hechos": 0, "codigo": codigo}
    except Exception as e:
        logger.error(f"Error registrar_nuevo_referido: {e}")
        return None

def sumar_referido(codigo_ref: str, telegram_id_nuevo: int, nombre_nuevo: str) -> bool:
    try:
        gc   = get_gspread_client()
        ws   = gc.open_by_key(SHEET_ID_CLIENTES).worksheet("REFERIDOS")
        rows = ws.get_all_values()
        for row_idx, row in enumerate(rows, start=1):
            if len(row) > 5 and row[5].strip().upper() == codigo_ref.strip().upper():
                referidos = int(row[4]) if row[4] else 0
                creditos  = int(row[3]) if row[3] else 0
                referidos += 1
                if referidos % 5 == 0:
                    creditos += 1
                ws.update_cell(row_idx, 4, creditos)
                ws.update_cell(row_idx, 5, referidos)
                return True
        return False
    except Exception as e:
        logger.error(f"Error sumar_referido: {e}")
        return False

def usar_credito(telegram_id: int) -> bool:
    try:
        gc   = get_gspread_client()
        ws   = gc.open_by_key(SHEET_ID_CLIENTES).worksheet("REFERIDOS")
        rows = ws.get_all_values()
        for row_idx, row in enumerate(rows, start=1):
            if len(row) > 1 and str(row[1]).strip() == str(telegram_id):
                creditos = int(row[3]) if row[3] else 0
                if creditos > 0:
                    ws.update_cell(row_idx, 4, creditos - 1)
                    return True
        return False
    except Exception as e:
        logger.error(f"Error usar_credito: {e}")
        return False

# ══════════════════════════════════════════════
#  MAYORISTAS — GOOGLE SHEETS
# ══════════════════════════════════════════════
def obtener_mayorista(telegram_id: int) -> dict:
    """Devuelve datos del proveedor mayorista o None si no existe."""
    try:
        gc   = get_gspread_client()
        ws   = gc.open_by_key(SHEET_ID_CLIENTES).worksheet("MAYORISTAS")
        rows = ws.get_all_values()
        for row_idx, row in enumerate(rows, start=1):
            if row_idx == 1: continue  # encabezado
            while len(row) < 6: row.append("")
            if str(row[1]).strip() == str(telegram_id):
                return {
                    "row_idx":  row_idx,
                    "nombre":   row[2].strip(),
                    "creditos": int(row[3]) if row[3] else 0,
                    "total_comprados": int(row[4]) if row[4] else 0,
                    "fecha_registro": row[5].strip(),
                }
        return None
    except Exception as e:
        logger.error(f"Error obtener_mayorista: {e}")
        return None

def registrar_mayorista_nuevo(telegram_id: int, nombre: str) -> dict:
    try:
        gc = get_gspread_client()
        ws = gc.open_by_key(SHEET_ID_CLIENTES).worksheet("MAYORISTAS")
        ws.append_row([now_peru(), str(telegram_id), nombre, 0, 0, now_peru()])
        return {"creditos": 0, "total_comprados": 0, "nombre": nombre}
    except Exception as e:
        logger.error(f"Error registrar_mayorista_nuevo: {e}")
        return None

def sumar_creditos_mayorista(telegram_id: int, cantidad: int):
    try:
        gc   = get_gspread_client()
        ws   = gc.open_by_key(SHEET_ID_CLIENTES).worksheet("MAYORISTAS")
        rows = ws.get_all_values()
        for row_idx, row in enumerate(rows, start=1):
            if str(row[1]).strip() == str(telegram_id):
                creditos_act    = int(row[3]) if row[3] else 0
                total_act       = int(row[4]) if row[4] else 0
                ws.update_cell(row_idx, 4, creditos_act + cantidad)
                ws.update_cell(row_idx, 5, total_act + cantidad)
                return True
        return False
    except Exception as e:
        logger.error(f"Error sumar_creditos_mayorista: {e}")
        return False

def usar_credito_mayorista(telegram_id: int) -> bool:
    try:
        gc   = get_gspread_client()
        ws   = gc.open_by_key(SHEET_ID_CLIENTES).worksheet("MAYORISTAS")
        rows = ws.get_all_values()
        for row_idx, row in enumerate(rows, start=1):
            if str(row[1]).strip() == str(telegram_id):
                creditos = int(row[3]) if row[3] else 0
                if creditos < 1: return False
                ws.update_cell(row_idx, 4, creditos - 1)
                return True
        return False
    except Exception as e:
        logger.error(f"Error usar_credito_mayorista: {e}")
        return False

def registrar_canje_mayorista(telegram_id: int, nombre_prov: str, etiqueta_cliente: str, cookie: str, token_url: str):
    """Guarda cada canje en la hoja MAYOR_CANJES para historial."""
    try:
        gc = get_gspread_client()
        ws = gc.open_by_key(SHEET_ID_CLIENTES).worksheet("MAYOR_CANJES")
        exp = (date.today() + timedelta(days=30)).strftime("%d/%m/%Y")
        ws.append_row([now_peru(), str(telegram_id), nombre_prov, etiqueta_cliente, cookie, token_url or "", exp, "ACTIVO"])
    except Exception as e:
        logger.error(f"Error registrar_canje_mayorista: {e}")

def obtener_historial_mayorista(telegram_id: int) -> list:
    try:
        gc   = get_gspread_client()
        ws   = gc.open_by_key(SHEET_ID_CLIENTES).worksheet("MAYOR_CANJES")
        rows = ws.get_all_values()
        canjes = []
        for row in rows[1:]:
            while len(row) < 8: row.append("")
            if str(row[1]).strip() == str(telegram_id):
                canjes.append({
                    "fecha":    row[0],
                    "etiqueta": row[3],
                    "vence":    row[6],
                    "estado":   row[7],
                })
        return canjes[-10:]  # últimos 10
    except Exception as e:
        logger.error(f"Error obtener_historial_mayorista: {e}")
        return []

def registrar_venta_mayorista_sheets(datos: dict):
    try:
        gc = get_gspread_client()
        ws = gc.open_by_key(SHEET_ID_CLIENTES).worksheet("VENTAS")
        ws.append_row([
            now_peru(),
            datos.get("nombre", ""),
            datos.get("telegram_id", ""),
            f"MAYORISTA {datos.get('cantidad', '')} créditos",
            f"S/{datos.get('total', '')}",
            "MAYORISTA",
            "PENDIENTE",
        ])
    except Exception as e:
        logger.error(f"Error registrar_venta_mayorista_sheets: {e}")

# ══════════════════════════════════════════════
#  RECORDATORIOS AUTOMÁTICOS
# ══════════════════════════════════════════════
async def job_recordatorios(context: ContextTypes.DEFAULT_TYPE):
    """Job que corre diariamente para avisar a clientes que vencen en 3 días o hoy."""
    try:
        gc   = get_gspread_client()
        ws   = gc.open_by_key(SHEET_ID_CLIENTES).worksheet("NETFLIX")
        rows = ws.get_all_values()
        hoy  = date.today()
        enviados = 0

        for row_idx, row in enumerate(rows, start=1):
            if row_idx < 10: continue
            while len(row) < 13: row.append("")
            telegram_id_str = str(row[12]).strip()
            expiracion_str  = str(row[10]).strip()
            nombre          = str(row[3]).strip() or "Cliente"

            if not telegram_id_str or not expiracion_str:
                continue

            try:
                telegram_id = int(telegram_id_str)
            except ValueError:
                continue

            exp_date = None
            for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
                try:
                    exp_date = datetime.strptime(expiracion_str, fmt).date()
                    break
                except ValueError:
                    continue
            if not exp_date:
                continue

            dias = (exp_date - hoy).days

            if dias == 3:
                try:
                    await context.bot.send_message(
                        chat_id=telegram_id,
                        text=(
                            f"⏰ *¡Hola {nombre}!*\n\n"
                            f"Tu suscripción de *Nexus Streaming* vence en *3 días* "
                            f"({exp_date.strftime('%d/%m/%Y')}).\n\n"
                            "💳 Renueva ahora y no pierdas el acceso:\n"
                            f"{WHATSAPP_LINK}"
                        ),
                        parse_mode="Markdown"
                    )
                    enviados += 1
                except Exception:
                    pass

            elif dias == 0:
                try:
                    await context.bot.send_message(
                        chat_id=telegram_id,
                        text=(
                            f"🚨 *¡{nombre}, tu suscripción vence HOY!*\n\n"
                            "No pierdas tu acceso a Netflix. Renueva ahora:\n"
                            f"{WHATSAPP_LINK}"
                        ),
                        parse_mode="Markdown"
                    )
                    enviados += 1
                except Exception:
                    pass

        logger.info(f"[RECORDATORIOS] Enviados: {enviados}")
    except Exception as e:
        logger.error(f"[RECORDATORIOS] Error: {e}")

# ══════════════════════════════════════════════
def _es_cuenta_premium(rows, start_idx):
    """Revisa hacia atrás desde la fila dada si el bloque tiene Plan: Premium y Max Streams: 4."""
    plan_premium = False
    max_streams_4 = False
    for k in range(start_idx, max(0, start_idx - 25), -1):
        v = str(rows[k][0]).strip() if rows[k] else ""
        if "Plan: Premium" in v:
            plan_premium = True
        if "Max Streams: 4" in v:
            max_streams_4 = True
        if "PREMIUM ACCOUNT" in v:
            break
    return plan_premium or max_streams_4

#  EXCEL — COOKIES POOL
# ══════════════════════════════════════════════
def obtener_pool(precio: float):
    try:
        gc   = get_gspread_client()
        ws   = gc.open_by_key(SHEET_ID_COOKIES).get_worksheet(0)
        rows = ws.get_all_values()
        espanol = []
        aleatorio = []
        pais_act = ""
        cod_act  = ""
        i = 0
        while i < len(rows):
            val = str(rows[i][0]).strip() if rows[i] else ""
            if "Country:" in val:
                pais_act = re.sub(r"[^\w\s]", "", val.split("Country:")[1]).strip()
                m = re.search(r'\b([A-Z]{2})\b', val)
                if m:
                    cod_act = m.group(1)
            if "Direct Login URL:" in val:
                entregado = any(x in val.lower() for x in ["estado: entregado", "estado: muerta"])
                j = i + 1
                cookie_val = None
                cookie_row = None
                cookie_col_f = ""
                while j < len(rows):
                    v2 = str(rows[j][0]).strip() if rows[j] else ""
                    if "Cookie:" in v2:
                        cookie_val = re.sub(r".*Cookie:\s*", "", v2).strip()
                        cookie_row = j + 1
                        # Verificar columna F de esa fila
                        cookie_col_f = str(rows[j][5]).strip() if len(rows[j]) > 5 else ""
                        break
                    if "------" in v2:
                        break
                    j += 1
                # Excluir si está entregada O si columna F dice COOKIE MUERTA
                if cookie_val and not entregado and "COOKIE MUERTA" not in cookie_col_f and _es_cuenta_premium(rows, i):
                    entry = (cookie_val, pais_act, cod_act, cookie_row)
                    if cod_act in CODIGOS_ESPANOL or pais_act in NOMBRES_ESPANOL:
                        espanol.append(entry)
                    else:
                        aleatorio.append(entry)
            i += 1
        if precio >= 10:
            # Plan español: preferir español, pero si no hay → fallback random
            if espanol:
                return espanol, False   # (pool, es_fallback)
            else:
                return aleatorio, True  # fallback a random — avisar al cliente
        else:
            return (aleatorio if aleatorio else espanol), False
    except Exception as e:
        logger.error(f"Error obtener_pool: {e}")
        return [], False

def obtener_pool_por_pais(codigo_pais: str):
    try:
        gc   = get_gspread_client()
        ws   = gc.open_by_key(SHEET_ID_COOKIES).get_worksheet(0)
        rows = ws.get_all_values()
        resultado = []
        pais_act = ""
        cod_act  = ""
        i = 0
        while i < len(rows):
            val = str(rows[i][0]).strip() if rows[i] else ""
            if "Country:" in val:
                pais_act = re.sub(r"[^\w\s]", "", val.split("Country:")[1]).strip()
                m = re.search(r'\b([A-Z]{2})\b', val)
                if m:
                    cod_act = m.group(1)
            if "Direct Login URL:" in val:
                entregado = any(x in val.lower() for x in ["estado: entregado", "estado: muerta"])
                j = i + 1
                cookie_val = None
                cookie_row = None
                cookie_col_f = ""
                while j < len(rows):
                    v2 = str(rows[j][0]).strip() if rows[j] else ""
                    if "Cookie:" in v2:
                        cookie_val = re.sub(r".*Cookie:\s*", "", v2).strip()
                        cookie_row = j + 1
                        cookie_col_f = str(rows[j][5]).strip() if len(rows[j]) > 5 else ""
                        break
                    if "------" in v2:
                        break
                    j += 1
                if cookie_val and not entregado and "COOKIE MUERTA" not in cookie_col_f and cod_act.upper() == codigo_pais.upper() and _es_cuenta_premium(rows, i):
                    resultado.append((cookie_val, pais_act, cod_act, cookie_row))
            i += 1
        return resultado
    except Exception as e:
        logger.error(f"Error obtener_pool_por_pais: {e}")
        return []

def obtener_paises_disponibles():
    try:
        gc   = get_gspread_client()
        ws   = gc.open_by_key(SHEET_ID_COOKIES).get_worksheet(0)
        rows = ws.get_all_values()
        paises   = {}
        pais_act = ""
        cod_act  = ""
        # FIX: enumerate para tener índice i disponible en _es_cuenta_premium
        for i, row in enumerate(rows):
            val = str(row[0]).strip() if row else ""
            if "Country:" in val:
                pais_act = re.sub(r"[^\w\s]", "", val.split("Country:")[1]).strip()
                m = re.search(r'\b([A-Z]{2})\b', val)
                if m:
                    cod_act = m.group(1)
            if "Direct Login URL:" in val:
                entregado = any(x in val.lower() for x in ["estado: entregado", "estado: muerta"])
                # FIX: usar i (índice actual) en lugar de i - 1 (que era incorrecto)
                if not entregado and cod_act and _es_cuenta_premium(rows, i):
                    if cod_act not in paises:
                        paises[cod_act] = [pais_act, 0]
                    paises[cod_act][1] += 1
        return paises
    except Exception as e:
        logger.error(f"Error obtener_paises_disponibles: {e}")
        return {}

def marcar_cookie_entregada(row_idx_cookie: int):
    try:
        gc   = get_gspread_client()
        ws   = gc.open_by_key(SHEET_ID_COOKIES).get_worksheet(0)
        rows = ws.get_all_values()
        for i in range(row_idx_cookie - 2, max(0, row_idx_cookie - 10), -1):
            val = str(rows[i][0]).strip() if rows[i] else ""
            if "Direct Login URL:" in val:
                ws.update_cell(i + 1, 1, "🔗 Direct Login URL: Estado: Entregado")
                return
    except Exception as e:
        logger.error(f"Error marcar_cookie_entregada: {e}")

def marcar_cookie_muerta(row_idx_cookie: int):
    try:
        gc   = get_gspread_client()
        ws   = gc.open_by_key(SHEET_ID_COOKIES).get_worksheet(0)
        rows = ws.get_all_values()
        for i in range(row_idx_cookie - 2, max(0, row_idx_cookie - 10), -1):
            val = str(rows[i][0]).strip() if rows[i] else ""
            if "Direct Login URL:" in val:
                ws.update_cell(i + 1, 1, "🔗 Direct Login URL: Estado: MUERTA ❌")
                return
    except Exception as e:
        logger.error(f"Error marcar_cookie_muerta: {e}")

def contar_stock():
    try:
        gc   = get_gspread_client()
        ws   = gc.open_by_key(SHEET_ID_COOKIES).get_worksheet(0)
        rows = ws.get_all_values()
        total = entregadas = muertas = pausadas = espanol = aleatorio = 0
        pais_act = cod_act = ""
        for row in rows:
            val  = str(row[0]).strip() if row else ""
            col6 = str(row[5]).strip() if len(row) > 5 else ""
            col7 = str(row[6]).strip() if len(row) > 6 else ""
            if "Country:" in val:
                pais_act = re.sub(r"[^\w\s]", "", val.split("Country:")[1]).strip()
                m = re.search(r'\b([A-Z]{2})\b', val)
                if m:
                    cod_act = m.group(1)
            if "Direct Login URL:" in val:
                total += 1
                es_esp = cod_act in CODIGOS_ESPANOL or pais_act in NOMBRES_ESPANOL
                # Leer estado desde col6/col7 O desde el valor de la celda
                val_lower = val.lower()
                if "estado: muerta" in val_lower or "cookie muerta" in col6.lower() or col7 == "💀":
                    muertas += 1
                elif "estado: entregado" in val_lower or "entregado" in col6.lower():
                    entregadas += 1
                elif "en pausa" in col6.lower() or col7 == "⚠️":
                    pausadas += 1
                else:
                    # Disponible real
                    if es_esp: espanol += 1
                    else: aleatorio += 1
        disponibles = espanol + aleatorio
        return {
            "total": total,
            "disponibles": disponibles,
            "espanol": espanol,
            "aleatorio": aleatorio,
            "pausadas": pausadas,
            "entregadas": entregadas,
            "muertas": muertas,
        }
    except Exception as e:
        logger.error(f"Error contar_stock: {e}")
        return None

# ══════════════════════════════════════════════
#  COOKIES — VERIFICACIÓN Y TOKEN
# ══════════════════════════════════════════════
def _normalizar_cookie(cookie_texto: str) -> str:
    """
    Si la cookie no comienza con 'NetflixId=' pero parece un token válido
    (largo, sin espacios, posiblemente URL-encoded), le agrega el prefijo
    automáticamente para que el checker pueda procesarla.
    """
    texto = cookie_texto.strip()
    if "NetflixId=" not in texto and len(texto) > 40 and " " not in texto:
        texto = "NetflixId=" + texto
    return texto

def _parsear_cookie(cookie_texto: str) -> dict:
    # 🔧 FIX: normalizar antes de parsear
    cookie_texto = _normalizar_cookie(cookie_texto)
    cookies = {}
    lineas   = cookie_texto.strip().split('\n')
    netscape = [l for l in lineas if '\t' in l and not l.startswith('#')]
    if netscape:
        for line in netscape:
            parts = line.strip().split('\t')
            if len(parts) >= 7:
                cookies[parts[5]] = parts[6]
        if cookies:
            return cookies
    for part in cookie_texto.replace('\n', '; ').split(';'):
        part = part.strip()
        if '=' in part:
            k, v = part.split('=', 1)
            if k.strip() and v.strip():
                cookies[k.strip()] = v.strip()
    return cookies

def _extraer_netflix_id(cookie_texto: str):
    # No usar urllib.parse.unquote para no romper el URL-encoding requerido por Cookie-Editor
    texto = _normalizar_cookie(cookie_texto.strip())
    match = re.search(r"(?<!\w)NetflixId=([^;,\s]+)", texto)
    if match:
        return match.group(1)
    return texto

def formatear_cookie_msg(cookie_raw: str) -> str:
    netflix_id = _extraer_netflix_id(cookie_raw)
    return f"NetflixId={netflix_id}" if netflix_id else cookie_raw

_NFTOKEN_API_URL = "https://ios.prod.ftl.netflix.com/iosui/user/15.48"
_NFTOKEN_PARAMS  = {
    "appVersion":    "15.48.1",
    "config":        '{"gamesInTrailersEnabled":"false","billboardEnabled":"true","useCDSGalleryEnabled":"true"}',
    "device_type":   "NFAPPL-02-",
    "esn":           "NFAPPL-02-IPHONE8%3D1-PXA-02026U9VV5O8AUKEAEO8PUJETCGDD4PQRI9DEB3MDLEMD0EACM4CS78LMD334MN3MQ3NMJ8SU9O9MVGS6BJCURM1PH1MUTGDPF4S4200",
    "idiom":         "phone",
    "iosVersion":    "15.8.5",
    "isTablet":      "false",
    "languages":     "en-US",
    "locale":        "en-US",
    "maxDeviceWidth":"375",
    "model":         "saget",
    "modelType":     "IPHONE8-1",
    "odpAware":      "true",
    "path":          '["account","token","default"]',
    "pathFormat":    "graph",
    "pixelDensity":  "2.0",
    "progressive":   "false",
    "responseFormat":"json",
}
_NFTOKEN_HEADERS = {
    "User-Agent":                        "Argo/15.48.1 (iPhone; iOS 15.8.5; Scale/2.00)",
    "x-netflix.request.attempt":         "1",
    "x-netflix.request.client.user.guid":"A4CS633D7VCBPE2GPK2HL4EKOE",
    "x-netflix.context.profile-guid":    "A4CS633D7VCBPE2GPK2HL4EKOE",
    "x-netflix.request.routing":         '{"path":"/nq/mobile/nqios/~15.48.0/user","control_tag":"iosui_argo"}',
    "x-netflix.context.app-version":     "15.48.1",
    "x-netflix.argo.translated":         "true",
    "x-netflix.context.form-factor":     "phone",
    "x-netflix.context.sdk-version":     "2012.4",
    "x-netflix.client.appversion":       "15.48.1",
    "x-netflix.context.max-device-width":"375",
    "x-netflix.context.ab-tests":        "",
    "x-netflix.client.type":             "argo",
    "x-netflix.client.ftl.esn":          "NFAPPL-02-IPHONE8=1-PXA-02026U9VV5O8AUKEAEO8PUJETCGDD4PQRI9DEB3MDLEMD0EACM4CS78LMD334MN3MQ3NMJ8SU9O9MVGS6BJCURM1PH1MUTGDPF4S4200",
    "x-netflix.context.locales":         "en-US",
    "x-netflix.client.iosversion":       "15.8.5",
    "accept-language":                   "en-US;q=1",
    "x-netflix.context.os-version":      "15.8.5",
    "x-netflix.request.client.context":  '{"appState":"foreground"}',
    "x-netflix.context.ui-flavor":       "argo",
    "x-netflix.argo.nfnsm":              "9",
    "x-netflix.context.pixel-density":   "2.0",
}

def generate_nftoken(cookie_texto: str):
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        netflix_id = _extraer_netflix_id(cookie_texto)
        if not netflix_id:
            return None
        headers = dict(_NFTOKEN_HEADERS)
        headers["Cookie"] = f"NetflixId={netflix_id}"
        response = requests.get(_NFTOKEN_API_URL, params=_NFTOKEN_PARAMS, headers=headers, timeout=20, verify=False)
        if response.status_code != 200:
            return None
        data = response.json()
        token_data = ((((data.get("value") or {}).get("account") or {}).get("token") or {}).get("default") or {})
        token = token_data.get("token")
        if not token:
            return None
        if "%" in token:
            token = urllib.parse.unquote(token)
        return f"https://www.netflix.com/unsupported?nftoken={token}"
    except Exception as e:
        return None

def _perfiles_desde_falcor(html: str) -> list:
    """
    Lee el falcorCache que Netflix embebe en el HTML de /ManageProfiles.
    Estructura exacta:
      netflix.falcorCache = {
        "profiles": {
          "GUID1": {"summary": {"$type":"atom","value":{"profileName":"...", "language":"es-MX", ...}}},
          ...
        },
        "profilesList": {"0":{"$type":"ref","value":["profiles","GUID1"]}, ...}
      }
    Retorna: [{"nombre": str, "lang": str}, ...]
    """
    import json as _json
    perfiles = []
    try:
        # Extraer netflix.falcorCache = {...};
        m = re.search(r'netflix\.falcorCache\s*=\s*(\{.+?\});\s*</script>', html, re.DOTALL)
        if not m:
            # Intentar sin el </script>
            m = re.search(r'netflix\.falcorCache\s*=\s*(\{.+?\});', html, re.DOTALL)
        if not m:
            logger.warning("[PERFILES] falcorCache no encontrado en HTML")
            return []

        cache = _json.loads(m.group(1))
        profiles_dict = cache.get("profiles", {})

        for guid, data in profiles_dict.items():
            if not isinstance(data, dict):
                continue
            summary_wrap = data.get("summary", {})
            # Puede venir como {"$type":"atom","value":{...}} o directo
            if isinstance(summary_wrap, dict) and "$type" in summary_wrap:
                summary = summary_wrap.get("value", {})
            else:
                summary = summary_wrap
            if not isinstance(summary, dict):
                continue
            nombre = summary.get("profileName", "")
            lang   = summary.get("language", "")
            if nombre:
                perfiles.append({"nombre": nombre, "lang": lang, "guid": guid})

        logger.info(f"[PERFILES] falcorCache → {len(perfiles)} perfiles: {[(p['nombre'], p['lang']) for p in perfiles]}")
    except Exception as e:
        logger.warning(f"[PERFILES] Error leyendo falcorCache: {e}")
    return perfiles


def detectar_perfiles_espanol(cookie_texto: str) -> dict:
    """
    Detecta TODOS los perfiles de la cuenta y cuáles están en español.
    Lee el falcorCache embebido en /ManageProfiles — contiene nombre + idioma
    de cada perfil directamente, sin necesidad de hacer SwitchProfile.

    Retorna: { "perfiles_espanol": [...], "todos_perfiles": [...], "ok": bool }
    """
    def _clasificar(perfiles_raw: list) -> dict:
        vistos = set()
        unicos = []
        for p in perfiles_raw:
            n = p.get("nombre", "").strip()
            if n and n not in vistos:
                vistos.add(n)
                unicos.append(p)
        todos      = [p["nombre"] for p in unicos]
        en_espanol = [p["nombre"] for p in unicos if p.get("lang", "").lower()[:2] == "es"]
        return {"perfiles_espanol": en_espanol, "todos_perfiles": todos, "ok": bool(todos)}

    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        cookies_dict = _parsear_cookie(cookie_texto)
        session = requests.Session()
        headers_web = {
            "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        for name, value in cookies_dict.items():
            session.cookies.set(name, value, domain=".netflix.com", path="/")

        # ── MÉTODO PRINCIPAL: GET /ManageProfiles → leer falcorCache ─────────
        # El falcorCache contiene exactamente {"profiles":{"GUID":{"summary":{"profileName":"...","language":"es-MX"}}}}
        try:
            r = session.get("https://www.netflix.com/ManageProfiles",
                            headers=headers_web, timeout=20,
                            allow_redirects=True, verify=False)
            if r.status_code == 200 and "login" not in r.url.lower():
                perfiles = _perfiles_desde_falcor(r.text)
                if perfiles:
                    resultado = _clasificar(perfiles)
                    logger.info(f"[PERFILES] ManageProfiles OK → {resultado}")
                    return resultado
        except Exception as e:
            logger.warning(f"[PERFILES] ManageProfiles falló: {e}")

        # ── FALLBACK 1: /browse también tiene falcorCache a veces ─────────────
        try:
            r2 = session.get("https://www.netflix.com/browse",
                             headers=headers_web, timeout=20,
                             allow_redirects=True, verify=False)
            if r2.status_code == 200 and "login" not in r2.url.lower():
                perfiles = _perfiles_desde_falcor(r2.text)
                if perfiles:
                    resultado = _clasificar(perfiles)
                    logger.info(f"[PERFILES] /browse falcorCache OK → {resultado}")
                    return resultado
        except Exception as e:
            logger.warning(f"[PERFILES] /browse falló: {e}")

        # ── FALLBACK 2: /account/profiles ─────────────────────────────────────
        try:
            r3 = session.get("https://www.netflix.com/account/profiles",
                             headers=headers_web, timeout=20,
                             allow_redirects=True, verify=False)
            if r3.status_code == 200 and "login" not in r3.url.lower():
                perfiles = _perfiles_desde_falcor(r3.text)
                if perfiles:
                    resultado = _clasificar(perfiles)
                    logger.info(f"[PERFILES] /account/profiles OK → {resultado}")
                    return resultado
        except Exception as e:
            logger.warning(f"[PERFILES] /account/profiles falló: {e}")

        logger.warning("[PERFILES] Todos los métodos fallaron")
        return {"perfiles_espanol": [], "todos_perfiles": [], "ok": False}

    except Exception as e:
        logger.warning(f"[PERFILES] Error general: {e}")
        return {"perfiles_espanol": [], "todos_perfiles": [], "ok": False}



def _parsear_fecha_netflix(html: str):
    """
    Extrae la fecha de vencimiento usando TODOS los métodos conocidos,
    en orden de confiabilidad. Retorna un objeto date o None.
    Métodos integrados desde 3 checkers profesionales.
    """
    from datetime import datetime as _dt, date as _date

    # ── MÉTODO 1 (Checker 3 / más confiable): GraphQL growthAccount ──
    # "GrowthNextBillingDate","date":"2025-07-15T..."
    m = re.search(r'"GrowthNextBillingDate"[^}]*"date"\s*:\s*"([^"T]+)T', html)
    if m:
        try:
            return _dt.strptime(m.group(1)[:10], "%Y-%m-%d").date()
        except ValueError:
            pass

    # ── MÉTODO 2 (Checker 3): localDate dentro de nextBillingDate ──
    # "nextBillingDate":{"localDate":"2025-07-15T..." o "localDate":"2025-07-15"}
    m = re.search(r'"nextBillingDate"\s*:\s*\{[^}]*"localDate"\s*:\s*"([^"T]+)', html)
    if m:
        try:
            return _dt.strptime(m.group(1)[:10], "%Y-%m-%d").date()
        except ValueError:
            pass

    # ── MÉTODO 3 (Checker 2): "localDate":"2025-07-15T..." suelto ──
    # Usado por cuentas de Indonesia, Lituania, Asia en general
    m = re.search(r'"localDate"\s*:\s*"([^"T]+)T?', html)
    if m:
        try:
            return _dt.strptime(m.group(1)[:10], "%Y-%m-%d").date()
        except ValueError:
            pass

    # ── MÉTODO 4 (Checker 1): estructura fieldType {"fieldType":"String","value":"..."} ──
    # "nextBillingDate":{"fieldType":"String","value":"July 15, 2025"} o ISO
    m = re.search(
        r'"nextBilling(?:Date)?"\s*:\s*\{\s*"fieldType"\s*:\s*"String"\s*,\s*"value"\s*:\s*"([^"]+)"',
        html
    )
    if not m:
        # También aparece como nextBilling sin Date en algunos mercados
        m = re.search(
            r'"nextBilling"\s*:\s*\{\s*"fieldType"\s*:\s*"String"\s*,\s*"value"\s*:\s*"([^"]+)"',
            html
        )
    if m:
        raw = m.group(1).strip()
        # Intentar ISO primero
        try:
            return _dt.strptime(raw[:10], "%Y-%m-%d").date()
        except ValueError:
            pass
        # Intentar formatos localizados comunes
        for fmt in ("%B %d, %Y", "%d %B %Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
            try:
                return _dt.strptime(raw, fmt).date()
            except ValueError:
                continue

    # ── MÉTODO 5: periodEndDate en milisegundos o segundos (timestamp Unix) ──
    m = re.search(r'"periodEndDate"\s*:\s*(\d{10,13})', html)
    if m:
        try:
            ts = int(m.group(1))
            if ts > 9_999_999_999:   # milisegundos → segundos
                ts = ts // 1000
            return _dt.utcfromtimestamp(ts).date()
        except (ValueError, OSError):
            pass

    # ── MÉTODO 6: nextBillingDate como string ISO puro ──
    # "nextBillingDate":"2025-07-15" o "nextBillingDate":"2025-07-15T00:00:00"
    m = re.search(r'"nextBillingDate"\s*:\s*"([^"]+)"', html)
    if m:
        raw = m.group(1)[:10]
        try:
            return _dt.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            pass

    # ── MÉTODO 7: nextBillingDate dentro de accountInfo (Checker 2 style) ──
    info_block = ""
    m_block = re.search(r'"accountInfo"\s*:\s*\{.*?"data"', html)
    if m_block:
        info_block = html[m_block.start():m_block.start() + 2000]
    if info_block:
        m = re.search(r'"nextBillingDate"\s*:\s*"([^"]+)"', info_block)
        if m:
            try:
                return _dt.strptime(m.group(1)[:10], "%Y-%m-%d").date()
            except ValueError:
                pass

    # ── MÉTODO 8 (fallback): cualquier fecha ISO en contexto de billing/period ──
    for pattern in [
        r'(?:billing|period|renew|renewal|expire|vencimiento|venciment)[^"]{0,80}"(\d{4}-\d{2}-\d{2})',
        r'"date"\s*:\s*"(\d{4}-\d{2}-\d{2})',
    ]:
        m = re.search(pattern, html, re.IGNORECASE)
        if m:
            try:
                candidate = _dt.strptime(m.group(1), "%Y-%m-%d").date()
                # Solo aceptar fechas futuras razonables (entre mañana y 2 años)
                today = _date.today()
                if today < candidate < _date(today.year + 2, today.month, today.day):
                    return candidate
            except ValueError:
                continue

    return None  # ningún método funcionó → días quedará como 99


def check_cookie(cookie_texto: str) -> dict:
    """
    Retorna siempre un dict con clave "estado":
      "OK"      → miembro activo con suficientes días
      "ON_HOLD" → cuenta en pausa / problema de pago
      "DEAD"    → redirige a login o no es CURRENT_MEMBER
    También incluye: country_code, dias_restantes (int), viva (bool, back-compat)
    Extracción de fecha con 8 métodos combinados de 3 checkers profesionales.
    """
    try:
        cookies = _parsear_cookie(cookie_texto)
        if not cookies:
            return {"estado": "DEAD", "viva": False}

        session = requests.Session()
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Pragma":          "no-cache",
        }
        for name, value in cookies.items():
            session.cookies.set(name, value, domain=".netflix.com", path="/")

        response = session.get(
            "https://www.netflix.com/account/membership",
            headers=headers, timeout=20, allow_redirects=True
        )
        if "login" in response.url.lower():
            return {"estado": "DEAD", "viva": False}

        html = response.text

        # ── Detectar ON_HOLD con señales exhaustivas (Checkers 1+3) ──────────
        on_hold_signals = [
            "MEMBERSHIP_ON_HOLD",
            '"isAccountOnHold":true',
            '"holdStatus":true',
            '"isUserOnHold":true',
            '"isOnHold":true',
            '"pastDue":true',
            '"isPastDue":true',
            "retry payment",
            "retrypayment",
            '"membershipStatus":"ON_HOLD"',
            '"membershipStatus":"PAYMENT_HOLD"',
            '"membershipStatus":"PAST_DUE"',
            '"membershipStatus":"PAYMENT_RETRY"',
            '"membershipStatus":"PAUSED"',
            '"membershipStatus":"SUSPENDED"',
            "PAYMENT_HOLD",
            "isAccountOnHold",
        ]
        if any(sig.lower() in html.lower() for sig in on_hold_signals):
            info = {"estado": "ON_HOLD", "viva": False}
            m = re.search(r'"countryOfSignup"\s*:\s*"([^"]+)"', html)
            if not m:
                m = re.search(r'"currentCountry"\s*:\s*"([^"]+)"', html)
            if m:
                info["country_code"] = m.group(1).upper()
            return info

        # ── Verificar membresía activa ────────────────────────────────────────
        # Aceptar tanto CURRENT_MEMBER como estado de extra_member (Checker 3)
        is_current = (
            '"membershipStatus":"CURRENT_MEMBER"' in html
            or '"membershipStatus": "CURRENT_MEMBER"' in html
        )
        # Cuentas extra-member tienen membershipStatus diferente pero son válidas
        extra_member_markers = [
            "assinante extra no plano de outra pessoa",
            "suscriptor extra en el plan de otra persona",
            "extra on someone",
            "abbonato extra sul piano",
        ]
        is_extra_member = any(m.lower() in html.lower() for m in extra_member_markers)

        if not is_current and not is_extra_member:
            return {"estado": "DEAD", "viva": False}

        info = {"estado": "OK", "viva": True}

        # ── País ──────────────────────────────────────────────────────────────
        for pat in [
            r'"countryOfSignup"\s*:\s*"([^"]+)"',
            r'"currentCountry"\s*:\s*"([^"]+)"',
            r'"country"\s*:\s*"([A-Z]{2})"',   # fallback corto
        ]:
            m = re.search(pat, html)
            if m:
                info["country_code"] = m.group(1).upper()
                info["country"]      = m.group(1)
                break

        # ── Días restantes con los 8 métodos ─────────────────────────────────
        from datetime import date as _date
        dias_restantes = 99   # default cuando ningún método extrae fecha
        end_date = _parsear_fecha_netflix(html)
        if end_date is not None:
            dias_restantes = max((end_date - _date.today()).days, 0)

        info["dias_restantes"] = dias_restantes
        return info

    except Exception:
        return {"estado": "DEAD", "viva": False}

# ══════════════════════════════════════════════
#  NUEVO: ACTIVAR TV
# ══════════════════════════════════════════════
def _decode_auth_url(raw: str) -> str:
    """Decodifica todos los escapes posibles del authURL de Netflix."""
    raw = raw.replace('\\x2F', '/').replace('\\x3D', '=').replace('\\x2B', '+')
    raw = raw.replace('\\u002F', '/').replace('\\u003D', '=').replace('\\u002B', '+')
    return raw

def activar_tv_con_codigo(cookie_texto: str, codigo_tv: str) -> dict:
    """
    Activa Netflix en TV usando el endpoint /tv2 (página real de vinculación de TV).
    Flujo: GET /tv2 con cookies → extrae authURL → POST /tv2 con código
    """
    try:
        cookies = _parsear_cookie(cookie_texto)
        if not cookies:
            return {'success': False, 'message': 'Cookie inválida.'}

        session = requests.Session()
        headers = {
            "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "es-PE,es;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
        }
        for name, value in cookies.items():
            session.cookies.set(name, value, domain='.netflix.com', path='/')

        # Paso 1: GET /tv2 — obtener la página con authURL en contexto TV
        resp = session.get("https://www.netflix.com/tv2", headers=headers, timeout=15, allow_redirects=True)
        logger.info(f"[TV] GET /tv2 status={resp.status_code} url_final={resp.url}")

        if 'login' in resp.url.lower():
            return {'success': False, 'message': 'La cookie no es válida para activar la TV.'}

        # Paso 2: extraer authURL del HTML de /tv2
        auth_match = re.search(r'"authURL"\s*:\s*"([^"]+)"', resp.text)
        if not auth_match:
            auth_match = re.search(r"'authURL'\s*:\s*'([^']+)'", resp.text)
        if not auth_match:
            auth_match = re.search(r'name=["\']authURL["\'][^>]*value=["\']([^"\']+)["\']', resp.text)
        if not auth_match:
            logger.error(f"[TV] authURL no encontrado en /tv2. url_final={resp.url}")
            return {'success': False, 'message': 'No se pudo obtener el token de seguridad. Intenta más tarde.'}

        auth_url = _decode_auth_url(auth_match.group(1))
        logger.info(f"[TV] authURL extraído OK (len={len(auth_url)})")

        # Paso 3: POST /tv2 con el código de TV
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        headers["Referer"]      = "https://www.netflix.com/tv2"
        headers["Origin"]       = "https://www.netflix.com"

        post_data = {
            "flow":                    "websiteSignUp",
            "authURL":                 auth_url,
            "flowMode":                "enterTvLoginRendezvousCode",
            "withFields":              "tvLoginRendezvousCode,isTvUrl2",
            "code":                    codigo_tv,
            "tvLoginRendezvousCode":   codigo_tv,
            "isTvUrl2":                "true",
            "action":                  "nextAction",
        }

        response = session.post(
            "https://www.netflix.com/tv2",
            headers=headers,
            data=post_data,
            allow_redirects=False,
            timeout=15,
        )

        location = response.headers.get('location', '')
        logger.info(f"[TV] POST /tv2 status={response.status_code} location={location}")

        # Éxito: Netflix redirige a /tv/out/success o /browse
        if response.status_code in (301, 302, 303) and any(x in location for x in [
            '/tv/out/success', '/browse', 'success'
        ]):
            return {'success': True, 'message': '¡TV vinculada con éxito! 🎉'}

        # Código incorrecto
        if any(x in response.text for x in [
            "That code wasn't right", "Este código no es correcto",
            "wasn't right", "code-error", "incorrect"
        ]):
            return {'success': False, 'message': 'Código incorrecto. Revisa bien la pantalla de tu TV y vuelve a intentarlo.'}

        # Si redirigió a cualquier lugar que no sea error, asumir éxito
        if response.status_code in (301, 302, 303) and location:
            logger.info(f"[TV] Redirección a {location} — asumiendo éxito")
            return {'success': True, 'message': '¡TV vinculada! Revisa tu televisor. 🎉'}

        # Netflix a veces responde 500 pero igual vincula la TV
        if response.status_code == 500:
            logger.info(f"[TV] status=500 — Netflix igual procesó la vinculación")
            return {'success': True, 'message': '¡TV vinculada! Revisa tu televisor en unos segundos. 🎉'}

        logger.warning(f"[TV] Respuesta inesperada status={response.status_code} body[:300]={response.text[:300]}")
        return {'success': False, 'message': 'No se pudo vincular. Asegúrate de que el código sea correcto y que Netflix esté abierto en tu TV.'}

    except requests.Timeout:
        return {'success': False, 'message': 'Tiempo de espera agotado. Intenta nuevamente.'}
    except Exception as e:
        logger.error(f"[TV] Error en activar_tv_con_codigo: {e}")
        return {'success': False, 'message': 'Error de conexión. Intenta nuevamente.'}

def resolver_cookie_valida(cliente: dict, app=None):
    # Si el cliente ya tiene cookie asignada y sigue OK, la devolvemos sin
    # importar los días restantes — el cliente no pierde su cuenta aunque
    # le queden pocos días. El límite de >= 5 días solo aplica al pool nuevo.
    if cliente.get("cookie"):
        info = check_cookie(cliente["cookie"])
        if info and info.get("estado") == "OK":
            pais_real = info.get("country_code", "") or ""
            token_url = generate_nftoken(cliente["cookie"])
            return cliente["cookie"], "propia_ok", None, token_url, pais_real

    pool, es_fallback_random = obtener_pool(cliente.get("precio", 0))
    for cookie_val, pais, codigo, row_idx in pool:
        info = check_cookie(cookie_val)
        estado = info.get("estado") if info else "DEAD"
        if estado == "OK" and info.get("dias_restantes", 99) >= 5:
            pais_real = info.get("country_code", pais) or pais
            token_url = generate_nftoken(cookie_val)
            if es_fallback_random:
                tipo = "nueva_random_fallback"   # era plan español pero no había → dimos random
            else:
                tipo = "nueva_espanol" if (codigo in CODIGOS_ESPANOL or pais in NOMBRES_ESPANOL) else "nueva_random"
            return cookie_val, tipo, row_idx, token_url, pais_real
        elif estado == "ON_HOLD":
            # Cuenta en pausa — saltar sin marcar muerta, puede revivir
            continue
        elif info and info.get("dias_restantes", 99) < 5 and estado == "OK":
            # Menos de 5 días — saltar sin marcar muerta
            continue
        else:
            # DEAD
            marcar_cookie_muerta(row_idx)
    return None, "sin_stock", None, None, ""
# ══════════════════════════════════════════════
#  TECLADOS
# ══════════════════════════════════════════════
def kb_menu():
    return ReplyKeyboardMarkup([
        [BTN_INCONVENIENTES, BTN_TICKET], [BTN_DIAS, BTN_PROMOCIONES],
        [BTN_COMPRAR, BTN_REFERIDOS],
        [BTN_MAYORISTA],
    ], resize_keyboard=True, one_time_keyboard=True)

def kb_mayorista():
    return ReplyKeyboardMarkup([
        [BTN_MAYOR_CANJEAR],
        [BTN_MAYOR_SALDO, BTN_MAYOR_HISTORIAL],
        [BTN_MAYOR_COMPRAR_MAS],
        [BTN_MENU],
    ], resize_keyboard=True, one_time_keyboard=True)

def kb_con_menu(botones: list):
    return ReplyKeyboardMarkup(
        botones + [[BTN_MENU]],
        resize_keyboard=True, one_time_keyboard=True
    )

def kb_si_no_tv():
    return ReplyKeyboardMarkup(
        [[BTN_SI_TV], [BTN_NO_TV], [BTN_MENU]],
        resize_keyboard=True, one_time_keyboard=True
    )

def formatear_token_msg(token_url, pais=""):
    pais_msg = f"\n🌍 *País de la cuenta:* `{pais}`" if pais else ""
    if token_url and "nftoken=" in token_url:
        token_raw = token_url.split("nftoken=")[1]
        return (
            f"{pais_msg}\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "🔗 *Link de acceso rápido:*\n\n"
            f"🌐 *Universal:*\n`https://netflix.com/?nftoken={token_raw}`\n\n"
            "_(Ábrelo en el navegador — válido aprox. 1 hora ⏱️)_"
        )
    return pais_msg if pais_msg else ""

# ══════════════════════════════════════════════
#  HANDLERS — PRINCIPALES Y REFERIDOS
# ══════════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    telegram_id = update.effective_user.id
    nombre      = update.effective_user.first_name or "Usuario"
    username    = update.effective_user.username or ""

    cliente = buscar_cliente_por_telegram_id(telegram_id)
    if not cliente:
        registrar_visita(telegram_id, nombre, username, "start")

    # Referidos
    codigo_ref = context.args[0] if context.args else None
    datos_ref  = obtener_datos_referido(telegram_id)
    if codigo_ref and datos_ref is None:
        valido = sumar_referido(codigo_ref, telegram_id, nombre)
        if valido:
            await update.message.reply_text(f"🎉 ¡Bienvenido/a *{nombre}*! Fuiste referido y ganaste *1 crédito gratis*.", parse_mode="Markdown")
        registrar_nuevo_referido(telegram_id, nombre)
    elif datos_ref is None and not cliente:
        registrar_nuevo_referido(telegram_id, nombre)

    await update.message.reply_text(
        f"👋 ¡Hola *{nombre}*! Bienvenido al soporte oficial de *Nexus Streaming* 📺\n\n"
        "¿En qué te puedo ayudar hoy?",
        parse_mode="Markdown", reply_markup=kb_menu(),
    )
    return MENU_PRINCIPAL

async def opcion_referidos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_id = update.effective_user.id
    nombre      = update.effective_user.first_name or "Usuario"
    datos       = obtener_datos_referido(telegram_id)

    if not datos:
        datos = registrar_nuevo_referido(telegram_id, nombre)

    codigo    = datos["codigo"]
    creditos  = datos["creditos"]
    referidos = datos["referidos_hechos"]
    proximos  = 5 - (referidos % 5)
    bot_username = context.bot.username

    await update.message.reply_text(
        f"👥 *Tu panel de referidos:*\n\n"
        f"🔑 *Tu código:* `{codigo}`\n"
        f"💎 *Créditos disponibles:* {creditos}\n"
        f"👤 *Referidos hechos:* {referidos}\n"
        f"🎯 *Faltan:* {proximos} para ganar 1 crédito\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "📤 *Comparte este link con tus amigos:*\n"
        f"`https://t.me/{bot_username}?start={codigo}`\n\n"
        "📌 *¿Cómo funciona?*\n"
        "• Cada amigo que entre con tu link = 1 referido\n"
        "• 5 referidos = 1 cookie gratis 🍪\n"
        "• Cada crédito = 1 cookie + token\n\n"
        "💳 Usa /canjear para usar tus créditos",
        parse_mode="Markdown",
        reply_markup=kb_menu(),
    )
    return MENU_PRINCIPAL

async def cmd_canjear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_id = update.effective_user.id
    nombre      = update.effective_user.first_name or "Usuario"
    datos       = obtener_datos_referido(telegram_id)

    if not datos or datos["creditos"] < 1:
        await update.message.reply_text("❌ No tienes créditos disponibles.\nRefiere 5 amigos para ganar 1 crédito.", reply_markup=kb_menu())
        return MENU_PRINCIPAL

    await update.message.reply_text("⏳ Canjeando tu crédito, buscando cookie disponible...", parse_mode="Markdown")

    cliente_sim = {"cookie": "", "precio": 0.0, "celular": str(telegram_id), "nombre": nombre}
    cookie_activa, estado, row_idx_cookie, token_url, pais = resolver_cookie_valida(cliente_sim, context.application)

    if not cookie_activa:
        await update.message.reply_text("⚠️ No hay cookies disponibles ahora. Inténtalo más tarde.", reply_markup=kb_menu())
        return MENU_PRINCIPAL

    usar_credito(telegram_id)
    if row_idx_cookie:
        marcar_cookie_entregada(row_idx_cookie)

    registrar_historial(str(telegram_id), nombre, cookie_activa, token_url or "")
    token_msg         = formatear_token_msg(token_url, pais)
    cookie_formateada = formatear_cookie_msg(cookie_activa)

    await update.message.reply_text(
        f"🎉 *¡Crédito canjeado exitosamente!*\n\n"
        f"🍪 *Tu cookie:*\n`{cookie_formateada}`\n{token_msg}\n\n"
        f"💎 *Créditos restantes:* {datos['creditos'] - 1}\n\n"
        "━━━━━━━━━━━━━━━━━━━\n📺 *¿Deseas activar Netflix en tu televisor?*",
        parse_mode="Markdown", reply_markup=kb_si_no_tv(),
    )
    context.application.bot_data[f"tv_cookie_{telegram_id}"] = cookie_activa
    return MENU_PRINCIPAL

async def volver_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("🏠 Menú principal:", reply_markup=kb_menu())
    return MENU_PRINCIPAL

async def opcion_inconvenientes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["opcion"] = OPC_INCONVENIENTES
    telegram_id = update.effective_user.id
    cliente = buscar_cliente_por_telegram_id(telegram_id)
    if cliente:
        context.user_data["cliente"] = cliente
        return await _procesar_inconvenientes(update, context, cliente)
    await update.message.reply_text(
        "🔧 Para verificar tu cuenta necesito identificarte.\n\n"
        "📱 Dime el *número de celular con el que hiciste el pago*:",
        parse_mode="Markdown", reply_markup=ReplyKeyboardRemove(),
    )
    return ESPERANDO_CELULAR

async def opcion_dias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["opcion"] = OPC_DIAS
    telegram_id = update.effective_user.id
    cliente = buscar_cliente_por_telegram_id(telegram_id)
    if cliente:
        context.user_data["cliente"] = cliente
        return await _procesar_dias(update, context, cliente)
    await update.message.reply_text(
        "📅 Dame tu número para buscar tu cuenta.\n\n"
        "📱 Dime el *número de celular con el que hiciste el pago*:",
        parse_mode="Markdown", reply_markup=ReplyKeyboardRemove(),
    )
    return ESPERANDO_CELULAR

async def opcion_promociones(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lista = "\n".join(PROMOCIONES)
    await update.message.reply_text(f"🎁 *Promociones:*\n\n{lista}", parse_mode="Markdown", reply_markup=kb_menu())
    return MENU_PRINCIPAL

async def opcion_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_id = update.effective_user.id
    cliente = buscar_cliente_por_telegram_id(telegram_id)

    if not cliente:
        await update.message.reply_text(
            "❌ *Usuario no encontrado.*\n\n"
            "Al parecer no cuentas con un plan activo o tu cuenta no está vinculada.\n"
            "¡Adquiere el servicio de *Nexus Streaming* para tener acceso a nuestro soporte técnico premium y muchos más beneficios! 💳🍿",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([[BTN_COMPRAR], [BTN_MENU]], resize_keyboard=True, one_time_keyboard=True)
        )
        return MENU_PRINCIPAL

    # 🔒 FIX: Bloquear tickets si la suscripción ya venció
    dias = cliente.get("dias_restantes")
    if dias is not None and dias < 0:
        await update.message.reply_text(
            f"❌ *Suscripción Vencida*\n\n"
            f"Tu plan expiró hace *{abs(dias)} día(s)*.\n"
            "No puedes solicitar soporte técnico hasta renovar tu servicio.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([[BTN_COMPRAR], [BTN_MENU]], resize_keyboard=True, one_time_keyboard=True)
        )
        return MENU_PRINCIPAL

    context.user_data["cliente"] = cliente
    kb = [["🌍 Problema de región"], ["💳 Problema de pago"], [BTN_MENU]]
    await update.message.reply_text(
        "🎫 *Selecciona el motivo de tu ticket:*",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True)
    )
    return ESPERANDO_MOTIVO_TICKET

async def recibir_motivo_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    motivo = update.message.text
    cliente = context.user_data.get("cliente")
    await update.message.reply_text("⏳ Registrando ticket...")
    tid = registrar_ticket_sheets(cliente, motivo)
    if tid:
        await update.message.reply_text(f"✅ *Ticket {tid} creado.*\nTe notificaremos pronto.", parse_mode="Markdown", reply_markup=kb_menu())
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"🎫 *NUEVO TICKET*\nID: {tid}\nCliente: {cliente['nombre']}\nMotivo: {motivo}")
    return MENU_PRINCIPAL

async def recibir_celular(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    celular     = update.message.text.strip()
    opcion      = context.user_data.get("opcion", OPC_INCONVENIENTES)
    telegram_id = update.effective_user.id

    await update.message.reply_text("🔍 Verificando tu número...")
    cliente = leer_cliente(celular)

    if not cliente:
        await update.message.reply_text(
            "❌ *Usuario no encontrado.*\n\n"
            "Si te equivocaste al escribir, inténtalo de nuevo 👇.\n\n"
            "⚠️ *¿Aún no tienes un plan?*\n"
            "¡Adquiere el servicio de *Nexus Streaming* para tener acceso a tus pantallas automáticas, soporte técnico y más funciones geniales! 💳🍿",
            parse_mode="Markdown",
            reply_markup=kb_con_menu([])
        )
        return ESPERANDO_CELULAR

    if cliente["telegram_id_guardado"] is None:
        guardar_telegram_id(cliente["row_idx"], telegram_id)
    elif cliente["telegram_id_guardado"] != telegram_id:
        await update.message.reply_text("🔒 *Acceso denegado.* Número vinculado a otra cuenta.", parse_mode="Markdown", reply_markup=kb_menu())
        return MENU_PRINCIPAL

    context.user_data["cliente"] = cliente

    if opcion == OPC_DIAS:
        return await _procesar_dias(update, context, cliente)
    else:
        return await _procesar_inconvenientes(update, context, cliente)

async def _procesar_dias(update: Update, context: ContextTypes.DEFAULT_TYPE, cliente: dict) -> int:
    nombre = cliente["nombre"] or "cliente"
    dias   = cliente["dias_restantes"]
    if dias is None:   msg = "📅 No pude calcular tu fecha. Contáctanos directamente."
    elif dias < 0:     msg = f"⚠️ Tu suscripción *venció hace {abs(dias)} días*. ¡Renueva!"
    elif dias == 0:    msg = "⚠️ Tu suscripción *vence hoy*. ¡Renueva ya!"
    elif dias <= 3:    msg = f"⏰ Te quedan solo *{dias} día(s)*. ¡Renueva pronto!"
    else:              msg = f"📅 Te quedan *{dias} días* activos. ¡Disfruta Nexus Streaming! 🍿"
    await update.message.reply_text(f"✅ ¡Hola, *{nombre}*!\n\n{msg}", parse_mode="Markdown", reply_markup=kb_menu())
    return MENU_PRINCIPAL

async def _procesar_inconvenientes(update: Update, context: ContextTypes.DEFAULT_TYPE, cliente: dict) -> int:
    nombre = cliente["nombre"] or "cliente"
    dias   = cliente.get("dias_restantes")

    if dias is not None and dias < 0:
        await update.message.reply_text(
            f"⚠️ *Hola {nombre}*, tu suscripción *venció hace {abs(dias)} día(s)*.\n\n"
            "❌ El soporte técnico solo está disponible para clientes activos.\n\n"
            "💳 Renueva tu plan para seguir disfrutando el servicio:",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([[BTN_COMPRAR], [BTN_MENU]], resize_keyboard=True, one_time_keyboard=True)
        )
        return MENU_PRINCIPAL

    await update.message.reply_text(f"⏳ Verificando estado de tu sesión, *{nombre}*...", parse_mode="Markdown")

    cookie_activa, estado, row_idx_cookie, token_url, pais = resolver_cookie_valida(cliente, context.application)
    if not cookie_activa:
        await update.message.reply_text("⚠️ No hay sesiones disponibles ahora. Inténtalo más tarde.", reply_markup=kb_menu())
        return MENU_PRINCIPAL

    context.user_data["cookie_activa"] = cookie_activa

    # Si es fallback random (plan español sin stock español), avisar antes de analizar perfiles
    if estado == "nueva_random_fallback":
        await update.message.reply_text("🔍 Analizando los perfiles de tu cuenta asignada...", parse_mode="Markdown")

    if estado == "propia_ok":
        # Sesión activa — entregar cookie activa + token fresco + opción TV con advertencia
        registrar_historial(cliente["celular"], nombre, cookie_activa, token_url or "")
        token_msg         = formatear_token_msg(token_url, pais)
        cookie_formateada = formatear_cookie_msg(cookie_activa)
        await update.message.reply_text(
            f"✅ ¡Hola, *{nombre}*! Tu sesión sigue funcionando con normalidad.\n\n"
            f"🍪 *Tu cookie activa:*\n`{cookie_formateada}`\n{token_msg}\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ *NOTA DE SEGURIDAD:* Si necesitas vincular un televisor nuevamente, puedes usar el botón "
            "de abajo. Ten en cuenta que cada acceso queda registrado en nuestro sistema. "
            "El uso indebido o exceso de vinculaciones podría afectar la garantía de tu servicio.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(
                [[BTN_ACTIVAR_TV_NUEVO], [BTN_MENU]],
                resize_keyboard=True, one_time_keyboard=True,
            ),
        )
        return PREGUNTA_ACTIVAR_TV
    else:
        # Sesión caída — entregar nueva cookie completa y preguntar por TV
        if row_idx_cookie:
            marcar_cookie_entregada(row_idx_cookie)
            guardar_cookie_en_cliente(cliente["row_idx"], cookie_activa)
        registrar_historial(cliente["celular"], nombre, cookie_activa, token_url or "")
        token_msg         = formatear_token_msg(token_url, pais)
        cookie_formateada = formatear_cookie_msg(cookie_activa)

        # ── Mensaje especial si era plan español pero solo había random disponible ──
        if estado == "nueva_random_fallback":
            # Detectar perfiles en español de esta cuenta random
            perfiles_info = detectar_perfiles_espanol(cookie_activa)
            perfiles_es   = perfiles_info.get("perfiles_espanol", [])
            todos         = perfiles_info.get("todos_perfiles", [])

            if perfiles_es:
                # ¡Hay perfiles en español! Decirle exactamente cuáles
                lista_es = "\n".join(f"  ✅ *{p}*" for p in perfiles_es)
                if len(perfiles_es) == 1:
                    aviso_espanol = (
                        f"\n\n🎉 *¡Buenas noticias!* Esta cuenta tiene un perfil en español:\n\n"
                        f"{lista_es}\n\n"
                        f"👉 Cuando entres, selecciona ese perfil y listo — tendrás la interfaz en español normalmente."
                    )
                else:
                    aviso_espanol = (
                        f"\n\n🎉 *¡Buenas noticias!* Esta cuenta tiene *{len(perfiles_es)} perfiles en español*:\n\n"
                        f"{lista_es}\n\n"
                        f"👉 Cuando entres, elige cualquiera de esos perfiles."
                    )
            elif todos:
                # Hay perfiles pero ninguno tiene preferredLocale en español
                # El cliente puede cambiarlo manualmente desde configuración del perfil
                lista_todos = ", ".join(f"`{p}`" for p in todos)
                aviso_espanol = (
                    f"\n\n⚠️ *NOTA:* Tu plan incluye cuenta en español, pero el stock español está temporalmente agotado. "
                    f"Te asignamos una cuenta *random* de forma temporal.\n\n"
                    f"Los perfiles disponibles son: {lista_todos}.\n\n"
                    "💡 *¿Quieres usarla en español ahora mismo?* Puedes cambiarlo fácilmente:\n"
                    "1️⃣ Entra a cualquier perfil\n"
                    "2️⃣ Ve a *Cuenta → Perfiles → tu perfil*\n"
                    "3️⃣ Cambia el idioma a *Español*\n\n"
                    "En cuanto tengamos stock español disponible, te reasignaremos automáticamente. 😊"
                )
            else:
                # No se pudo consultar perfiles (error de red, etc.)
                aviso_espanol = (
                    "\n\n⚠️ *NOTA:* Tu plan incluye cuenta en español, pero en este momento "
                    "no hay cookies españolas disponibles en stock.\n\n"
                    "Te asignamos una cuenta *random* temporal. "
                    "👉 Cuando entres, revisa los perfiles: si alguno está en 🇪🇸 español, quédate ahí. "
                    "Si no, en cuanto llegue stock español te reasignaremos. 😊"
                )
        else:
            aviso_espanol = ""

        await update.message.reply_text(
            f"✨ Te asigné una nueva sesión fresca.\n\n"
            f"🍪 *Tu nueva cookie:*\n`{cookie_formateada}`\n{token_msg}"
            f"{aviso_espanol}\n\n"
            "━━━━━━━━━━━━━━━━━━━\n📺 *¿Deseas activar Netflix en tu televisor?*",
            parse_mode="Markdown",
            reply_markup=kb_si_no_tv(),
        )
        return PREGUNTA_ACTIVAR_TV

# ══════════════════════════════════════════════
#  NUEVO FLUJO: ACTIVACIÓN TV AUTOMÁTICA
# ══════════════════════════════════════════════
async def respuesta_si_tv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "📺 ¡Perfecto! Ve a tu televisor, abre Netflix y busca la opción de **iniciar sesión desde la web**.\n\n"
        "Debería aparecer un **código de 8 caracteres** en la pantalla.\n\n"
        "👉 *Escribe ese código aquí abajo:*",
        parse_mode="Markdown",
        reply_markup=kb_con_menu([]) 
    )
    return ESPERANDO_CODIGO_TV

async def recibir_codigo_tv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    codigo_tv = update.message.text.strip().replace(" ", "")
    
    if len(codigo_tv) != 8:
        await update.message.reply_text("❌ El código debe tener exactamente 8 caracteres. Intenta de nuevo:", reply_markup=kb_con_menu([]))
        return ESPERANDO_CODIGO_TV
        
    cookie_activa = context.user_data.get("cookie_activa")
    if not cookie_activa:
        await update.message.reply_text("❌ Tu sesión expiró. Vuelve a pedir tu cuenta desde el menú principal.", reply_markup=kb_menu())
        return MENU_PRINCIPAL

    msg = await update.message.reply_text("⏳ Procesando... Conectando con tu televisor...")
    resultado = activar_tv_con_codigo(cookie_activa, codigo_tv)
    
    if resultado['success']:
        await msg.edit_text(f"🎉 **¡Éxito!**\n\n{resultado['message']}\nYa deberías ver tu perfil de Netflix en la TV.", parse_mode="Markdown")
        await update.message.reply_text("¿Necesitas ayuda con algo más?", reply_markup=kb_menu())
        return MENU_PRINCIPAL
    else:
        await msg.edit_text(f"⚠️ **Error:**\n{resultado['message']}", parse_mode="Markdown")
        await update.message.reply_text("Verifica el código en tu TV y envíalo de nuevo, o presiona Menú para salir.", reply_markup=kb_con_menu([]))
        return ESPERANDO_CODIGO_TV

async def respuesta_no_tv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("😄 ¡Genial! Que disfrutes del servicio. 🍿", reply_markup=kb_menu())
    context.user_data.clear()
    return MENU_PRINCIPAL

# ══════════════════════════════════════════════
#  VENTAS
# ══════════════════════════════════════════════
async def opcion_comprar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "🌍 *¿Desde dónde realizarás el pago?*",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            [[BTN_PAGO_PERU], [BTN_PAGO_EXTRANJERO], [BTN_MENU]],
            resize_keyboard=True, one_time_keyboard=True
        ),
    )
    return VENTA_ELEGIR_ORIGEN

async def venta_recibir_origen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto = update.message.text.strip()
    if texto == BTN_PAGO_PERU:
        context.user_data["venta_origen"] = "Peru"
        # Flujo normal — directo a elegir dispositivo
        await update.message.reply_text(
            "📱 *¿Para qué dispositivo?*",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(
                [[BTN_TIPO_TV], [BTN_TIPO_CEL], [BTN_TIPO_RAPIDO]],
                resize_keyboard=True, one_time_keyboard=True
            ),
        )
        return VENTA_ELEGIR_DISPOSITIVO
    elif texto == BTN_PAGO_EXTRANJERO:
        context.user_data["venta_origen"] = "Extranjero"
        # Preguntar método de pago internacional
        await update.message.reply_text(
            "💳 *¿Qué método de pago prefieres usar?*",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(
                [[BTN_PAGO_BINANCE], [BTN_PAGO_LEMON], [BTN_CANCELAR_VENTA]],
                resize_keyboard=True, one_time_keyboard=True
            ),
        )
        return VENTA_ELEGIR_METODO_INT
    else:
        # Respuesta inesperada — volver a preguntar
        await update.message.reply_text(
            "Por favor elige una opción válida 👇",
            reply_markup=ReplyKeyboardMarkup(
                [[BTN_PAGO_PERU], [BTN_PAGO_EXTRANJERO], [BTN_MENU]],
                resize_keyboard=True, one_time_keyboard=True
            ),
        )
        return VENTA_ELEGIR_ORIGEN

async def venta_recibir_metodo_int(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto = update.message.text.strip()
    if texto == BTN_PAGO_BINANCE:
        context.user_data["venta_metodo_int"] = "Binance"
    elif texto == BTN_PAGO_LEMON:
        context.user_data["venta_metodo_int"] = "Lemon"
    else:
        # Respuesta inesperada — volver a preguntar
        await update.message.reply_text(
            "Por favor elige una opción válida 👇",
            reply_markup=ReplyKeyboardMarkup(
                [[BTN_PAGO_BINANCE], [BTN_PAGO_LEMON], [BTN_CANCELAR_VENTA]],
                resize_keyboard=True, one_time_keyboard=True
            ),
        )
        return VENTA_ELEGIR_METODO_INT

    await update.message.reply_text(
        "📱 *¿Para qué dispositivo?*",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            [[BTN_TIPO_TV], [BTN_TIPO_CEL], [BTN_TIPO_RAPIDO]],
            resize_keyboard=True, one_time_keyboard=True
        ),
    )
    return VENTA_ELEGIR_DISPOSITIVO

async def opcion_planes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "💎 *Planes disponibles:*\n\n"
        "📺 *TV / PC / Laptop:*\n  • S/8/mes → Compartida random\n  • S/10/mes → Compartida español\n\n"
        "📱 *Celular Xiaomi / Redmi:*\n  • S/8/mes → Compartida random\n  • S/10/mes → Compartida español\n\n"
        "🌟 *Perfil personal:\n  • S/15/mes → Perfil solo tuyo\n\n"
        "⚡ *Acceso rápido:*\n  • S/2.5 → Sin garantía\n",
        parse_mode="Markdown", reply_markup=kb_menu(),
    )
    return MENU_PRINCIPAL

async def venta_elegir_canal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text.strip() == BTN_COMPRAR_WHATSAPP:
        await update.message.reply_text(f"📱 Compra por WhatsApp:\n{WHATSAPP_LINK}", reply_markup=kb_menu())
        return MENU_PRINCIPAL
    await update.message.reply_text(
        "📱 *¿Para qué dispositivo?*", parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([[BTN_TIPO_TV], [BTN_TIPO_CEL], [BTN_TIPO_RAPIDO]], resize_keyboard=True, one_time_keyboard=True),
    )
    return VENTA_ELEGIR_DISPOSITIVO

async def venta_elegir_dispositivo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto = update.message.text.strip()
    if texto == BTN_TIPO_RAPIDO:
        context.user_data.update({"venta_plan": "Acceso rápido S/2.5", "venta_precio": 2.5, "venta_tipo": "random", "venta_dispositivo": "RAPIDO"})
        await update.message.reply_text(
            "⚡ *Acceso rápido S/2.5*\n\n⚠️ *IMPORTANTE:*\n• SIN garantía\n• SIN soporte técnico\n\n¿Continuar?",
            parse_mode="Markdown", reply_markup=ReplyKeyboardMarkup([[BTN_CONFIRMAR], [BTN_CANCELAR_VENTA]], resize_keyboard=True, one_time_keyboard=True),
        )
        return VENTA_CONFIRMAR_RAPIDO
    planes = PLANES_TV if texto == BTN_TIPO_TV else PLANES_CEL
    context.user_data["venta_planes"] = planes
    kb = [[p] for p in planes.keys()] + [[BTN_CANCELAR_VENTA]]
    await update.message.reply_text("💎 *Elige tu plan:*", parse_mode="Markdown", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True))
    return VENTA_ELEGIR_PLAN

async def venta_confirmar_rapido(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("👤 Dime tu *nombre completo*:", parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    return VENTA_PEDIR_NOMBRE

async def venta_elegir_plan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto  = update.message.text.strip()
    planes = context.user_data.get("venta_planes", {})
    if texto not in planes:
        await update.message.reply_text("Por favor elige una opción válida.")
        return VENTA_ELEGIR_PLAN
    info = planes[texto]
    context.user_data.update({"venta_plan": texto, "venta_precio": info["precio"], "venta_tipo": info["tipo"], "venta_dispositivo": info["dispositivo"]})
    await update.message.reply_text("👤 Dime tu *nombre completo*:", parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    return VENTA_PEDIR_NOMBRE

async def venta_pedir_nombre(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["venta_nombre"] = update.message.text.strip()
    await update.message.reply_text("📱 Ahora dime tu *número de celular*:", parse_mode="Markdown")
    return VENTA_PEDIR_CELULAR

async def venta_pedir_celular(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["venta_celular"] = normalizar_celular(update.message.text.strip())
    precio     = context.user_data.get("venta_precio", 0)
    plan       = context.user_data.get("venta_plan", "")
    origen     = context.user_data.get("venta_origen", "Peru")
    metodo_int = context.user_data.get("venta_metodo_int", "Binance")

    kb_cancelar = ReplyKeyboardMarkup([[BTN_CANCELAR_VENTA]], resize_keyboard=True)

    if origen == "Extranjero":
        monto_usd = round((precio / TASA_DOLAR) + COMISION_INT, 2)

        if metodo_int == "Binance":
            texto = (
                f"💳 *Pago Internacional — Binance Pay*\n\n"
                f"📋 Plan: {plan}\n"
                f"💰 Monto exacto a enviar: *{monto_usd} USDT/USD*\n"
                f"_(Incluye comisión y tasa de cambio S/ {TASA_DOLAR})_\n\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                "🟡 *Datos de Binance Pay:*\n"
                "   • ID de Binance: `1045838138`\n\n"
                "📸 Realiza el pago y envía la *foto del comprobante* aquí:"
            )
            try:
                with open(QR_BINANCE_PATH, "rb") as qr_file:
                    await update.message.reply_photo(photo=qr_file, caption=texto, parse_mode="Markdown", reply_markup=kb_cancelar)
            except FileNotFoundError:
                await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=kb_cancelar)

        else:  # Lemon
            texto = (
                f"💳 *Pago Internacional — Lemon Cash*\n\n"
                f"📋 Plan: {plan}\n"
                f"💰 Monto exacto a enviar: *{monto_usd} USDT/USD*\n"
                f"_(Incluye comisión y tasa de cambio S/ {TASA_DOLAR})_\n\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                "🍋 *Datos de Lemon Cash:*\n"
                "   • $LemonTag: `nexustreaming`\n\n"
                "📸 Realiza el pago y envía la *foto del comprobante* aquí:"
            )
            try:
                with open(QR_LEMON_PATH, "rb") as qr_file:
                    await update.message.reply_photo(photo=qr_file, caption=texto, parse_mode="Markdown", reply_markup=kb_cancelar)
            except FileNotFoundError:
                await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=kb_cancelar)

    else:
        # Perú — Yape
        texto = (
            f"💳 *Datos de pago:*\n\n"
            f"📲 Yape a nombre de: *{YAPE_NOMBRE}*\n"
            f"💰 Monto: *S/{precio}*\n"
            f"📋 Plan: {plan}\n\n"
            "📸 Envía la *foto del comprobante* aquí:"
        )
        try:
            with open(QR_IMAGE_PATH, "rb") as qr_file:
                await update.message.reply_photo(photo=qr_file, caption=texto, parse_mode="Markdown", reply_markup=kb_cancelar)
        except FileNotFoundError:
            await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=kb_cancelar)

    return VENTA_PEDIR_COMPROBANTE

async def fallo_comprobante(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("📸 Por favor envía la *foto* del comprobante (no texto).", parse_mode="Markdown")
    return VENTA_PEDIR_COMPROBANTE

async def venta_recibir_comprobante(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    nombre     = context.user_data.get("venta_nombre", "")
    celular    = context.user_data.get("venta_celular", "")
    plan       = context.user_data.get("venta_plan", "")
    precio     = context.user_data.get("venta_precio", "")
    tipo       = context.user_data.get("venta_tipo", "random")
    dispositivo = context.user_data.get("venta_dispositivo", "")
    foto_id    = update.message.photo[-1].file_id
    chat_id    = update.effective_user.id

    pendientes_venta[str(chat_id)] = {
        "nombre": nombre, "celular": celular, "plan": plan,
        "precio": precio, "tipo": tipo, "dispositivo": dispositivo,
        "foto_id": foto_id, "chat_id": chat_id,
    }
    registrar_venta_sheets(pendientes_venta[str(chat_id)])

    await update.message.reply_text(
        "✅ *Comprobante recibido*\n⏳ Tu pago está en revisión (5–10 min).",
        parse_mode="Markdown", reply_markup=kb_menu(),
    )
    await context.bot.send_photo(
        chat_id=ADMIN_ID, photo=foto_id,
        caption=f"🛒 *NUEVO PAGO*\n👤 {nombre}\n📱 {celular}\n📋 {plan}\n💰 S/{precio}\n\n`/aprobar {chat_id}`\n`/rechazar {chat_id}`",
        parse_mode="Markdown",
    )
    return MENU_PRINCIPAL

# ══════════════════════════════════════════════
#  HANDLERS — MAYORISTAS
# ══════════════════════════════════════════════
async def opcion_mayorista(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_id = update.effective_user.id
    nombre      = update.effective_user.first_name or "Proveedor"
    datos       = obtener_mayorista(telegram_id)

    if datos:
        # Ya es mayorista — mostrar panel directo
        creditos = datos["creditos"]
        total    = datos["total_comprados"]
        await update.message.reply_text(
            f"🏪 *Panel de Proveedor Mayorista*\n\n"
            f"👤 *{datos['nombre']}*\n"
            f"💎 *Créditos disponibles:* {creditos}\n"
            f"📦 *Total comprados:* {total}\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "Cada crédito = 1 cuenta Netflix completa\n"
            "• 🍪 Cookie de acceso\n"
            "• 🔗 Token de ingreso rápido\n"
            "• 📺 Activación en TV incluida\n"
            "• 🛡️ Garantía y soporte 30 días",
            parse_mode="Markdown",
            reply_markup=kb_mayorista(),
        )
        return MENU_PRINCIPAL
    else:
        # No es mayorista — preguntar origen antes de mostrar packs
        await update.message.reply_text(
            "🏪 *¡Bienvenido al Programa de Proveedores Mayoristas!*\n\n"
            "Compra créditos por adelantado y entrega cuentas Netflix a tus clientes cuando los necesites.\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "💎 *Cada crédito incluye:*\n"
            "• 🍪 Cookie de acceso\n"
            "• 🔗 Token de ingreso rápido\n"
            "• 📺 Opción de activar en TV\n"
            "• 🛡️ Garantía y soporte 30 días\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "🌍 *¿Desde dónde realizarás el pago?*",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(
                [[BTN_PAGO_PERU], [BTN_PAGO_EXTRANJERO], [BTN_MENU]],
                resize_keyboard=True, one_time_keyboard=True
            ),
        )
        return MAYOR_ELEGIR_ORIGEN

async def mayor_recibir_origen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto = update.message.text.strip()
    kb_packs = ReplyKeyboardMarkup(
        [[BTN_MAYOR_6], [BTN_MAYOR_10], [BTN_MAYOR_20], [BTN_CANCELAR_VENTA]],
        resize_keyboard=True, one_time_keyboard=True
    )
    if texto == BTN_PAGO_PERU:
        context.user_data["mayor_origen"] = "Peru"
        await update.message.reply_text(
            "📦 *Elige tu pack:*",
            parse_mode="Markdown",
            reply_markup=kb_packs,
        )
        return MAYOR_ELEGIR_CANTIDAD
    elif texto == BTN_PAGO_EXTRANJERO:
        context.user_data["mayor_origen"] = "Extranjero"
        await update.message.reply_text(
            "📦 *Elige tu pack:*",
            parse_mode="Markdown",
            reply_markup=kb_packs,
        )
        return MAYOR_ELEGIR_CANTIDAD
    else:
        await update.message.reply_text(
            "Por favor elige una opción válida 👇",
            reply_markup=ReplyKeyboardMarkup(
                [[BTN_PAGO_PERU], [BTN_PAGO_EXTRANJERO], [BTN_MENU]],
                resize_keyboard=True, one_time_keyboard=True
            ),
        )
        return MAYOR_ELEGIR_ORIGEN

async def mayor_recibir_metodo_int(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto = update.message.text.strip()
    if texto == BTN_PAGO_BINANCE:
        context.user_data["mayor_metodo_int"] = "Binance"
    elif texto == BTN_PAGO_LEMON:
        context.user_data["mayor_metodo_int"] = "Lemon"
    else:
        await update.message.reply_text(
            "Por favor elige una opción válida 👇",
            reply_markup=ReplyKeyboardMarkup(
                [[BTN_PAGO_BINANCE], [BTN_PAGO_LEMON], [BTN_CANCELAR_VENTA]],
                resize_keyboard=True, one_time_keyboard=True
            ),
        )
        return MAYOR_ELEGIR_METODO_INT

    # Mostrar resumen y QR con monto en USDT
    pack       = context.user_data.get("mayor_pack", {})
    metodo     = context.user_data["mayor_metodo_int"]
    total_soles = pack.get("total", 0)
    monto_usd  = round((total_soles / TASA_DOLAR) + COMISION_INT, 2)

    kb_cancelar = ReplyKeyboardMarkup([[BTN_CANCELAR_VENTA]], resize_keyboard=True)

    if metodo == "Binance":
        texto_pago = (
            f"💳 *Resumen — Binance Pay*\n\n"
            f"📦 {pack['cantidad']} créditos\n"
            f"💰 Total a depositar: *{monto_usd} USDT*\n"
            f"_(Incluye S/{total_soles} equivalente + comisión S/{COMISION_INT} USD)_\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "🟡 *Datos de Binance Pay:*\n"
            "   • ID de Binance: `1045838138`\n\n"
            "📸 Envía la *foto del comprobante* para procesar:"
        )
        qr_path = QR_BINANCE_PATH
    else:
        texto_pago = (
            f"💳 *Resumen — Lemon Cash*\n\n"
            f"📦 {pack['cantidad']} créditos\n"
            f"💰 Total a depositar: *{monto_usd} USDT*\n"
            f"_(Incluye S/{total_soles} equivalente + comisión S/{COMISION_INT} USD)_\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "🍋 *Datos de Lemon Cash:*\n"
            "   • $LemonTag: `nexustreaming`\n\n"
            "📸 Envía la *foto del comprobante* para procesar:"
        )
        qr_path = QR_LEMON_PATH

    try:
        with open(qr_path, "rb") as qr_file:
            await update.message.reply_photo(photo=qr_file, caption=texto_pago, parse_mode="Markdown", reply_markup=kb_cancelar)
    except FileNotFoundError:
        await update.message.reply_text(texto_pago, parse_mode="Markdown", reply_markup=kb_cancelar)

    return MAYOR_PEDIR_COMPROBANTE

async def mayor_elegir_cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto = update.message.text.strip()
    packs = {
        BTN_MAYOR_6:  {"cantidad": 6,  "precio_unit": 4.0,  "total": 24.0},
        BTN_MAYOR_10: {"cantidad": 10, "precio_unit": 3.7,  "total": 37.0},
        BTN_MAYOR_20: {"cantidad": 20, "precio_unit": 3.5,  "total": 70.0},
    }
    if texto not in packs:
        await update.message.reply_text(
            "Por favor elige un pack válido 👇",
            reply_markup=ReplyKeyboardMarkup(
                [[BTN_MAYOR_6], [BTN_MAYOR_10], [BTN_MAYOR_20], [BTN_CANCELAR_VENTA]],
                resize_keyboard=True, one_time_keyboard=True
            ),
        )
        return MAYOR_ELEGIR_CANTIDAD

    pack = packs[texto]
    context.user_data["mayor_pack"]       = pack
    context.user_data["mayor_pack_label"] = texto
    origen = context.user_data.get("mayor_origen", "Peru")

    if origen == "Extranjero":
        # Preguntar método de pago internacional
        await update.message.reply_text(
            f"📦 *Pack seleccionado:* {pack['cantidad']} créditos — S/{pack['total']}\n\n"
            "💳 *¿Qué método de pago prefieres usar?*",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(
                [[BTN_PAGO_BINANCE], [BTN_PAGO_LEMON], [BTN_CANCELAR_VENTA]],
                resize_keyboard=True, one_time_keyboard=True
            ),
        )
        return MAYOR_ELEGIR_METODO_INT
    else:
        # Perú — mostrar QR Yape directo
        total_soles = pack["total"]
        kb_cancelar = ReplyKeyboardMarkup([[BTN_CANCELAR_VENTA]], resize_keyboard=True)
        texto_pago = (
            f"💳 *Resumen de tu pedido:*\n\n"
            f"📦 {pack['cantidad']} créditos\n"
            f"💰 S/{pack['precio_unit']} c/u × {pack['cantidad']} = *S/{total_soles}*\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"📲 Yape a nombre de: *{YAPE_NOMBRE}*\n"
            f"💰 Monto exacto: *S/{total_soles}*\n\n"
            "📸 Envía la *foto del comprobante* para procesar:"
        )
        try:
            with open(QR_IMAGE_PATH, "rb") as qr_file:
                await update.message.reply_photo(photo=qr_file, caption=texto_pago, parse_mode="Markdown", reply_markup=kb_cancelar)
        except FileNotFoundError:
            await update.message.reply_text(texto_pago, parse_mode="Markdown", reply_markup=kb_cancelar)
        return MAYOR_PEDIR_COMPROBANTE

async def mayor_recibir_comprobante(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pack        = context.user_data.get("mayor_pack", {})
    origen      = context.user_data.get("mayor_origen", "Peru")
    metodo      = context.user_data.get("mayor_metodo_int", "")
    nombre      = update.effective_user.first_name or "Proveedor"
    telegram_id = update.effective_user.id
    foto_id     = update.message.photo[-1].file_id
    chat_id     = update.effective_user.id

    total_soles = pack.get("total", 0)
    if origen == "Extranjero":
        monto_usd = round((total_soles / TASA_DOLAR) + COMISION_INT, 2)
        monto_label = f"{monto_usd} USDT ({metodo})"
    else:
        monto_label = f"S/{total_soles} (Yape)"

    pendientes_mayorista[str(chat_id)] = {
        "nombre":      nombre,
        "telegram_id": telegram_id,
        "chat_id":     chat_id,
        "cantidad":    pack.get("cantidad", 0),
        "total":       total_soles,
        "precio_unit": pack.get("precio_unit", 4.0),
        "foto_id":     foto_id,
        "origen":      origen,
        "metodo":      metodo,
    }

    registrar_venta_mayorista_sheets(pendientes_mayorista[str(chat_id)])

    await update.message.reply_text(
        "✅ *Comprobante recibido*\n⏳ Tu pago está en revisión (5–10 min).\n\nTe notificamos apenas se acrediten tus créditos.",
        parse_mode="Markdown",
        reply_markup=kb_menu(),
    )
    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=foto_id,
        caption=(
            f"🏪 *PAGO MAYORISTA*\n"
            f"👤 {nombre}\n"
            f"🆔 Telegram ID: `{telegram_id}`\n"
            f"📦 {pack.get('cantidad', 0)} créditos\n"
            f"💰 {monto_label}\n\n"
            f"`/aprobar_mayor {chat_id}`\n"
            f"`/rechazar_mayor {chat_id}`"
        ),
        parse_mode="Markdown",
    )
    return MENU_PRINCIPAL

async def mayor_fallo_comprobante(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("📸 Por favor envía la *foto* del comprobante (no texto).", parse_mode="Markdown")
    return MAYOR_PEDIR_COMPROBANTE

async def mayor_panel_desde_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja los botones del panel mayorista cuando ya es proveedor."""
    telegram_id = update.effective_user.id
    texto       = update.message.text.strip()

    datos = obtener_mayorista(telegram_id)

    if texto == BTN_MAYOR_SALDO:
        if not datos:
            await update.message.reply_text("❌ No tienes cuenta mayorista.", reply_markup=kb_menu())
            return MENU_PRINCIPAL
        await update.message.reply_text(
            f"💎 *Tus créditos disponibles:* {datos['creditos']}\n"
            f"📦 *Total comprados:* {datos['total_comprados']}",
            parse_mode="Markdown",
            reply_markup=kb_mayorista(),
        )
        return MENU_PRINCIPAL

    elif texto == BTN_MAYOR_HISTORIAL:
        canjes = obtener_historial_mayorista(telegram_id)
        if not canjes:
            await update.message.reply_text("📋 No tienes canjes registrados aún.", reply_markup=kb_mayorista())
            return MENU_PRINCIPAL
        msg = "📋 *Tus últimos canjes:*\n\n"
        for c in canjes:
            msg += f"👤 `{c['etiqueta']}` — Vence: {c['vence']} — {c['estado']}\n"
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb_mayorista())
        return MENU_PRINCIPAL

    elif texto == BTN_MAYOR_COMPRAR_MAS:
        await update.message.reply_text(
            "🌍 *¿Desde dónde realizarás el pago?*",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(
                [[BTN_PAGO_PERU], [BTN_PAGO_EXTRANJERO], [BTN_MENU]],
                resize_keyboard=True, one_time_keyboard=True
            ),
        )
        return MAYOR_ELEGIR_ORIGEN

    elif texto == BTN_MAYOR_CANJEAR:
        if not datos or datos["creditos"] < 1:
            await update.message.reply_text(
                "❌ No tienes créditos disponibles.\n\nCompra un pack para continuar:",
                reply_markup=ReplyKeyboardMarkup([[BTN_MAYOR_COMPRAR_MAS], [BTN_MENU]], resize_keyboard=True, one_time_keyboard=True),
            )
            return MENU_PRINCIPAL
        await update.message.reply_text(
            f"🎟️ *Canjear crédito*\n\n"
            f"💎 Créditos disponibles: *{datos['creditos']}*\n\n"
            "Escribe un *nombre o número* para identificar a este cliente\n"
            "_(Ej: `Juan 921234567` o `Cliente-01`)_",
            parse_mode="Markdown",
            reply_markup=kb_con_menu([]),
        )
        return MAYOR_CANJEAR_ETIQUETA

    return MENU_PRINCIPAL

BTN_MAYOR_REGION_ES  = "🇪🇸 Cuenta Español"
BTN_MAYOR_REGION_RDM = "🌍 Cuenta Random"

async def mayor_recibir_etiqueta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    etiqueta    = update.message.text.strip()
    telegram_id = update.effective_user.id

    datos = obtener_mayorista(telegram_id)
    if not datos or datos["creditos"] < 1:
        await update.message.reply_text("❌ Sin créditos. Compra un pack primero.", reply_markup=kb_menu())
        return MENU_PRINCIPAL

    # Guardar etiqueta y generar código de soporte, pero NO buscar cookie todavía
    celular_cliente = normalizar_celular(etiqueta)
    if len(celular_cliente) < 8:
        ts = datetime.now(PERU_TZ).strftime("%d%H%M%S")
        celular_cliente = f"PROV{telegram_id % 10000}-{ts}"

    context.user_data["mayor_etiqueta"]       = etiqueta
    context.user_data["mayor_celular_cliente"] = celular_cliente

    await update.message.reply_text(
        f"👤 *Cliente:* `{etiqueta}`\n\n"
        "🌍 *¿Qué tipo de cuenta deseas entregar?*",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            [[BTN_MAYOR_REGION_ES], [BTN_MAYOR_REGION_RDM], [BTN_MENU]],
            resize_keyboard=True, one_time_keyboard=True,
        ),
    )
    return MAYOR_ELEGIR_REGION

async def mayor_recibir_region(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto           = update.message.text.strip()
    telegram_id     = update.effective_user.id
    nombre_prov     = update.effective_user.first_name or "Proveedor"
    etiqueta        = context.user_data.get("mayor_etiqueta", "Cliente")
    celular_cliente = context.user_data.get("mayor_celular_cliente", str(telegram_id))

    datos = obtener_mayorista(telegram_id)
    if not datos or datos["creditos"] < 1:
        await update.message.reply_text("❌ Sin créditos. Compra un pack primero.", reply_markup=kb_menu())
        return MENU_PRINCIPAL

    if texto == BTN_MAYOR_REGION_ES:
        precio_busqueda = 10.0
        tipo_label      = "Español 🇪🇸"
    elif texto == BTN_MAYOR_REGION_RDM:
        precio_busqueda = 8.0
        tipo_label      = "Random 🌍"
    else:
        await update.message.reply_text("Por favor elige una opción válida.")
        return MAYOR_ELEGIR_REGION

    await update.message.reply_text(f"⏳ Buscando cuenta {tipo_label}...")

    cliente_sim = {"cookie": "", "precio": precio_busqueda, "celular": celular_cliente, "nombre": etiqueta}
    cookie_activa, estado, row_idx_cookie, token_url, pais = resolver_cookie_valida(cliente_sim, context.application)

    if not cookie_activa:
        await update.message.reply_text("⚠️ No hay cuentas disponibles ahora. Intenta más tarde.", reply_markup=kb_mayorista())
        return MENU_PRINCIPAL

    # Descontar crédito y marcar cookie
    usar_credito_mayorista(telegram_id)
    if row_idx_cookie:
        marcar_cookie_entregada(row_idx_cookie)

    registrar_canje_mayorista(telegram_id, nombre_prov, etiqueta, cookie_activa, token_url or "")
    registrar_historial(str(telegram_id), f"MAYORISTA-{etiqueta}", cookie_activa, token_url or "")

    # Registrar en NETFLIX con precio=0.0 (no altera contabilidad) pero CON cookie para evitar doble gasto
    agregar_cliente_nuevo(etiqueta, celular_cliente, 0.0, "MAYORISTA", cookie=cookie_activa)

    token_msg         = formatear_token_msg(token_url, pais)
    cookie_formateada = formatear_cookie_msg(cookie_activa)
    datos_actualizados = obtener_mayorista(telegram_id)
    creditos_rest = datos_actualizados["creditos"] if datos_actualizados else datos["creditos"] - 1

    await update.message.reply_text(
        f"✅ *¡Cuenta entregada!*\n\n"
        f"👤 *Cliente:* `{etiqueta}`\n"
        f"🌍 *Tipo:* {tipo_label}\n"
        f"🔑 *Código de soporte:* `{celular_cliente}`\n\n"
        f"🍪 *Cookie:*\n`{cookie_formateada}`\n"
        f"{token_msg}\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📋 *Mensaje listo para copiar a tu cliente:*\n"
        f"_\"Si tu pantalla falla, entra al bot, presiona "
        f"'🔧 Tengo inconvenientes' e ingresa: `{celular_cliente}`\"_\n\n"
        f"💎 *Créditos restantes:* {creditos_rest}\n\n"
        "📺 ¿Activar esta cuenta en TV?",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            [[BTN_SI_TV], ["❌ No activar TV"], [BTN_MENU]],
            resize_keyboard=True, one_time_keyboard=True,
        ),
    )
    context.application.bot_data[f"tv_cookie_{telegram_id}"] = cookie_activa
    # Limpiar user_data del flujo mayorista
    context.user_data.pop("mayor_etiqueta", None)
    context.user_data.pop("mayor_celular_cliente", None)
    return MENU_PRINCIPAL

# ══════════════════════════════════════════════
#  ADMIN COMANDOS — MAYORISTAS
# ══════════════════════════════════════════════
async def cmd_aprobar_mayor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args: return
    chat_id_str = context.args[0]
    datos = pendientes_mayorista.get(chat_id_str)
    if not datos:
        await update.message.reply_text("❌ Pedido no encontrado o ya procesado.")
        return

    telegram_id = datos["telegram_id"]
    nombre      = datos["nombre"]
    cantidad    = datos["cantidad"]
    total       = datos["total"]

    # Registrar o actualizar mayorista en Sheets
    existente = obtener_mayorista(telegram_id)
    if existente:
        sumar_creditos_mayorista(telegram_id, cantidad)
    else:
        registrar_mayorista_nuevo(telegram_id, nombre)
        sumar_creditos_mayorista(telegram_id, cantidad)

    datos_final = obtener_mayorista(telegram_id)
    creditos_now = datos_final["creditos"] if datos_final else cantidad

    await context.bot.send_message(
        chat_id=datos["chat_id"],
        text=(
            f"✅ *¡Pago confirmado!*\n\n"
            f"🎉 Se acreditaron *{cantidad} créditos* a tu cuenta.\n\n"
            f"💎 *Total créditos disponibles:* {creditos_now}\n\n"
            "Usa el botón *🎟️ Canjear crédito* del menú de proveedor\n"
            "para entregar cuentas a tus clientes cuando los necesites.\n\n"
            "¡Gracias por confiar en Nexus Streaming! 🍿"
        ),
        parse_mode="Markdown",
        reply_markup=kb_mayorista(),
    )
    await update.message.reply_text(
        f"✅ Mayorista aprobado\n👤 {nombre} | +{cantidad} créditos | Total: {creditos_now}",
        parse_mode="Markdown",
    )
    del pendientes_mayorista[chat_id_str]

async def cmd_rechazar_mayor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args: return
    chat_id_str = context.args[0]
    datos = pendientes_mayorista.get(chat_id_str)
    if not datos: return
    await context.bot.send_message(
        chat_id=datos["chat_id"],
        text="❌ *Pago no válido.*\n\nNo se pudo verificar tu comprobante. Si crees que es un error contáctanos.",
        parse_mode="Markdown",
    )
    await update.message.reply_text(f"❌ Pedido mayorista rechazado: {datos['nombre']}")
    del pendientes_mayorista[chat_id_str]

async def cmd_mayoristas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista todos los mayoristas con sus créditos."""
    if update.effective_user.id != ADMIN_ID: return
    try:
        gc   = get_gspread_client()
        ws   = gc.open_by_key(SHEET_ID_CLIENTES).worksheet("MAYORISTAS")
        rows = ws.get_all_values()
        if len(rows) <= 1:
            await update.message.reply_text("📋 No hay proveedores mayoristas registrados.")
            return
        msg = "🏪 *Proveedores Mayoristas:*\n\n"
        for row in rows[1:]:
            while len(row) < 5: row.append("")
            msg += f"👤 {row[2]} | 💎 {row[3]} créditos | 📦 Total: {row[4]}\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def cmd_pendientes_mayor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not pendientes_mayorista:
        await update.message.reply_text("✅ No hay pedidos mayoristas pendientes.")
        return
    msg = "🏪 *Pedidos mayoristas pendientes:*\n\n"
    for cid, d in pendientes_mayorista.items():
        msg += f"👤 {d['nombre']} | 📦 {d['cantidad']} créditos — S/{d['total']}\n`/aprobar_mayor {cid}` | `/rechazar_mayor {cid}`\n━━━\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

# ══════════════════════════════════════════════
#  ADMIN COMANDOS
# ══════════════════════════════════════════════
async def cmd_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    stock = contar_stock()
    if not stock:
        await update.message.reply_text("❌ Error al leer cookies.")
        return
    await update.message.reply_text(
        "📊 *Stock de cookies:*\n\n"
        f"📦 Total:           *{stock['total']}*\n"
        f"✅ Disponibles:     *{stock['disponibles']}*\n"
        f"   ├ 🇪🇸 Español:  *{stock['espanol']}*\n"
        f"   └ 🌍 Otros:     *{stock['aleatorio']}*\n"
        f"⚠️ En Hold/Pausa: *{stock.get('pausadas', 0)}*\n"
        f"📤 Entregadas:      *{stock['entregadas']}*\n"
        f"💀 Muertas:         *{stock['muertas']}*",
        parse_mode="Markdown",
    )

async def _entregar_cookie_admin(update, context=None, tipo: str = "any", codigo_pais: str = None):
    if update.effective_user.id != ADMIN_ID: return
    es_fallback = False
    if codigo_pais:
        await update.message.reply_text(f"🔍 Buscando cookie de *{codigo_pais.upper()}*...", parse_mode="Markdown")
        pool = obtener_pool_por_pais(codigo_pais)
    elif tipo == "es":
        pool, es_fallback = obtener_pool(10.0)
        if es_fallback:
            await update.message.reply_text("⚠️ Sin stock español — usando random + detección de perfiles...", parse_mode="Markdown")
        else:
            await update.message.reply_text("🔍 Buscando cookie en español 🇪🇸...", parse_mode="Markdown")
    else:
        pool, _ = obtener_pool(0.0)
        await update.message.reply_text("🔍 Buscando cookie random 🌍...")

    if not pool:
        await update.message.reply_text("❌ No hay cookies disponibles de ese tipo.")
        return

    cookie_val = None
    token_raw  = None
    row_idx    = None
    pais_final = ""

    for cv, pais, codigo, ridx in pool:
        info    = check_cookie(cv)
        estado  = info.get("estado") if info else "DEAD"
        if estado == "OK":
            pais_final = info.get("country_code", pais) or pais
            token_url  = generate_nftoken(cv)
            if token_url and "nftoken=" in token_url:
                cookie_val = cv
                token_raw  = token_url.split("nftoken=")[1]
                row_idx    = ridx
                break
            else:
                cookie_val = cv
                row_idx    = ridx
                break
        elif estado == "ON_HOLD":
            await update.message.reply_text(f"⚠️ Cookie EN PAUSA (on hold) — saltando:\n`{cv[:60]}...`", parse_mode="Markdown")
            continue
        else:
            marcar_cookie_muerta(ridx)
            await update.message.reply_text(f"💀 Cookie muerta marcada:\n`{cv[:60]}...`", parse_mode="Markdown")

    if not cookie_val:
        await update.message.reply_text("❌ No se encontró ninguna cookie viva. Revisa tu stock.")
        return

    if row_idx:
        marcar_cookie_entregada(row_idx)

    token_celular = f"https://netflix.com/?nftoken={token_raw}" if token_raw else "No generado"
    registrar_historial("ADMINISTRADOR", "ADMIN", cookie_val, token_celular)
    cookie_formateada = formatear_cookie_msg(cookie_val)

    pais_msg = f"\n🌍 *País:* `{pais_final}`" if pais_final else ""

    # ── Si es fallback español→random, detectar perfiles en español ──────
    perfiles_msg = ""
    if es_fallback:
        perfiles_info = detectar_perfiles_espanol(cookie_val)
        perfiles_es   = perfiles_info.get("perfiles_espanol", [])
        todos         = perfiles_info.get("todos_perfiles", [])
        if perfiles_es:
            lista_es = ", ".join(f"*{p}*" for p in perfiles_es)
            perfiles_msg = f"\n\n🇪🇸 *Perfiles en español detectados:* {lista_es}"
        elif todos:
            lista_todos = ", ".join(f"`{p}`" for p in todos)
            perfiles_msg = (
                f"\n\n⚠️ *Sin perfiles en español* (idioma de cuenta extranjera).\n"
                f"Perfiles disponibles: {lista_todos}\n"
                f"_(El cliente puede cambiar el idioma desde Cuenta → Perfiles → Idioma)_"
            )
        else:
            perfiles_msg = "\n\n⚠️ No se pudieron leer los perfiles."
        perfiles_msg += "\n_(Cookie entregada como fallback — sin stock español)_"

    msg = f"✅ *Cookie válida:*{pais_msg}\n\n🍪 *Cookie:*\n`{cookie_formateada}`\n\n"
    if token_raw:
        msg += (
            "━━━━━━━━━━━━━━━━━━━\n🔗 *Token:*\n\n"
            f"🌐 Universal:\n`https://netflix.com/?nftoken={token_raw}`\n\n"
            "_(Válido aprox. 1 hora ⏱️)_"
        )
    else:
        msg += "⚠️ No se pudo generar token esta vez."
    msg += perfiles_msg
    msg += "\n━━━━━━━━━━━━━━━━━━━\n📺 *¿Deseas activar esta cuenta en un televisor?*"
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb_si_no_tv())
    context.application.bot_data[f"tv_cookie_{update.effective_user.id}"] = cookie_val

async def cmd_genes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _entregar_cookie_admin(update, context, tipo="es")

async def cmd_genrdm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _entregar_cookie_admin(update, context, tipo="rdm")

async def cmd_gencountry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if context.args:
        await _entregar_cookie_admin(update, context, codigo_pais=context.args[0])
        return
    paises = obtener_paises_disponibles()
    if not paises:
        await update.message.reply_text("❌ No hay cookies disponibles.")
        return
    msg = "🌍 *Países disponibles:*\n\n"
    for cod, (nombre, cantidad) in sorted(paises.items()):
        msg += f"• `{cod}` — {nombre}: *{cantidad}* cookie(s)\n"
    msg += "\nUsa: `/gencountry XX` (ej: `/gencountry BR`)"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def cmd_checkthis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    context.user_data["esperando_checkthis"] = True
    await update.message.reply_text(
        "🔍 *Chequeo individual*\n\nEnvíame la cookie que quieres auditar:",
        parse_mode="Markdown"
    )

async def cmd_checkcookies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    context.user_data["esperando_checkcookies"] = True
    await update.message.reply_text(
        "📦 *Chequeo masivo*\n\nEnvíame el lote de cookies a verificar (una por línea o separadas por `NetflixId=`):",
        parse_mode="Markdown"
    )

async def cmd_resolver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("⚠️ Uso: `/resolver TK-XXXXXX`", parse_mode="Markdown")
        return
    ticket_id = context.args[0].upper()

    # 1. Marcar como RESUELTO en Sheets
    celular, nombre = resolver_ticket_sheets(ticket_id)
    if not celular:
        await update.message.reply_text(f"❌ No se encontró el ticket `{ticket_id}` o ya fue resuelto.", parse_mode="Markdown")
        return

    # 2. Buscar cliente por celular en la hoja NETFLIX
    if not celular:
        await update.message.reply_text(
            f"✅ Ticket `{ticket_id}` marcado como RESUELTO.\n\n"
            f"⚠️ No se pudo entregar cookie: sin celular registrado en el ticket.",
            parse_mode="Markdown"
        )
        return

    cliente = buscar_cliente_por_numero(celular)
    if not cliente or not cliente.get("telegram_id"):
        await update.message.reply_text(
            f"✅ Ticket `{ticket_id}` marcado como RESUELTO.\n\n"
            f"⚠️ No se encontró Telegram ID para `{celular}`. El cliente debe escribir /start primero.",
            parse_mode="Markdown"
        )
        return

    chat_id_cliente = int(cliente["telegram_id"])

    # 3. Buscar nueva cookie
    cliente_sim = {"cookie": "", "precio": 0.0, "celular": celular, "nombre": nombre}
    cookie_activa, estado, row_idx_cookie, token_url, pais = resolver_cookie_valida(cliente_sim, context.application)

    if not cookie_activa:
        await context.bot.send_message(
            chat_id=chat_id_cliente,
            text=f"✅ *Tu ticket {ticket_id} fue resuelto*\n\n"
                 f"Hola *{nombre}*, tu problema ha sido atendido.\n\n"
                 "Si tienes alguna otra consulta, escríbenos. 😊",
            parse_mode="Markdown"
        )
        await update.message.reply_text(
            f"✅ Ticket `{ticket_id}` resuelto.\n⚠️ No hay cookies disponibles para entregar ahora.",
            parse_mode="Markdown"
        )
        return

    # 4. Marcar cookie como entregada y registrar historial
    if row_idx_cookie:
        marcar_cookie_entregada(row_idx_cookie)
    registrar_historial(celular, nombre, cookie_activa, token_url or "")
    token_msg         = formatear_token_msg(token_url, pais)
    cookie_formateada = formatear_cookie_msg(cookie_activa)

    # 5. Enviar cookie + pregunta TV al cliente
    await context.bot.send_message(
        chat_id=chat_id_cliente,
        text=f"✅ *Tu ticket {ticket_id} fue resuelto*\n\n"
             f"Hola *{nombre}*, te enviamos una cookie nueva fresca 🍪\n\n"
             f"🍪 *Tu nueva cookie:*\n`{cookie_formateada}`\n{token_msg}\n\n"
             "━━━━━━━━━━━━━━━━━━━\n📺 *¿Deseas activar Netflix en tu televisor?*",
        parse_mode="Markdown",
        reply_markup=kb_si_no_tv()
    )
    context.application.bot_data[f"tv_cookie_{chat_id_cliente}"] = cookie_activa

    # 6. Confirmar al admin
    await update.message.reply_text(
        f"✅ *Ticket resuelto y cookie entregada*\n\n"
        f"🎫 ID: `{ticket_id}`\n"
        f"👤 Cliente: *{nombre}*\n"
        f"📱 Celular: `{celular}`\n"
        f"🌍 País cookie: `{pais}`",
        parse_mode="Markdown"
    )

async def cmd_checkeo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    msg = await update.message.reply_text("⏳ Iniciando checkeo de cookies Premium... puede tardar 3-5 minutos, no lo canceles.")
    try:
        gc   = get_gspread_client()
        ws   = gc.open_by_key(SHEET_ID_COOKIES).get_worksheet(0)
        rows = ws.get_all_values()

        vivas        = 0
        muertas      = 0
        pausadas     = 0
        errores      = 0
        total        = 0
        muertas_rows  = []  # acumular filas muertas para escribir al final
        pausadas_rows = []  # acumular filas en hold (no borrar)

        i = 0
        while i < len(rows):
            val = str(rows[i][0]).strip() if rows[i] else ""
            if "Cookie:" in val:
                cookie_val = re.sub(r".*Cookie:\s*", "", val).strip()
                if not cookie_val:
                    i += 1
                    continue
                if not _es_cuenta_premium(rows, i):
                    i += 1
                    continue
                total += 1
                row_num = i + 1
                # Buscar fila del Direct Login URL hacia arriba
                direct_row = None
                for k in range(i, max(0, i - 5), -1):
                    v = str(rows[k][0]).strip() if rows[k] else ""
                    if "Direct Login URL:" in v:
                        direct_row = k + 1
                        break
                try:
                    resultado = check_cookie(cookie_val)
                    estado_r  = resultado.get("estado") if resultado else "DEAD"
                    if estado_r == "OK":
                        vivas += 1
                    elif estado_r == "ON_HOLD":
                        pausadas += 1
                        pausadas_rows.append((row_num, direct_row))
                    else:
                        muertas += 1
                        muertas_rows.append((row_num, direct_row))
                except Exception as e:
                    logger.warning(f"[CHECKEO] Error fila {row_num}: {e}")
                    errores += 1

                # Actualizar progreso cada 50 cookies
                if total % 50 == 0:
                    await msg.edit_text(
                        f"⏳ Chequeando... {total} revisadas\n"
                        f"🟢 Vivas: {vivas} | ⚠️ Hold: {pausadas} | 💀 Muertas: {muertas}",
                    )
            i += 1

        # ── Marcar muertas en Sheets ──────────────────────────────────────
        await msg.edit_text(
            f"✅ Checkeo listo. Marcando {len(muertas_rows)} muertas y {len(pausadas_rows)} en hold..."
        )

        for idx, (row_num, direct_row) in enumerate(muertas_rows):
            try:
                ws.update_cell(row_num, 6, "COOKIE MUERTA")
                ws.update_cell(row_num, 7, "💀")
                if direct_row:
                    ws.update_cell(direct_row, 1, "🔗 Direct Login URL: Estado: Muerta ☠️")
                await asyncio.sleep(1.5)
            except Exception as e:
                logger.warning(f"[CHECKEO] Error marcando muerta fila {row_num}: {e}")
                await asyncio.sleep(3)
            if (idx + 1) % 10 == 0:
                await msg.edit_text(f"📝 Marcando muertas... {idx+1}/{len(muertas_rows)}")

        # ── Marcar en hold en Sheets (sin borrar) ────────────────────────
        for idx, (row_num, direct_row) in enumerate(pausadas_rows):
            try:
                ws.update_cell(row_num, 6, "EN PAUSA")
                ws.update_cell(row_num, 7, "⚠️")
                await asyncio.sleep(1.5)
            except Exception as e:
                logger.warning(f"[CHECKEO] Error marcando pausa fila {row_num}: {e}")
                await asyncio.sleep(3)
            if (idx + 1) % 10 == 0:
                await msg.edit_text(f"📝 Marcando en hold... {idx+1}/{len(pausadas_rows)}")

        await msg.edit_text(
            f"✅ *Checkeo completado*\n\n"
            f"📊 Total revisadas (Premium): *{total}*\n"
            f"🟢 Vivas: *{vivas}*\n"
            f"⚠️ En Hold/Pausa: *{pausadas}*\n"
            f"💀 Muertas marcadas: *{muertas}*\n"
            f"🔴 Errores: *{errores}*\n\n"
            f"Las cuentas en hold están marcadas con ⚠️ y NO fueron eliminadas.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"[CHECKEO] Error general: {e}")
        await msg.edit_text(f"❌ Error durante el checkeo: `{e}`", parse_mode="Markdown")

async def cmd_limpiar_muertas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Elimina del sheet de cookies todas las filas pertenecientes a cuentas
    marcadas como MUERTAS (columna F = 'COOKIE MUERTA' o Direct Login URL con 'Muerta').
    Antes de eliminar hace una última verificación de la cookie para no borrar nada vivo.
    Solo accesible para el ADMIN.
    """
    if update.effective_user.id != ADMIN_ID:
        return

    msg = await update.message.reply_text(
        "🧹 *Iniciando limpieza de cookies muertas...*\n\n"
        "Paso 1: Leyendo el sheet y detectando bloques muertos...",
        parse_mode="Markdown"
    )

    try:
        gc   = get_gspread_client()
        ws   = gc.open_by_key(SHEET_ID_COOKIES).get_worksheet(0)
        rows = ws.get_all_values()

        # ── PASO 1: Detectar bloques muertos ─────────────────────────────────
        # Un "bloque" es el conjunto de filas entre dos separadores "------".
        # Primero identificamos todos los bloques y su estado.

        bloques_muertos   = []   # lista de (fila_inicio, fila_fin, cookie) base-1
        bloque_inicio     = None
        cookie_val_bloque = None
        es_muerta_bloque  = False
        col_f_muerta      = False
        sep_anterior      = None   # None = esperando separador de apertura

        i = 0
        while i < len(rows):
            val  = str(rows[i][0]).strip() if rows[i] else ""
            col6 = str(rows[i][5]).strip() if len(rows[i]) > 5 else ""
            fila_actual = i + 1   # base-1

            es_separador = val.startswith("------") or val.endswith("------") or val == "---"*5

            if es_separador:
                if sep_anterior is None:
                    # Apertura de bloque — guardar fila del separador inicial
                    sep_anterior      = fila_actual
                    bloque_inicio     = fila_actual   # incluir el separador de apertura
                    cookie_val_bloque = None
                    es_muerta_bloque  = False
                    col_f_muerta      = False
                else:
                    # Cierre de bloque — bloque_fin incluye el separador de cierre
                    bloque_fin = fila_actual
                    if es_muerta_bloque or col_f_muerta:
                        bloques_muertos.append((bloque_inicio, bloque_fin, cookie_val_bloque))
                    # Resetear para el siguiente bloque — sep_anterior=None
                    # para que el PRÓXIMO separador sea tratado como apertura limpia
                    sep_anterior      = None
                    bloque_inicio     = None
                    cookie_val_bloque = None
                    es_muerta_bloque  = False
                    col_f_muerta      = False
            else:
                # Dentro de un bloque
                if "Direct Login URL:" in val:
                    val_lower = val.lower()
                    if "estado: muerta" in val_lower or "muerta ❌" in val or "muerta" in val_lower:
                        es_muerta_bloque = True
                if "Cookie:" in val and cookie_val_bloque is None:
                    cookie_val_bloque = re.sub(r".*Cookie:\s*", "", val).strip()
                if "COOKIE MUERTA" in col6.upper():
                    col_f_muerta = True

            i += 1

        total_detectados = len(bloques_muertos)
        if total_detectados == 0:
            await msg.edit_text(
                "✅ *No se encontraron bloques muertos para limpiar.*\n\n"
                "El sheet está limpio 🎉",
                parse_mode="Markdown"
            )
            return

        await msg.edit_text(
            f"🔍 Detectados *{total_detectados}* bloques marcados como muertos.\n\n"
            f"Paso 2: Verificación final de cada cookie antes de eliminar...",
            parse_mode="Markdown"
        )

        # ── PASO 2: Verificación final — solo eliminar lo confirmado muerto ──
        bloques_confirmados = []
        verificadas = 0
        for inicio, fin, cookie_val in bloques_muertos:
            verificadas += 1
            if cookie_val:
                try:
                    info = check_cookie(cookie_val)
                    estado_r = info.get("estado") if info else "DEAD"
                    if estado_r == "OK":
                        # ¡Está viva! No eliminar — limpiar marcas
                        logger.info(f"[LIMPIAR] Cookie viva en bloque {inicio}-{fin}, se salva")
                        continue
                    elif estado_r == "ON_HOLD":
                        # En pausa — no eliminar
                        continue
                    # DEAD → confirmar para eliminar
                    bloques_confirmados.append((inicio, fin))
                except Exception:
                    # Si hay error al verificar, ser conservador: no eliminar
                    continue
            else:
                # No se encontró cookie en el bloque → bloque inútil/vacío → eliminar
                bloques_confirmados.append((inicio, fin))

            await asyncio.sleep(1.2)  # respetar rate limit de Netflix

            if verificadas % 10 == 0:
                await msg.edit_text(
                    f"🔍 Verificando... {verificadas}/{total_detectados} revisadas\n"
                    f"Confirmadas para borrar: {len(bloques_confirmados)}",
                )

        confirmados = len(bloques_confirmados)
        if confirmados == 0:
            await msg.edit_text(
                f"✅ *Verificación completada.*\n\n"
                f"De los {total_detectados} bloques marcados como muertos, "
                f"ninguno pudo confirmarse como DEAD en la reverificación.\n\n"
                "No se eliminó ninguna fila. Puedes correr `/checkeo` para actualizar marcas.",
                parse_mode="Markdown"
            )
            return

        await msg.edit_text(
            f"🗑️ *{confirmados} bloques confirmados como muertos.*\n\n"
            f"Paso 3: Eliminando filas del sheet (de abajo hacia arriba)...",
            parse_mode="Markdown"
        )

        # ── PASO 3: Eliminar de abajo hacia arriba para no desplazar índices ─
        # Ordenar en reversa por fila de inicio
        bloques_confirmados.sort(key=lambda x: x[0], reverse=True)

        eliminadas = 0
        for inicio, fin in bloques_confirmados:
            try:
                num_filas = fin - inicio + 1
                ws.delete_rows(inicio, fin)
                eliminadas += num_filas
                await asyncio.sleep(2)   # pausa generosa para no saturar la API
            except Exception as e:
                logger.warning(f"[LIMPIAR] Error eliminando filas {inicio}-{fin}: {e}")
                await asyncio.sleep(5)

        await msg.edit_text(
            f"✅ *Limpieza completada*\n\n"
            f"🔍 Bloques detectados:    *{total_detectados}*\n"
            f"✔️ Confirmados muertos:  *{confirmados}*\n"
            f"🗑️ Filas eliminadas:     *{eliminadas}*\n"
            f"🛡️ Salvadas (vivas/hold): *{total_detectados - confirmados}*\n\n"
            "El sheet quedó más limpio y liviano 🎉\n"
            "Usa /stock para ver el inventario actualizado.",
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"[LIMPIAR_MUERTAS] Error general: {e}")
        await msg.edit_text(f"❌ Error durante la limpieza: `{e}`", parse_mode="Markdown")


async def cmd_cmds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Panel de comandos admin."""
    if update.effective_user.id != ADMIN_ID: return
    lineas = [
        "\U0001f6e0 *Panel de comandos \u2014 Admin Nexus Streaming*",
        "",
        "\u2501\u2501\u2501 \U0001f4e6 STOCK Y COOKIES \u2501\u2501\u2501",
        "/stock \u2014 Resumen del inventario (total, disponibles, muertas, hold)",
        "/checkeo \u2014 Verificar todas las cookies y marcar muertas/hold",
        "/limpiar_muertas — Borrar del sheet bloques de cookies muertas confirmadas",
        "/genes \u2014 Entregar cookie en espa\u00f1ol (fallback random si no hay stock)",
        "/genrdm \u2014 Entregar cookie random de cualquier pa\u00eds",
        "/gencountry \u2014 Ver pa\u00edses disponibles con stock",
        "/gencountry XX \u2014 Entregar cookie de pa\u00eds espec\u00edfico (ej: /gencountry BR)",
        "/checkthis \u2014 Auditar una cookie individual (estado, pa\u00eds, d\u00edas)",
        "/checkcookies \u2014 Verificar un lote de cookies de golpe",
        "",
        "\u2501\u2501\u2501 \U0001f6d2 VENTAS Y PAGOS \u2501\u2501\u2501",
        "/pendientes \u2014 Ver pagos de clientes pendientes de aprobaci\u00f3n",
        "/aprobar ID \u2014 Aprobar pago y entregar cuenta al cliente",
        "/rechazar ID \u2014 Rechazar comprobante de pago",
        "",
        "\u2501\u2501\u2501 \U0001f3ab TICKETS \u2501\u2501\u2501",
        "/resolver TK\u2011XXXX \u2014 Marcar ticket resuelto y enviar cookie nueva al cliente",
        "",
        "\u2501\u2501\u2501 \U0001f3ea MAYORISTAS \u2501\u2501\u2501",
        "/mayoristas \u2014 Lista de proveedores con cr\u00e9ditos",
        "/pendientes_mayor — Pedidos mayoristas pendientes",
        "/aprobar_mayor ID — Aprobar compra de créditos mayoristas",
        "/rechazar_mayor ID — Rechazar comprobante mayorista",
        "",
        "\u2501\u2501\u2501 \U0001f381 REFERIDOS \u2501\u2501\u2501",
        "/canjear \u2014 Canjear cr\u00e9dito de referidos por cookie",
        "",
        "\u2501\u2501\u2501 \u2139\ufe0f AYUDA \u2501\u2501\u2501",
        "/cmds \u2014 Mostrar este panel",
    ]
    await update.message.reply_text("\n".join(lineas), parse_mode="Markdown")


async def cmd_aprobar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args: return
    chat_id_str = context.args[0]
    datos = pendientes_venta.get(chat_id_str)
    if not datos: return
    
    precio, tipo, nombre, celular, chat_id, dispositivo = datos["precio"], datos["tipo"], datos["nombre"], datos["celular"], datos["chat_id"], datos["dispositivo"]

    if precio == 15:
        context.bot_data[f"perfil_{chat_id}"] = {"paso": "nombre", "datos": datos}
        await context.bot.send_message(chat_id=chat_id, text="✅ *¡Pago confirmado!*\n👤 ¿Con qué *nombre* te gustaría tu perfil?", parse_mode="Markdown")
        actualizar_estado_venta(celular, "APROBADO")
        del pendientes_venta[chat_id_str]
        return

    cliente_sim = {"cookie": "", "precio": 10.0 if tipo == "espanol" else 0.0, "celular": celular, "nombre": nombre}
    cookie_activa, estado, row_idx_cookie, token_url, pais = resolver_cookie_valida(cliente_sim, context.application)

    if not cookie_activa:
        await update.message.reply_text("⚠️ No hay cookies disponibles.")
        return

    if row_idx_cookie: marcar_cookie_entregada(row_idx_cookie)
    registrar_historial(celular, nombre, cookie_activa, token_url or "")
    actualizar_estado_venta(celular, "APROBADO")
    agregar_cliente_nuevo(nombre, celular, float(precio), dispositivo, cookie=cookie_activa)

    token_msg         = formatear_token_msg(token_url, pais)
    cookie_formateada = formatear_cookie_msg(cookie_activa)
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"✅ *¡Pago confirmado!*\n\n🍪 *Tu cookie:*\n`{cookie_formateada}`\n{token_msg}\n\n"
             "━━━━━━━━━━━━━━━━━━━\n📺 *¿Deseas activar Netflix en tu televisor?*",
        parse_mode="Markdown",
        reply_markup=kb_si_no_tv()
    )
    context.application.bot_data[f"tv_cookie_{chat_id}"] = cookie_activa

    # ── Confirmación al admin ──
    await update.message.reply_text(
        f"✅ *Cuenta entregada correctamente*\n\n"
        f"👤 Cliente: *{nombre}*\n"
        f"📱 Celular: `{celular}`\n"
        f"💰 Plan: S/{precio} — {tipo}\n"
        f"🌍 País cookie: `{pais}`",
        parse_mode="Markdown"
    )
    del pendientes_venta[chat_id_str]

async def cmd_rechazar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args: return
    chat_id_str = context.args[0]
    if chat_id_str in pendientes_venta:
        actualizar_estado_venta(pendientes_venta[chat_id_str]["celular"], "RECHAZADO")
        await context.bot.send_message(chat_id=pendientes_venta[chat_id_str]["chat_id"], text="❌ *Pago no válido.*", parse_mode="Markdown")
        del pendientes_venta[chat_id_str]

async def cmd_pendientes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not pendientes_venta:
        await update.message.reply_text("✅ No hay pedidos pendientes.")
        return
    msg = "📋 *Pedidos pendientes:*\n\n"
    for cid, d in pendientes_venta.items():
        msg += f"👤 {d['nombre']} | 📱 {d['celular']}\n📋 {d['plan']} — S/{d['precio']}\n`/aprobar {cid}` | `/rechazar {cid}`\n━━━\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def handler_perfil_global(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_user.id
    texto   = update.message.text.strip()

    # ── Chequeo individual /checkthis ──
    if context.user_data.get("esperando_checkthis"):
        context.user_data.pop("esperando_checkthis", None)
        info = check_cookie(texto)
        estado = info.get("estado") if info else "DEAD"
        pais   = info.get("country_code", "?") if info else "?"
        dias   = info.get("dias_restantes") if info else None
        if estado == "OK":
            dias_txt = f" · *{dias} días restantes*" if dias is not None else ""
            await update.message.reply_text(
                f"✅ *Cookie VIVA* 🟢\n🌍 País: `{pais}`{dias_txt}",
                parse_mode="Markdown"
            )
        elif estado == "ON_HOLD":
            await update.message.reply_text(
                f"⚠️ *Cookie EN PAUSA* (On Hold)\n🌍 País: `{pais}`\n💳 Problema de pago — no apta para entregar.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("💀 *Cookie MUERTA*", parse_mode="Markdown")
        return

    # ── Chequeo masivo /checkcookies ──
    if context.user_data.get("esperando_checkcookies"):
        context.user_data.pop("esperando_checkcookies", None)
        # Extraer cookies: separadas por línea o por "NetflixId="
        import re as _re
        partes = _re.split(r'\n|(?=NetflixId=)', texto)
        cookies = [p.strip() for p in partes if p.strip() and len(p.strip()) > 20]
        total = len(cookies)
        if total == 0:
            await update.message.reply_text("⚠️ No encontré cookies en el texto enviado.")
            return
        msg_progreso = await update.message.reply_text(f"⏳ Chequeando {total} cookies...")
        vivas = 0
        pausadas = 0
        muertas = 0
        for cookie in cookies:
            info = check_cookie(cookie)
            estado = info.get("estado") if info else "DEAD"
            if estado == "OK":
                vivas += 1
            elif estado == "ON_HOLD":
                pausadas += 1
            else:
                muertas += 1
        await msg_progreso.edit_text(
            f"📊 *Reporte de chequeo*\n\n"
            f"📦 Total: {total}\n"
            f"🟢 Vivas: {vivas}\n"
            f"⚠️ En Hold/Pausa: {pausadas}\n"
            f"💀 Muertas: {muertas}",
            parse_mode="Markdown"
        )
        return

    # ── Flujo TV post-aprobación de pago ──
    tv_key = f"tv_cookie_{chat_id}"
    if tv_key in context.application.bot_data:
        cookie_activa = context.application.bot_data[tv_key]
        if texto == "✅ Sí, actívame en mi TV":
            await update.message.reply_text(
                "📺 Ve a tu televisor, abre Netflix y busca la opción de iniciar sesión desde la web.\n\n"
                "Debería aparecer un código de 8 caracteres en la pantalla.\n\n"
                "👉 *Escribe ese código aquí abajo:*",
                parse_mode="Markdown",
                reply_markup=kb_con_menu([])
            )
            context.user_data["cookie_activa"] = cookie_activa
            context.user_data["esperando_codigo_tv_global"] = True
            del context.application.bot_data[tv_key]
            return
        elif texto == "❌ No, gracias":
            await update.message.reply_text("😄 ¡Genial! Que disfrutes del servicio. 🍿", reply_markup=kb_menu())
            del context.application.bot_data[tv_key]
            return

    # ── Recibir código TV fuera del ConversationHandler ──
    if context.user_data.get("esperando_codigo_tv_global"):
        if texto == BTN_MENU:
            context.user_data.pop("esperando_codigo_tv_global", None)
            await update.message.reply_text("🏠 Menú principal:", reply_markup=kb_menu())
            return
        codigo_tv = texto.replace(" ", "")
        if len(codigo_tv) != 8:
            await update.message.reply_text("❌ El código debe tener exactamente 8 caracteres. Intenta de nuevo:", reply_markup=kb_con_menu([]))
            return
        cookie_activa = context.user_data.get("cookie_activa")
        msg = await update.message.reply_text("⏳ Procesando... Conectando con tu televisor...")
        resultado = activar_tv_con_codigo(cookie_activa, codigo_tv)
        if resultado['success']:
            await msg.edit_text(f"🎉 *¡Éxito!*\n\n{resultado['message']}\nYa deberías ver tu perfil de Netflix en la TV.", parse_mode="Markdown")
        else:
            await msg.edit_text(f"⚠️ *Error:*\n{resultado['message']}", parse_mode="Markdown")
            await update.message.reply_text("Verifica el código en tu TV y envíalo de nuevo, o presiona Menú para salir.", reply_markup=kb_con_menu([]))
            return
        context.user_data.pop("esperando_codigo_tv_global", None)
        await update.message.reply_text("¿Necesitas ayuda con algo más?", reply_markup=kb_menu())
        return

    # ── Flujo perfil personalizado (plan S/15) ──
    key = f"perfil_{chat_id}"
    if key not in context.bot_data: return
    estado = context.bot_data[key]
    if estado["paso"] == "nombre":
        context.bot_data[key]["nombre_perfil"] = update.message.text.strip()
        context.bot_data[key]["paso"] = "pin"
        await update.message.reply_text("🔢 ¿Qué *PIN de 4 dígitos* deseas?", parse_mode="Markdown")
    elif estado["paso"] == "pin":
        pin = update.message.text.strip()
        if not pin.isdigit() or len(pin) != 4:
            await update.message.reply_text("Solo 4 dígitos.")
            return
        await update.message.reply_text("✅ Perfil en configuración.", reply_markup=kb_menu())
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"👤 *CONFIGURAR PERFIL*\nCliente: {estado['datos']['nombre']}\nPerfil: {estado['nombre_perfil']}\nPIN: {pin}", parse_mode="Markdown")
        agregar_cliente_nuevo(estado['datos']["nombre"], estado['datos']["celular"], 15.0, estado['datos'].get("dispositivo", "PERSONAL"))
        del context.bot_data[key]

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("👋 Cancelado.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════

async def soporte_wa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"soporte_wa llamado por user_id: {user_id}")
    if user_id not in [ADMIN_ID, BRIDGE_BOT_ID]:
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("❌ Uso: /soporte 51XXXXXXXXX")
        return
    
    celular_wa = normalizar_celular(args[0])
    cliente = leer_cliente(celular_wa)
    
    if not cliente:
        await update.message.reply_text(
            f"❌ El número {celular_wa} no está registrado como cliente.\n"
            "Por favor comunícate con el administrador."
        )
        return
    
    nombre = cliente["nombre"]
    dias = cliente["dias_restantes"]
    cookie = cliente["cookie"]
    
    respuesta = (
        f"WA:51{celular_wa}\n"
        f"✅ ¡Hola, {nombre}! Tu sesión está activa.\n\n"
        f"📅 Días restantes: {dias}\n"
        f"🍪 Tu cookie activa:\n{cookie}"
    )
    await update.message.reply_text(respuesta)

async def soporte_wa_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"soporte_wa_mensaje llamado por user_id: {update.effective_user.id}")
    
    text = update.message.text
    if not text:
        return
    
    # Extrae número del comando /soporte5151928671758
    celular_wa = normalizar_celular(text.replace("/soporte51", "").strip())
    cliente = leer_cliente(celular_wa)
    
    if not cliente:
        await update.message.reply_text(
            f"❌ El número {celular_wa} no está registrado.\n"
            "Comunícate con el administrador."
        )
        return
    
    nombre = cliente["nombre"]
    dias = cliente["dias_restantes"]
    cookie = cliente["cookie"]
    
    respuesta = (
        f"WA:51{celular_wa}\n"
        f"✅ ¡Hola, {nombre}! Tu sesión está activa.\n\n"
        f"📅 Días restantes: {dias}\n"
        f"🍪 Tu cookie activa:\n{cookie}"
    )
    await update.message.reply_text(respuesta)

async def ayuda_wa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != BRIDGE_BOT_ID:
        return
    
    args = context.args
    if not args:
        return
    
    celular_wa = normalizar_celular(args[0])
    cliente = leer_cliente(celular_wa)
    
    if not cliente:
        await _enviar_wa(celular_wa, 
            "❌ Tu número no está registrado como cliente.\n"
            "Comunícate con el administrador."
        )
        return
    
    nombre = cliente["nombre"]
    dias = cliente["dias_restantes"]
    cookie = cliente["cookie"]
    
    if dias is not None and dias < 0:
        await _enviar_wa(celular_wa,
            f"⚠️ Hola {nombre}, tu suscripción venció hace {abs(dias)} día(s).\n\n"
            "❌ El soporte solo está disponible para clientes activos.\n\n"
            "💳 Renueva tu plan para seguir disfrutando el servicio."
        )
        return
    
    # Entregar cookie
    cookie_formateada = cookie.strip()
    await _enviar_wa(celular_wa,
        f"✅ ¡Hola, {nombre}! Tu sesión está activa.\n\n"
        f"📅 Días restantes: {dias}\n\n"
        f"🍪 Tu cookie activa:\n{cookie_formateada}\n\n"
        "📺 ¿Deseas activar Netflix en tu TV?\n"
        "Responde: *1* para activar TV o *2* para finalizar"
    )
    
    # Guardar estado esperando respuesta TV
    context.application.bot_data[f"wa_tv_{celular_wa}"] = True

def main() -> None:
    if not BOT_TOKEN: return
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("ayuda", ayuda_wa))

# Comandos admin
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Chat(-5282560412) & filters.User(BRIDGE_BOT_ID), 
        soporte_wa_mensaje
    ))
    for cmd, fn in [("aprobar", cmd_aprobar), ("rechazar", cmd_rechazar), ("resolver", cmd_resolver), ("checkeo", cmd_checkeo), 
                    ("stock", cmd_stock), ("genes", cmd_genes), ("genrdm", cmd_genrdm),
                    ("gencountry", cmd_gencountry), ("pendientes", cmd_pendientes),
                    ("canjear", cmd_canjear),
                    ("checkthis", cmd_checkthis), ("checkcookies", cmd_checkcookies),
                    ("limpiar_muertas", cmd_limpiar_muertas),
                    ("cmds", cmd_cmds),
                    ("aprobar_mayor", cmd_aprobar_mayor), ("rechazar_mayor", cmd_rechazar_mayor),
                    ("mayoristas", cmd_mayoristas), ("pendientes_mayor", cmd_pendientes_mayor)]:
        app.add_handler(CommandHandler(cmd, fn))

    menu_fallback = MessageHandler(filters.Regex(f"^{re.escape(BTN_MENU)}$"), volver_menu)
    cancel_venta_fallback = MessageHandler(filters.Regex(f"^{re.escape(BTN_CANCELAR_VENTA)}$"), volver_menu)


    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex(f"^{re.escape(BTN_MAYORISTA)}$"), opcion_mayorista),
        ],
        states={
            MENU_PRINCIPAL: [
                MessageHandler(filters.Regex(f"^{re.escape(BTN_INCONVENIENTES)}$"), opcion_inconvenientes),
                MessageHandler(filters.Regex(f"^{re.escape(BTN_TICKET)}$"), opcion_ticket),
                MessageHandler(filters.Regex(f"^{re.escape(BTN_DIAS)}$"), opcion_dias),
                MessageHandler(filters.Regex(f"^{re.escape(BTN_PROMOCIONES)}$"), opcion_promociones),
                MessageHandler(filters.Regex(f"^{re.escape(BTN_COMPRAR)}$"), opcion_comprar),
                MessageHandler(filters.Regex(f"^{re.escape(BTN_PLANES)}$"), opcion_planes),
                MessageHandler(filters.Regex(f"^{re.escape(BTN_REFERIDOS)}$"), opcion_referidos),
                # Botón mayorista — siempre disponible desde menú principal
                MessageHandler(filters.Regex(f"^{re.escape(BTN_MAYORISTA)}$"), opcion_mayorista),
                # Botones del panel mayorista desde menú principal
                MessageHandler(
                    filters.Regex(f"^({re.escape(BTN_MAYOR_SALDO)}|{re.escape(BTN_MAYOR_HISTORIAL)}|{re.escape(BTN_MAYOR_COMPRAR_MAS)}|{re.escape(BTN_MAYOR_CANJEAR)})$"),
                    mayor_panel_desde_menu
                ),
            ],
            ESPERANDO_CELULAR: [
                menu_fallback,
                MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_celular),
            ],
            ESPERANDO_MOTIVO_TICKET: [
                menu_fallback,
                MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_motivo_ticket),
            ],
            PREGUNTA_ACTIVAR_TV: [
                menu_fallback,
                MessageHandler(filters.Regex(f"^{re.escape(BTN_SI_TV)}$"), respuesta_si_tv),
                MessageHandler(filters.Regex(f"^{re.escape(BTN_NO_TV)}$"), respuesta_no_tv),
                MessageHandler(filters.Regex(f"^{re.escape(BTN_ACTIVAR_TV_NUEVO)}$"), respuesta_si_tv),
            ],
            ESPERANDO_CODIGO_TV: [
                menu_fallback,
                MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_codigo_tv),
            ],
            VENTA_ELEGIR_CANAL: [
                menu_fallback,
                MessageHandler(filters.TEXT & ~filters.COMMAND, venta_elegir_canal),
            ],
            VENTA_ELEGIR_ORIGEN: [
                menu_fallback,
                MessageHandler(filters.TEXT & ~filters.COMMAND, venta_recibir_origen),
            ],
            VENTA_ELEGIR_METODO_INT: [
                menu_fallback, cancel_venta_fallback,
                MessageHandler(filters.TEXT & ~filters.COMMAND, venta_recibir_metodo_int),
            ],
            VENTA_ELEGIR_DISPOSITIVO: [
                menu_fallback, cancel_venta_fallback,
                MessageHandler(filters.TEXT & ~filters.COMMAND, venta_elegir_dispositivo),
            ],
            VENTA_ELEGIR_PLAN: [
                menu_fallback, cancel_venta_fallback,
                MessageHandler(filters.TEXT & ~filters.COMMAND, venta_elegir_plan),
            ],
            VENTA_CONFIRMAR_RAPIDO: [
                menu_fallback, cancel_venta_fallback,
                MessageHandler(filters.TEXT & ~filters.COMMAND, venta_confirmar_rapido),
            ],
            VENTA_PEDIR_NOMBRE: [
                menu_fallback,
                MessageHandler(filters.TEXT & ~filters.COMMAND, venta_pedir_nombre),
            ],
            VENTA_PEDIR_CELULAR: [
                menu_fallback,
                MessageHandler(filters.TEXT & ~filters.COMMAND, venta_pedir_celular),
            ],
            VENTA_PEDIR_COMPROBANTE: [
                menu_fallback, cancel_venta_fallback,
                MessageHandler(filters.TEXT & ~filters.COMMAND, fallo_comprobante),
                MessageHandler(filters.PHOTO, venta_recibir_comprobante),
            ],
            # Estados mayorista dentro del conv principal (comprar más créditos)
            MAYOR_ELEGIR_ORIGEN: [
                menu_fallback,
                MessageHandler(filters.TEXT & ~filters.COMMAND, mayor_recibir_origen),
            ],
            MAYOR_ELEGIR_METODO_INT: [
                menu_fallback, cancel_venta_fallback,
                MessageHandler(filters.TEXT & ~filters.COMMAND, mayor_recibir_metodo_int),
            ],
            MAYOR_ELEGIR_CANTIDAD: [
                menu_fallback, cancel_venta_fallback,
                MessageHandler(filters.TEXT & ~filters.COMMAND, mayor_elegir_cantidad),
            ],
            MAYOR_PEDIR_COMPROBANTE: [
                menu_fallback, cancel_venta_fallback,
                MessageHandler(filters.PHOTO, mayor_recibir_comprobante),
                MessageHandler(filters.TEXT & ~filters.COMMAND, mayor_fallo_comprobante),
            ],
            MAYOR_CANJEAR_ETIQUETA: [
                menu_fallback,
                MessageHandler(filters.TEXT & ~filters.COMMAND, mayor_recibir_etiqueta),
            ],
            MAYOR_ELEGIR_REGION: [
                menu_fallback,
                MessageHandler(filters.TEXT & ~filters.COMMAND, mayor_recibir_region),
            ],
        },
        fallbacks=[
            CommandHandler("cancelar", cancelar),
            MessageHandler(filters.Regex(f"^{re.escape(BTN_MENU)}$"), volver_menu),
        ],
    )

    app.add_handler(CommandHandler("soporte", soporte_wa))
    app.add_handler(CommandHandler("soporte51", soporte_wa_mensaje))
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler_perfil_global))

    # ── Job recordatorios: corre cada día a las 10:00 AM hora Perú ──
    from telegram.ext import JobQueue
    job_queue = app.job_queue
    if job_queue:
        # Ejecutar a las 10:00 hora Perú (UTC-5 = 15:00 UTC)
        import datetime as dt
        hora_envio = dt.time(hour=15, minute=0, tzinfo=timezone.utc)
        job_queue.run_daily(job_recordatorios, time=hora_envio, name="recordatorios_diarios")
        logger.info("✅ Job de recordatorios programado a las 10:00 AM (Perú)")

    # drop_pending_updates=True: descarta mensajes acumulados si el bot estuvo caído,
    # evita el error Conflict cuando Railway reinicia y había otra instancia corriendo
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
