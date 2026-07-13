"""Agendador: guarda os jobs no disco e dispara as mensagens na hora certa."""
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger

import db
import telegram_api
from config import JOBS_DB_URL, TIMEZONE

TZ = ZoneInfo(TIMEZONE)

# Os jobs sao persistidos em jobs.sqlite -> sobrevivem a reinicios do programa.
scheduler = BackgroundScheduler(
    jobstores={"default": SQLAlchemyJobStore(url=JOBS_DB_URL)},
    timezone=TZ,
)


def start():
    if not scheduler.running:
        scheduler.start()


def _job_id(dispatch_id):
    return f"dispatch:{dispatch_id}"


def schedule_dispatch(dispatch_id, scheduled_at_iso, repeat):
    """Cria (ou substitui) o job de um disparo ja gravado no banco."""
    run_dt = datetime.fromisoformat(scheduled_at_iso).replace(tzinfo=TZ)

    if repeat == "daily":
        trigger = CronTrigger(hour=run_dt.hour, minute=run_dt.minute,
                              start_date=run_dt, timezone=TZ)
    elif repeat == "weekly":
        trigger = CronTrigger(day_of_week=run_dt.weekday(), hour=run_dt.hour,
                              minute=run_dt.minute, start_date=run_dt, timezone=TZ)
    else:  # once
        trigger = DateTrigger(run_date=run_dt, timezone=TZ)

    scheduler.add_job(
        send_dispatch,
        trigger=trigger,
        args=[dispatch_id],
        id=_job_id(dispatch_id),
        replace_existing=True,
        misfire_grace_time=3600,  # tolera atraso de ate 1h (ex.: PC estava desligado)
    )


def cancel_job(dispatch_id):
    try:
        scheduler.remove_job(_job_id(dispatch_id))
    except Exception:
        pass  # job pode ja ter rodado ou nao existir


def send_dispatch(dispatch_id):
    """Funcao chamada pelo agendador na hora marcada. Envia via Telegram."""
    d = db.get_dispatch(dispatch_id)
    if not d or d["status"] == "canceled":
        return

    try:
        chat_id = d["chat_id"]
        fmt = bool(d.get("formatar"))
        if d["msg_type"] == "text":
            telegram_api.send_text(chat_id, d["text"] or "", parse_html=fmt)
        elif d["msg_type"] == "photo":
            telegram_api.send_photo(chat_id, d["media_path"], d["text"], parse_html=fmt)
        elif d["msg_type"] == "video":
            telegram_api.send_video(chat_id, d["media_path"], d["text"], parse_html=fmt)
        else:
            raise ValueError(f"tipo desconhecido: {d['msg_type']}")

        now = datetime.now(TZ).isoformat(timespec="seconds")
        # 'once' vira 'sent'; recorrentes continuam 'active' aguardando o proximo.
        new_status = "sent" if d["repeat"] == "once" else "active"
        db.update_dispatch(dispatch_id, status=new_status, sent_at=now, error=None)
    except Exception as exc:
        db.update_dispatch(dispatch_id, status="error", error=str(exc))
