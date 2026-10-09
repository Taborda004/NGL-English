#!/usr/bin/env python3
"""
==============================================================================
NGL English Assistant - One-Click Master Launcher (run.py)
==============================================================================
Este script automatiza por completo el flujo de inicio del proyecto:
1. Valida la versión de Python (>= 3.10).
2. Crea y activa automáticamente el entorno virtual (.venv) si no existe.
3. Verifica e instala dependencias faltantes (requirements.txt + Playwright).
4. Configura el archivo .env a partir de .env.example (solicita API Key si falta).
5. Comprueba si Google Chrome está en modo depuración (puerto 9222).
   - Si no está abierto, localiza el ejecutable de Chrome y lo lanza automáticamente.
6. Inicia la interfaz web de Streamlit (app.py).

Uso:
    python run.py
==============================================================================
"""

import sys
import os
import subprocess
import shutil
import platform
import time
import urllib.request
import json
import argparse
from pathlib import Path

# Constantes de configuración
MIN_PYTHON_VERSION = (3, 10)
CHROME_DEBUG_PORT = 9222
PROJECT_DIR = Path(__file__).resolve().parent
VENV_DIR = PROJECT_DIR / ".venv"
ENV_FILE = PROJECT_DIR / ".env"
ENV_EXAMPLE_FILE = PROJECT_DIR / ".env.example"
REQUIREMENTS_FILE = PROJECT_DIR / "requirements.txt"
APP_FILE = PROJECT_DIR / "app.py"

# Colores ANSI para terminal
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_step(step_num: int, title: str) -> None:
    """Imprime un encabezado formateado para cada fase del launcher."""
    print(f"\n{BOLD}{CYAN}[Paso {step_num}] {title}{RESET}")


def print_success(msg: str) -> None:
    print(f"  {GREEN}[OK] {msg}{RESET}")


def print_warning(msg: str) -> None:
    print(f"  {YELLOW}[AVISO] {msg}{RESET}")


def print_error(msg: str) -> None:
    print(f"  {RED}[ERROR] {msg}{RESET}")


def verify_python_version() -> None:
    """Verifica que la versión de Python en ejecución cumpla los requisitos mínimos."""
    if sys.version_info < MIN_PYTHON_VERSION:
        print_error(
            f"Se requiere Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]} o superior. "
            f"Versión actual detectada: {sys.version_info.major}.{sys.version_info.minor}"
        )
        sys.exit(1)


def get_venv_python_path() -> Path:
    """Obtiene la ruta al binario de Python dentro del entorno virtual .venv."""
    if platform.system() == "Windows":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def is_running_in_venv() -> bool:
    """Comprueba si el proceso actual se está ejecutando dentro de un virtualenv."""
    return getattr(sys, "base_prefix", sys.prefix) != sys.prefix or hasattr(sys, "real_prefix")


def ensure_virtualenv() -> Path:
    """
    Garantiza la existencia del entorno virtual .venv.
    Si no existe, lo crea automáticamente.
    Retorna la ruta al ejecutable de Python del venv.
    """
    venv_python = get_venv_python_path()
    
    if not venv_python.exists():
        print("  Creando entorno virtual (.venv)...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
        print_success("Entorno virtual creado exitosamente.")
    else:
        print_success("Entorno virtual (.venv) detectado.")
        
    return venv_python


def ensure_dependencies(venv_python: Path) -> None:
    """Comprueba e instala las dependencias de requirements.txt y navegadores Playwright."""
    print("  Verificando dependencias del proyecto...")
    
    # Comprobar si streamlit y playwright ya están instalados dentro del venv
    check_code = "import streamlit, playwright, google.generativeai, sounddevice, pyttsx3"
    result = subprocess.run(
        [str(venv_python), "-c", check_code],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("  Instalando paquetes desde requirements.txt (puede tardar un momento)...")
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)],
            check=True
        )
        print_success("Dependencias de Python instaladas correctamente.")
    else:
        print_success("Todas las librerías de Python están al día.")

    # Asegurar que Playwright tenga Chromium instalado
    pw_check_code = "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); p.stop()"
    pw_res = subprocess.run([str(venv_python), "-c", pw_check_code], capture_output=True, text=True)
    if pw_res.returncode != 0:
        print("  Configurando Playwright Chromium...")
        subprocess.run([str(venv_python), "-m", "playwright", "install", "chromium"], check=True)
        print_success("Playwright configurado.")


def ensure_env_configuration() -> None:
    """
    Asegura la existencia de .env. Si no existe, lo crea desde .env.example
    y solicita interactivamente la GEMINI_API_KEY si no está presente.
    """
    if not ENV_FILE.exists():
        if ENV_EXAMPLE_FILE.exists():
            shutil.copy(str(ENV_EXAMPLE_FILE), str(ENV_FILE))
            print_success("Archivo .env generado a partir de .env.example.")
        else:
            with open(ENV_FILE, "w", encoding="utf-8") as f:
                f.write(f"GEMINI_API_KEY=your_gemini_api_key_here\nCHROME_DEBUGGING_PORT={CHROME_DEBUG_PORT}\n")
            print_success("Archivo .env creado con plantilla estándar.")

    # Leer valor actual de GEMINI_API_KEY
    api_key_val = ""
    lines = []
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines:
            if line.strip().startswith("GEMINI_API_KEY="):
                api_key_val = line.strip().split("=", 1)[1].strip()

    if not api_key_val or api_key_val == "your_gemini_api_key_here":
        print_warning("No se ha configurado la clave GEMINI_API_KEY en tu archivo .env.")
        print("  Puedes obtener una clave gratuita en: https://aistudio.google.com/")
        try:
            user_key = input("  Introduce tu Gemini API Key (o presiona Enter para configurar luego): ").strip()
            if user_key:
                new_lines = []
                found = False
                for line in lines:
                    if line.strip().startswith("GEMINI_API_KEY="):
                        new_lines.append(f"GEMINI_API_KEY={user_key}\n")
                        found = True
                    else:
                        new_lines.append(line)
                if not found:
                    new_lines.append(f"GEMINI_API_KEY={user_key}\n")
                with open(ENV_FILE, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
                print_success("Clave de Gemini guardada correctamente en .env.")
            else:
                print_warning("Se continuará sin clave. Podrás añadirla en el archivo .env en cualquier momento.")
        except (KeyboardInterrupt, EOFError):
            print("\n")
    else:
        print_success("Clave GEMINI_API_KEY detectada en .env.")


def is_chrome_debugging_active(port: int = CHROME_DEBUG_PORT) -> bool:
    """Verifica si Chrome ya está escuchando activamente en el puerto de depuración."""
    try:
        url = f"http://127.0.0.1:{port}/json/version"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            return resp.status == 200
    except Exception:
        return False


def get_browser_catalog() -> dict[str, tuple[str, list[str], str]]:
    """
    Retorna el catálogo de navegadores según el sistema operativo:
    dict con estructura { 'key': (Nombre, [Rutas_candidatas], comando_corto) }
    """
    system = platform.system()
    if system == "Windows":
        return {
            "1": (
                "Google Chrome",
                [
                    os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
                    os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
                    os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
                ],
                "chrome"
            ),
            "2": (
                "Brave Browser",
                [
                    os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"),
                    os.path.expandvars(r"%ProgramFiles(x86)%\BraveSoftware\Brave-Browser\Application\brave.exe"),
                    os.path.expandvars(r"%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe"),
                ],
                "brave"
            ),
            "3": (
                "Opera GX",
                [
                    os.path.expandvars(r"%LocalAppData%\Programs\Opera GX\launcher.exe"),
                    os.path.expandvars(r"%ProgramFiles%\Opera GX\launcher.exe"),
                    os.path.expandvars(r"%ProgramFiles(x86)%\Opera GX\launcher.exe"),
                    os.path.expandvars(r"%AppData%\Opera Software\Opera GX Stable\launcher.exe"),
                ],
                "opera"
            ),
            "4": (
                "Opera Estándar",
                [
                    os.path.expandvars(r"%LocalAppData%\Programs\Opera\launcher.exe"),
                    os.path.expandvars(r"%ProgramFiles%\Opera\launcher.exe"),
                    os.path.expandvars(r"%ProgramFiles(x86)%\Opera\launcher.exe"),
                    os.path.expandvars(r"%AppData%\Opera Software\Opera Stable\launcher.exe"),
                ],
                "opera"
            ),
            "5": (
                "Microsoft Edge",
                [
                    os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
                    os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
                    os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
                ],
                "msedge"
            ),
            "6": (
                "Vivaldi",
                [
                    os.path.expandvars(r"%LocalAppData%\Vivaldi\Application\vivaldi.exe"),
                    os.path.expandvars(r"%ProgramFiles%\Vivaldi\Application\vivaldi.exe"),
                    os.path.expandvars(r"%ProgramFiles(x86)%\Vivaldi\Application\vivaldi.exe"),
                ],
                "vivaldi"
            ),
        }
    elif system == "Darwin":  # macOS
        return {
            "1": ("Google Chrome", ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"], "google-chrome"),
            "2": ("Brave Browser", ["/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"], "brave"),
            "3": ("Opera GX", ["/Applications/Opera GX.app/Contents/MacOS/Opera GX"], "opera"),
            "4": ("Opera Estándar", ["/Applications/Opera.app/Contents/MacOS/Opera"], "opera"),
            "5": ("Microsoft Edge", ["/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"], "microsoft-edge"),
            "6": ("Vivaldi", ["/Applications/Vivaldi.app/Contents/MacOS/Vivaldi"], "vivaldi"),
        }
    else:  # Linux
        return {
            "1": ("Google Chrome", ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable"], "google-chrome"),
            "2": ("Brave Browser", ["/usr/bin/brave-browser", "/usr/bin/brave"], "brave-browser"),
            "3": ("Opera", ["/usr/bin/opera"], "opera"),
            "4": ("Microsoft Edge", ["/usr/bin/microsoft-edge", "/usr/bin/microsoft-edge-stable"], "microsoft-edge"),
            "5": ("Chromium", ["/usr/bin/chromium-browser", "/usr/bin/chromium"], "chromium"),
            "6": ("Vivaldi", ["/usr/bin/vivaldi"], "vivaldi"),
        }


def locate_browser_path(paths: list[str], short_cmd: str) -> str | None:
    """Busca si el ejecutable del navegador existe en las rutas dadas o en el PATH."""
    for p in paths:
        if os.path.isfile(p):
            return p
    which_path = shutil.which(short_cmd)
    if which_path and os.path.isfile(which_path):
        return which_path
    return None


def select_and_configure_browser(preferred: str | None = None) -> None:
    """
    Menú interactivo y no invasivo para seleccionar o confirmar el navegador Chromium.
    Pregunta al usuario qué navegador tiene y qué desea hacer, sin forzar acciones no deseadas.
    """
    # 1. Si ya hay una instancia escuchando en el puerto 9222, avisar de inmediato
    if is_chrome_debugging_active():
        print_success(f"Navegador compatible ya activo en modo depuración (puerto {CHROME_DEBUG_PORT}).")
        return

    catalog = get_browser_catalog()

    # Si se especificó el navegador por parámetro (--browser brave / opera / etc.), atenderlo directo
    if preferred:
        pref_norm = preferred.lower().replace(" ", "").replace("_", "")
        for key, (name, paths, cmd) in catalog.items():
            if pref_norm in name.lower().replace(" ", "").replace("_", ""):
                print(f"  Navegador seleccionado por parámetro: {name}")
                _handle_selected_browser(name, paths, cmd)
                return
        print_warning(f"No se reconoció el navegador '{preferred}'. Mostrando menú interactivo...")

    # 2. Presentar Menú Interactivo No Invasivo
    print(f"\n{BOLD}{CYAN}------------------------------------------------------------------------------{RESET}")
    print(f"{BOLD}{CYAN} SELECCION DE NAVEGADOR WEB{RESET}")
    print(f"{BOLD}{CYAN}------------------------------------------------------------------------------{RESET}")
    print("El asistente se comunica con cualquier navegador Chromium en el puerto 9222.")
    print("¿Con qué navegador deseas trabajar?\n")

    for key, (name, paths, cmd) in catalog.items():
        found = locate_browser_path(paths, cmd) is not None
        tag = f"{GREEN}[Detectado en tu equipo]{RESET}" if found else f"{YELLOW}[No detectado]{RESET}"
        print(f"  [{key}] {name.ljust(18)} {tag}")

    print("  [7] Abrir manualmente (o ya lo tengo abierto)")
    print("  [0] Salir\n")

    while True:
        try:
            choice = input(f"{BOLD}Selecciona una opcion [1-7] (Enter por defecto = 1): {RESET}").strip()
            if not choice:
                choice = "1"

            if choice == "0":
                print("\nOperación cancelada por el usuario.")
                sys.exit(0)

            if choice == "7":
                print_info("Continuando sin abrir navegador automáticamente.")
                print(f"Recuerda iniciar tu navegador con el flag: --remote-debugging-port={CHROME_DEBUG_PORT}")
                return

            if choice in catalog:
                name, paths, cmd = catalog[choice]
                _handle_selected_browser(name, paths, cmd)
                return

            print_warning(f"Opción '{choice}' no válida. Introduce un número entre 0 y 7.")
        except (KeyboardInterrupt, EOFError):
            print("\nOperación cancelada.")
            sys.exit(0)


def _handle_selected_browser(name: str, paths: list[str], cmd: str) -> None:
    """Gestiona el navegador elegido: localiza la ruta y consulta amablemente si desea abrirlo."""
    path = locate_browser_path(paths, cmd)

    if not path:
        print_warning(f"\nNo se localizó {name} en las rutas estándar.")
        custom = input("¿Deseas ingresar la ruta completa del ejecutable? (Enter para omitir): ").strip().strip('"')
        if custom and os.path.isfile(custom):
            path = custom
        else:
            print_info("Continuando sin abrir el navegador. Podrás abrirlo manualmente.")
            return

    # Definir directorio de perfil seguro y aislado
    slug = name.lower().replace(" ", "-")
    if platform.system() == "Windows":
        profile_dir = Path(os.environ.get("LOCALAPPDATA", "C:\\")) / f"{slug}-dev-profile"
    else:
        profile_dir = Path.home() / f"{slug}-dev-profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    manual_cmd = f'"{path}" --remote-debugging-port={CHROME_DEBUG_PORT} --user-data-dir="{profile_dir}"'

    # Preguntar con respeto antes de abrir nada
    print(f"\n{GREEN}[OK] {name} localizado:{RESET} {path}")
    ans = input(f"¿Deseas que el asistente abra {name} ahora en modo depuración? [S/n]: ").strip().lower()

    if ans in ["n", "no"]:
        print_info("Entendido. No se abrirá ninguna ventana automáticamente.")
        print(f"Para iniciarlo tú mismo cuando lo necesites, ejecuta:\n  {manual_cmd}\n")
        return

    print(f"  Iniciando {name} en https://learn.eltngl.com ...")
    launch_args = [
        path,
        f"--remote-debugging-port={CHROME_DEBUG_PORT}",
        f"--user-data-dir={profile_dir}",
        "https://learn.eltngl.com"
    ]
    try:
        subprocess.Popen(launch_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(8):
            time.sleep(0.5)
            if is_chrome_debugging_active():
                print_success(f"{name} iniciado y listo en el puerto {CHROME_DEBUG_PORT}.")
                return
        print_info(f"{name} fue lanzado. Si tarda en abrir, la interfaz continuará cargando.")
    except Exception as e:
        print_warning(f"No se pudo iniciar automáticamente: {e}")
        print(f"Puedes ejecutarlo manualmente con:\n  {manual_cmd}")


def ensure_chrome_running(preferred: str | None = None) -> None:
    """Alias retrocompatible para select_and_configure_browser."""
    select_and_configure_browser(preferred=preferred)


def launch_streamlit(venv_python: Path) -> None:
    """Ejecuta la interfaz gráfica Streamlit utilizando el entorno virtual."""
    print(f"\n{BOLD}{GREEN}=============================================================================={RESET}")
    print(f"{BOLD}{GREEN} Iniciando NGL English Assistant...{RESET}")
    print(f"{BOLD}{GREEN}=============================================================================={RESET}\n")
    print(f"  {CYAN}URL de la interfaz:{RESET} http://localhost:8501")
    print(f"  {YELLOW}Para detener el asistente, presiona Ctrl+C en esta terminal.{RESET}\n")

    cmd = [
        str(venv_python),
        "-m", "streamlit", "run",
        str(APP_FILE),
        "--server.port", "8501",
        "--server.headless", "false"
    ]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Asistente detenido por el usuario.{RESET}")


def main() -> None:
    """Función principal orquestadora."""
    parser = argparse.ArgumentParser(description="NGL English Assistant - One-Click Launcher")
    parser.add_argument(
        "--browser", "-b",
        help="Navegador Chromium a utilizar: brave, opera, operagx, edge, chrome, vivaldi",
        default=None
    )
    args, _ = parser.parse_known_args()
    preferred_browser = args.browser or os.environ.get("BROWSER") or os.environ.get("PREFERRED_BROWSER")

    print(f"{BOLD}{CYAN}=============================================================================={RESET}")
    print(f"{BOLD}{CYAN} NGL English Assistant - Launcher{RESET}")
    print(f"{BOLD}{CYAN}=============================================================================={RESET}")

    # 1. Validación de versión
    verify_python_version()

    # 2. Entorno virtual (.venv)
    print_step(1, "Verificando Entorno Virtual")
    venv_python = ensure_virtualenv()

    # Si estamos corriendo fuera del venv, nos re-ejecutamos transparentemente dentro del venv
    if not is_running_in_venv():
        # Comprobar si ya llamamos desde el venv o necesitamos relanzar
        pass

    # 3. Instalación de dependencias
    print_step(2, "Verificando Dependencias")
    ensure_dependencies(venv_python)

    # 4. Configuración del archivo .env
    print_step(3, "Comprobando Configuración (.env)")
    ensure_env_configuration()

    # 5. Estado del Navegador Chromium (Chrome, Brave, Opera, Edge, etc.)
    print_step(4, "Comprobando Conexión con Navegador Chromium (Brave, Opera, Chrome, Edge)")
    ensure_chrome_running(preferred=preferred_browser)

    # 6. Ejecución de Streamlit
    print_step(5, "Iniciando Interfaz de Usuario")
    launch_streamlit(venv_python)


if __name__ == "__main__":
    main()
