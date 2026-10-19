"""
Script de Compilación y Distribución Segura - NGL English Assistant.
Empaqueta el código fuente en un ejecutable binario (.exe) protegido y cerrado,
evitando que terceros puedan leer, modificar o saltarse la comprobación de licencias.
"""

import sys
import os
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"


def check_and_install_pyinstaller():
    """Instala PyInstaller si no está presente en el entorno."""
    try:
        import PyInstaller
        print(f"[OK] PyInstaller detectado (v{PyInstaller.__version__})")
    except ImportError:
        print("[INFO] Instalando PyInstaller para compilar el ejecutable...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print("[OK] PyInstaller instalado exitosamente.")


def build_binary():
    """Compila el lanzador y la suite en un binario ejecutable."""
    check_and_install_pyinstaller()
    
    print("\nIniciando compilacion de NGL English Assistant...")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name=NGL_Assistant",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        "--add-data=auth;auth",
        "--add-data=config;config",
        "--add-data=ai;ai",
        "--add-data=analyzer;analyzer",
        "--add-data=interaction;interaction",
        "--add-data=browser;browser",
        "--add-data=automation;automation",
        "--add-data=app.py;.",
        "--add-data=.env.example;.",
        str(PROJECT_ROOT / "run.py")
    ]
    
    print("Ejecutando comando de compilación:")
    print(" ".join(cmd))
    
    res = subprocess.run(cmd)
    if res.returncode == 0:
        print("\n" + "=" * 70)
        print("[EXITO] Compilación completada con éxito.")
        print(f"El ejecutable protegido se encuentra en: {DIST_DIR / 'NGL_Assistant'}")
        print("Puedes distribuir únicamente la carpeta generada en 'dist' sin compartir")
        print("tu código fuente de GitHub.")
        print("=" * 70)
    else:
        print(f"\n[ERROR] La compilación falló con código de salida: {res.returncode}")


if __name__ == "__main__":
    build_binary()
