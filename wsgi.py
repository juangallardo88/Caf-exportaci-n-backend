"""Punto de entrada: `gunicorn wsgi:app` (Render) o `flask --app wsgi run` (local)."""
from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402

app = create_app()
