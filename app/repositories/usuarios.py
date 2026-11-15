from __future__ import annotations

from . import Repositorio

CAMPOS_PUBLICOS = "id, nombre, correo, rol, activo, creado_en"


class UsuarioRepositorio(Repositorio):
    tabla = "usuario"
    columnas_editables = ("rol", "activo")

    def por_correo(self, correo: str):
        return self.db.uno("SELECT * FROM usuario WHERE correo = ?", (correo,))

    def por_id(self, id_: int):
        return self.db.uno(f"SELECT {CAMPOS_PUBLICOS} FROM usuario WHERE id = ?", (id_,))

    def listar(self):
        return self.db.todos(f"SELECT {CAMPOS_PUBLICOS} FROM usuario ORDER BY nombre")

    def crear(self, nombre: str, correo: str, contrasena_hash: str, rol: str) -> int:
        return self.db.insertar(
            "INSERT INTO usuario (nombre, correo, contrasena_hash, rol) VALUES (?, ?, ?, ?)",
            (nombre, correo, contrasena_hash, rol),
        )

    def contar_administradores_activos(self) -> int:
        return self.db.valor(
            "SELECT COUNT(*) AS n FROM usuario WHERE rol = 'ADMINISTRADOR' AND activo = ?", (True,)
        )

    def revocar_token(self, jti: str, expira_en: str):
        self.db.ejecutar("INSERT INTO token_revocado (jti, expira_en) VALUES (?, ?)", (jti, expira_en))
        # Limpieza de tokens que ya vencieron
        self.db.ejecutar("DELETE FROM token_revocado WHERE expira_en < CURRENT_TIMESTAMP")
