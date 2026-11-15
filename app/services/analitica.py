"""Dashboard (HU-27), estadísticas (HU-28), búsqueda (HU-29) y reportes CSV (HU-30)."""
from __future__ import annotations

import csv
import io

from ..domain.reglas import estado_stock
from ..errors import ErrorApp
from ..repositories.analitica import AnaliticaRepositorio
from ..repositories.exportaciones import ExportacionRepositorio
from ..repositories.productos import InventarioRepositorio

ESTADOS = ("BORRADOR", "CONFIRMADA", "EN_TRANSITO", "ENTREGADA", "CANCELADA")


def dashboard() -> dict:
    repo = AnaliticaRepositorio()
    conteo = {fila["estado"]: fila["cantidad"] for fila in repo.conteo_por_estado()}
    inventario = repo.resumen_inventario()
    return {
        "exportaciones": {
            "total": sum(conteo.values()),
            "activas": conteo.get("CONFIRMADA", 0) + conteo.get("EN_TRANSITO", 0),
            "por_estado": {estado: conteo.get(estado, 0) for estado in ESTADOS},
            "valor_exportado": round(repo.valor_exportado(), 2),
        },
        "inventario": {
            "productos": inventario["productos"],
            "unidades": inventario["unidades"],
            "valor": round(inventario["valor"], 2),
            "bajo_stock": inventario["bajo_stock"],
        },
        "clientes": repo.contar("cliente"),
        "proveedores": repo.contar("proveedor"),
        "ultimas_exportaciones": repo.ultimas_exportaciones(),
    }


def estadisticas() -> dict:
    repo = AnaliticaRepositorio()
    return {
        "por_mes": repo.por_mes(),
        "por_destino": repo.por_destino(),
        "top_productos": repo.top_productos(),
        "inventario_por_categoria": repo.inventario_por_categoria(),
    }


def buscar(q: str | None) -> dict:
    if not q or len(q.strip()) < 2:
        raise ErrorApp("Escribe al menos 2 caracteres para buscar")
    return AnaliticaRepositorio().buscar(q)


def _csv(encabezados: list[str], filas: list[list]) -> str:
    """CSV con ';' y BOM UTF-8 para que Excel en español lo abra con tildes y columnas."""
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";", lineterminator="\r\n")
    escritor.writerow(encabezados)
    escritor.writerows(filas)
    return "﻿" + salida.getvalue()


def _numero(valor: float) -> str:
    return f"{valor:.2f}".replace(".", ",")


def reporte_exportaciones(estado=None, desde=None, hasta=None) -> str:
    filas = [
        [e["consecutivo"], e["cliente"], e["pais_destino"], e["incoterm"], e["estado"],
         e["fecha_embarque"] or "", e["fecha_estimada_llegada"] or "",
         _numero(e["subtotal"]), _numero(e["impuestos"]), _numero(e["flete"]), _numero(e["total"])]
        for e in ExportacionRepositorio().listar(estado, desde, hasta)
    ]
    return _csv(["Consecutivo", "Cliente", "País destino", "Incoterm", "Estado", "Fecha embarque",
                 "Llegada estimada", "Subtotal (USD)", "Impuestos (USD)", "Flete (USD)", "Total (USD)"], filas)


def reporte_inventario() -> str:
    filas = [
        [i["sku"], i["nombre"], i["categoria"], i["cantidad"], i["stock_minimo"], i["ubicacion"],
         estado_stock(i["cantidad"], i["stock_minimo"])]
        for i in InventarioRepositorio().listar()
    ]
    return _csv(["SKU", "Producto", "Categoría", "Cantidad", "Stock mínimo", "Ubicación", "Estado"], filas)
