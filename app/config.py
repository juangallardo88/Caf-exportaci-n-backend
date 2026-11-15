"""Configuración leída de variables de entorno."""
import os


class Config:
    ENTORNO = os.getenv("ENTORNO", "desarrollo")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///instance/desarrollo.db")
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    JWT_HORAS = int(os.getenv("JWT_HORAS", "8"))
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
    # Método de hash de contraseñas (werkzeug). En pruebas se usan menos iteraciones.
    HASH_METHOD = os.getenv("HASH_METHOD", "pbkdf2:sha256")
    TESTING = False

    @classmethod
    def validar(cls):
        if cls.ENTORNO == "produccion":
            if len(cls.SECRET_KEY) < 32:
                raise RuntimeError("SECRET_KEY debe tener al menos 32 caracteres en producción")
            if cls.DATABASE_URL.startswith("sqlite"):
                raise RuntimeError("En producción DATABASE_URL debe apuntar a PostgreSQL (Neon)")
            if "*" in cls.CORS_ORIGINS:
                raise RuntimeError("En producción CORS_ORIGINS debe listar el dominio del frontend")
        elif not cls.SECRET_KEY:
            cls.SECRET_KEY = "clave-solo-para-desarrollo-local-no-usar-en-produccion"
