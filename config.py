"""Configuracoes centrais lidas do arquivo .env."""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

# Carrega o .env que fica ao lado deste arquivo (idempotente).
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TIMEZONE = os.environ.get("TIMEZONE", "America/Sao_Paulo").strip()
PORT = int(os.environ.get("PORT", "5000"))

# Conta de administrador inicial (criada automaticamente no primeiro start).
ADMIN_USER = os.environ.get("ADMIN_USER", "admin").strip()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin").strip()

# Chave usada para assinar a sessao de login. Se nao vier do .env, geramos uma
# e guardamos num arquivo local para manter os logins validos entre reinicios.
SECRET_KEY = os.environ.get("SECRET_KEY", "").strip()
if not SECRET_KEY:
    _secret_file = BASE_DIR / ".secret"
    if _secret_file.exists():
        SECRET_KEY = _secret_file.read_text(encoding="utf-8").strip()
    else:
        SECRET_KEY = secrets.token_hex(32)
        _secret_file.write_text(SECRET_KEY, encoding="utf-8")

# Pastas de dados
UPLOAD_DIR = BASE_DIR / "uploads"
DB_PATH = BASE_DIR / "data.db"
JOBS_DB_URL = f"sqlite:///{(BASE_DIR / 'jobs.sqlite').as_posix()}"

UPLOAD_DIR.mkdir(exist_ok=True)

# Extensoes aceitas por tipo de midia
ALLOWED_IMAGE = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_VIDEO = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
