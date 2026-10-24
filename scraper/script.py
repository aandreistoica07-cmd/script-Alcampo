#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alcampo Scraper - Script de Pruebas y Extracción de Saldos (Restaurado y Optimizado)
Soporta la lectura directa de cualquier archivo Excel (.xlsx, .ods), CSV o JSON.
"""
import sys
import os
from pathlib import Path

# Activar codificación UTF-8 para consola Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Importar motor principal optimizado
try:
    from script_optimizado import main as run_optimizado
except ImportError:
    from scraper.script_optimizado import main as run_optimizado

if __name__ == "__main__":
    # Si se pasa la ruta de un Excel o JSON directamente (ej: python script.py mi_excel.xlsx)
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        excel_or_json_file = sys.argv[1]
        sys.argv = [sys.argv[0], "--input-file", excel_or_json_file] + sys.argv[2:]

    print("🚀 Ejecutando Script de Pruebas Alcampo (Motor Optimizado v2.0)...")
    run_optimizado()
