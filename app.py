"""Painel web (Flask) para criar e gerenciar disparos programados no Telegram."""
import uuid
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import (Flask, render_template, request, redirect, url_for, jsonify,
                   flash, session)
from werkzeug.security import generate_password_hash, check_password_hash

import db
import scheduler
import telegram_api
from config import (BOT_TOKEN, PORT, TIMEZONE, UPLOAD_DIR, ALLOWED_IMAGE,
                    ALLOWED_VIDEO, ADMIN_USER, ADMIN_PASSWORD, SECRET_KEY)

TZ = ZoneInfo(TIMEZONE)

app = Flask(__name__)
app.secret_key = SECRET_KEY


# ------------------------------------------------------------- autenticacao ---

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login", next=request.path))
        if not session.get("is_admin"):
            flash("Acesso restrito ao administrador.", "error")
            return redirect(url_for("index"))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_user():
    """Disponibiliza o usuario logado para todos os templates (barra superior)."""
    return {"current_user": session.get("user"),
            "current_is_admin": bool(session.get("is_admin"))}


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user"):
        return redirect(url_for("index"))
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        user = db.get_user(username)
        if user and check_password_hash(user["password_hash"], password):
            session["user"] = user["username"]
            session["is_admin"] = bool(user["is_admin"])
            nxt = request.args.get("next") or url_for("index")
            if not nxt.startswith("/"):   # evita redirect para site externo
                nxt = url_for("index")
            return redirect(nxt)
        flash("Usuário ou senha inválidos.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# --------------------------------------------------------------- usuarios -----

@app.route("/users")
@admin_required
def users():
    return render_template("users.html", users=db.list_users())


@app.route("/users/add", methods=["POST"])
@admin_required
def users_add():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    is_admin = bool(request.form.get("is_admin"))
    if not username or not password:
        flash("Informe usuário e senha.", "error")
    elif db.get_user(username):
        flash(f"O usuário '{username}' já existe.", "error")
    else:
        db.create_user(username, generate_password_hash(password), is_admin)
        flash(f"Usuário '{username}' criado com sucesso.", "ok")
    return redirect(url_for("users"))


@app.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def users_delete(user_id):
    target = next((u for u in db.list_users() if u["id"] == user_id), None)
    if target and target["username"] == session.get("user"):
        flash("Você não pode excluir a própria conta.", "error")
    else:
        db.delete_user(user_id)
        flash("Usuário removido.", "ok")
    return redirect(url_for("users"))


def _save_upload(file_storage, expected):
    """Salva o arquivo enviado validando a extensao. Retorna o caminho salvo."""
    ext = Path(file_storage.filename).suffix.lower()
    allowed = ALLOWED_IMAGE if expected == "photo" else ALLOWED_VIDEO
    if ext not in allowed:
        raise ValueError(f"Extensao {ext or '(vazia)'} nao permitida para {expected}.")
    dest = UPLOAD_DIR / f"{uuid.uuid4().hex}{ext}"
    file_storage.save(dest)
    return str(dest)


@app.route("/")
@login_required
def index():
    bot = None
    bot_error = None
    try:
        bot = telegram_api.get_me()
    except Exception as exc:
        bot_error = str(exc)
    # "Agora" no fuso configurado, para preencher data/hora padrao coerentes
    # com o fuso que o agendador realmente usa (nao o do navegador).
    now = datetime.now(TZ)
    return render_template(
        "index.html",
        dispatches=db.list_dispatches(),
        bot=bot,
        bot_error=bot_error,
        timezone=TIMEZONE,
        today=now.strftime("%Y-%m-%d"),
        now_time=now.strftime("%H:%M"),
    )


@app.route("/dispatch", methods=["POST"])
@login_required
def create():
    f = request.form
    msg_type = f.get("msg_type", "text")
    text = (f.get("text") or "").strip()

    # Junta data e hora do formulario num ISO local.
    date = f.get("date")
    time = f.get("time")
    if not date or not time:
        flash("Informe data e hora do disparo.", "error")
        return redirect(url_for("index"))
    scheduled_at = f"{date}T{time}:00"

    repeat = f.get("repeat", "once")
    # Para envio unico, o horario precisa ser futuro. Damos 60s de tolerancia
    # (o padrao do formulario e "agora", entao clicar na hora certa deve valer).
    # Envios recorrentes (diario/semanal) podem ter horario "passado" hoje,
    # pois disparam na proxima ocorrencia.
    if repeat == "once":
        try:
            run_dt = datetime.fromisoformat(scheduled_at).replace(tzinfo=TZ)
        except ValueError:
            flash("Data ou hora invalida.", "error")
            return redirect(url_for("index"))
        if run_dt < datetime.now(TZ) - timedelta(seconds=60):
            flash("O horário escolhido já passou. Escolha um horário futuro.", "error")
            return redirect(url_for("index"))

    chat_id = (f.get("chat_id") or "").strip()
    if not chat_id:
        flash("Informe o grupo/canal de destino.", "error")
        return redirect(url_for("index"))

    media_path = None
    try:
        if msg_type in ("photo", "video"):
            upload = request.files.get("media")
            if not upload or not upload.filename:
                raise ValueError("Selecione o arquivo de foto/video.")
            media_path = _save_upload(upload, msg_type)
        elif not text:
            raise ValueError("Escreva o texto da mensagem.")
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("index"))

    dispatch_id = db.create_dispatch(
        chat_id=chat_id,
        chat_label=(f.get("chat_label") or "").strip() or chat_id,
        msg_type=msg_type,
        text=text,
        media_path=media_path,
        scheduled_at=scheduled_at,
        repeat=repeat,
        formatar=1 if f.get("formatar") else 0,
        created_by=session.get("user"),
        status="pending",
    )
    scheduler.schedule_dispatch(dispatch_id, scheduled_at, repeat)
    flash("Disparo agendado com sucesso!", "ok")
    return redirect(url_for("index"))


@app.route("/dispatch/<int:dispatch_id>/cancel", methods=["POST"])
@login_required
def cancel(dispatch_id):
    scheduler.cancel_job(dispatch_id)
    db.update_dispatch(dispatch_id, status="canceled")
    flash("Disparo cancelado.", "ok")
    return redirect(url_for("index"))


@app.route("/dispatch/<int:dispatch_id>/delete", methods=["POST"])
@login_required
def delete(dispatch_id):
    scheduler.cancel_job(dispatch_id)
    db.delete_dispatch(dispatch_id)
    flash("Disparo removido.", "ok")
    return redirect(url_for("index"))


@app.route("/discover")
@login_required
def discover():
    """Endpoint AJAX: lista grupos/canais recentes onde o bot esta."""
    try:
        return jsonify({"ok": True, "chats": telegram_api.discover_chats()})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)})


def _seed_admin():
    """Cria a conta de administrador a partir do .env no primeiro start."""
    if db.count_users() == 0:
        db.create_user(ADMIN_USER, generate_password_hash(ADMIN_PASSWORD),
                       is_admin=True)
        print(f"  [INFO] Usuario admin '{ADMIN_USER}' criado a partir do .env.")
        if ADMIN_PASSWORD == "admin":
            print("  [ATENCAO] Senha padrao 'admin' em uso. Troque ADMIN_PASSWORD no .env!")


def main():
    db.init_db()
    _seed_admin()
    scheduler.start()
    print(f"\n  Painel: http://127.0.0.1:{PORT}\n")
    if not BOT_TOKEN:
        print("  [ATENCAO] Configure TELEGRAM_BOT_TOKEN no arquivo .env\n")
    # use_reloader=False para nao iniciar o agendador em processo duplicado.
    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
