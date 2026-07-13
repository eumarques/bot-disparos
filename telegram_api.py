"""Funcoes simples que falam direto com a Bot API do Telegram via HTTP."""
import html as html_lib
import re

import requests

from config import BOT_TOKEN

API_BASE = "https://api.telegram.org/bot{token}/{method}"
TIMEOUT = 60


class TelegramError(Exception):
    pass


def _url(method):
    if not BOT_TOKEN:
        raise TelegramError("TELEGRAM_BOT_TOKEN nao configurado no arquivo .env")
    return API_BASE.format(token=BOT_TOKEN, method=method)


def _post(method, data=None, files=None):
    resp = requests.post(_url(method), data=data, files=files, timeout=TIMEOUT)
    payload = resp.json()
    if not payload.get("ok"):
        raise TelegramError(payload.get("description", "erro desconhecido"))
    return payload["result"]


def get_me():
    """Retorna os dados do bot (usado para mostrar que o token funciona)."""
    return _post("getMe")


def render_html(text):
    """Converte marcacoes simples em HTML do Telegram, de forma segura.

    Primeiro escapa TUDO (& < >) para o texto do usuario nunca quebrar o
    parse; depois transforma as marcacoes (que usam caracteres nao-HTML):
        *negrito*            -> <b>negrito</b>
        _italico_            -> <i>italico</i>
        [texto](https://...) -> <a href="...">texto</a>
    """
    if not text:
        return text or ""
    esc = html_lib.escape(text, quote=False)  # escapa & < >

    def _link(m):
        label, url = m.group(1), m.group(2)
        return f'<a href="{html_lib.escape(url, quote=True)}">{label}</a>'

    esc = re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", _link, esc)
    esc = re.sub(r"\*([^*\n]+)\*", r"<b>\1</b>", esc)     # *negrito*
    esc = re.sub(r"_([^_\n]+)_", r"<i>\1</i>", esc)       # _italico_
    return esc


def _text_payload(field, text, parse_html):
    """Monta o campo de texto/legenda, aplicando formatacao se pedido.

    Sem parse_html o texto vai puro (qualquer caractere e aceito).
    """
    if parse_html:
        return {field: render_html(text or ""), "parse_mode": "HTML"}
    return {field: text or ""}


def send_text(chat_id, text, parse_html=False):
    data = {"chat_id": chat_id, **_text_payload("text", text, parse_html)}
    return _post("sendMessage", data=data)


def send_photo(chat_id, media_path, caption=None, parse_html=False):
    with open(media_path, "rb") as fh:
        data = {"chat_id": chat_id, **_text_payload("caption", caption, parse_html)}
        return _post("sendPhoto", data=data, files={"photo": fh})


def send_video(chat_id, media_path, caption=None, parse_html=False):
    with open(media_path, "rb") as fh:
        data = {"chat_id": chat_id, **_text_payload("caption", caption, parse_html)}
        return _post("sendVideo", data=data, files={"video": fh})


def discover_chats():
    """Le as atualizacoes recentes e devolve os chats onde o bot aparece.

    Serve para descobrir o id/@usuario de grupos e canais. Para funcionar,
    e preciso que exista atividade recente (uma mensagem no grupo, ou o bot
    ser adicionado/promovido a admin no canal).
    """
    # getUpdates nao funciona junto com webhook (ex.: bot ligado ao ManyChat).
    # Avisamos de forma clara em vez de estourar o erro cru "Conflict".
    info = _post("getWebhookInfo")
    if info.get("url"):
        raise TelegramError(
            "Este bot esta com um webhook ativo (" + info["url"] + "), "
            "provavelmente ligado a outra ferramenta. Para descobrir os chats e "
            "preciso remover o webhook (isso pode desligar a outra integracao). "
            "Se preferir manter, digite o ID do grupo/canal manualmente."
        )

    updates = _post("getUpdates", data={"timeout": 0, "limit": 100})
    chats = {}
    for upd in updates:
        for key in ("message", "channel_post", "my_chat_member", "chat_member"):
            obj = upd.get(key)
            if not obj:
                continue
            chat = obj.get("chat", {})
            if chat and chat.get("id") is not None:
                title = chat.get("title") or chat.get("username") or chat.get("first_name")
                chats[chat["id"]] = {
                    "id": chat["id"],
                    "title": title or str(chat["id"]),
                    "type": chat.get("type"),
                    "username": chat.get("username"),
                }
    return list(chats.values())
