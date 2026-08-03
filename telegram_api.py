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


# [rotulo](url) -- aceita espaco entre ] e (, e um nivel de parenteses dentro
# da URL (ex.: .../Bot_(informatica)).
LINK_RE = re.compile(
    r"\[([^\[\]\n]+)\][ \t]*\([ \t]*([^()\s]*(?:\([^()\s]*\)[^()\s]*)*)[ \t]*\)"
)

# Esquemas que o Telegram aceita num href.
SCHEME_RE = re.compile(r"^(?:https?://|tg://|mailto:|tel:)", re.I)

# Marca temporaria que guarda o lugar de um link durante a conversao. Usa \x00
# porque esse caractere nao aparece em texto digitado no painel.
_SLOT_RE = re.compile(r"\x00(\d+)\x00")


def _escape_attr(url):
    """Escapa a URL para dentro do href usando so as entidades que o Telegram
    entende (&amp; &lt; &gt; &quot;)."""
    return (url.replace("&", "&amp;")
               .replace("<", "&lt;")
               .replace(">", "&gt;")
               .replace('"', "&quot;"))


def _normalize_url(url):
    """Devolve a URL pronta para o href, ou None se nao parecer um link.

    Aceita link escrito sem http:// (o mais comum de quem so cola o endereco):
    'www.site.com' e 'site.com.br/promo' viram 'https://...'.
    """
    url = url.strip()
    if not url:
        return None
    if SCHEME_RE.match(url):
        return url
    if "@" in url and "/" not in url:          # e-mail digitado solto
        return "mailto:" + url
    if "." in url.split("/", 1)[0]:            # tem cara de dominio
        return "https://" + url
    return None


def _inline(text):
    """Aplica *negrito* e _italico_ num trecho de texto JA escapado."""
    text = re.sub(r"\*([^*\n]+)\*", r"<b>\1</b>", text)
    text = re.sub(r"_([^_\n]+)_", r"<i>\1</i>", text)
    return text


def render_html(text):
    """Converte marcacoes simples em HTML do Telegram, de forma segura.

        *negrito*            -> <b>negrito</b>
        _italico_            -> <i>italico</i>
        [texto](https://...) -> <a href="...">texto</a>

    Os links sao retirados do texto ANTES de escapar e de aplicar negrito/
    italico, e so voltam no fim. Sem isso uma URL com '_' ou '*' (ex.:
    site.com/promo_black_friday) era despedacada por essas marcacoes e o
    Telegram recusava a mensagem inteira.
    """
    if not text:
        return text or ""
    text = text.replace("\x00", "")   # protege a marca temporaria

    links = []

    def _guardar(m):
        url = _normalize_url(m.group(2))
        if url is None:
            return m.group(0)         # nao parece link: segue como texto comum
        rotulo = _inline(html_lib.escape(m.group(1), quote=False))
        links.append(f'<a href="{_escape_attr(url)}">{rotulo}</a>')
        return f"\x00{len(links) - 1}\x00"

    esc = LINK_RE.sub(_guardar, text)         # 1) tira os links do caminho
    esc = html_lib.escape(esc, quote=False)   # 2) escapa & < > do resto
    esc = _inline(esc)                        # 3) *negrito* e _italico_
    return _SLOT_RE.sub(lambda m: links[int(m.group(1))], esc)  # 4) devolve os links


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
