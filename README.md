# NGL English Assistant 

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![Playwright](https://img.shields.io/badge/automation-Playwright-45ba4b.svg)](https://playwright.dev/)
[![Gemini](https://img.shields.io/badge/AI-Google%20Gemini-8E75C2.svg)](https://aistudio.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Un asistente inteligente y autónomo diseñado para analizar, resolver y verificar ejercicios y exámenes de inglés en la plataforma **National Geographic Learning (NGL / Avallain)** (`learn.eltngl.com`).

Se conecta a tu sesión activa de Google Chrome mediante el protocolo **Chrome DevTools (CDP)** sin almacenar credenciales de usuario. Extrae el contexto interactivo (textos, audios, imágenes y modelos de datos MVC de la plataforma), resuelve mediante modelos de **Google Gemini** y completa los ejercicios garantizando máxima precisión.

---

## Características Principales

* **Modo Autónomo en Cadena:** Resuelve continuamente ejercicio tras ejercicio dentro de asignaciones completas o exámenes multi-pantalla (Unit Tests de 25 pantallas), verificando la finalización y avanzando automáticamente.
* **Modo Asistido Seguro (Sin Enviar):** Resuelve y rellena las respuestas en el formulario de Chrome para que puedas revisarlas antes de enviar manualmente.
* **Soporte de Ejercicios de Pronunciación (Speaking):**
  * Reproduce el audio de la pregunta para que el estudiante escuche el diálogo/enunciado.
  * Selecciona de forma exacta la opción correcta en el modelo MVC interno de Avallain y en el DOM.
  * Emite voz en inglés sintetizada de forma nativa a través de **VB-Audio Virtual Cable**, permitiendo que Chrome capture el audio real a través del micrófono.
* **Resolución Multimodal con Gemini:** Combina transcripciones, audio MP3, capturas de pantalla y texto DOM estructurado para un análisis contextual preciso.
* **Parada de Seguridad Inteligente:** Si la confianza de la IA es inferior al umbral configurado o se detecta un comportamiento inesperado, la ejecución se pausa de inmediato.

---

## Tipos de Ejercicios Soportados

| Tipo de Ejercicio | Identificador | Descripción |
|---|---|---|
| **Fill in the Blanks** | `FILL_BLANK` | Rellenar huecos y cajas de texto (`input.textGapItem__input`). |
| **Multiple Choice** | `MULTIPLE_CHOICE` | Opción múltiple con radio buttons o casillas (`choice_interaction`). |
| **Drag & Drop** | `DRAG_AND_DROP` | Fichas de palabras arrastrables a huecos (`om-text-gap__target-item`). |
| **Dropdown Menus** | `DROPDOWN` | Selección de opciones en menús desplegables (`listbox`). |
| **Sorting** | `SORTING` | Clasificación de fichas en columnas y categorías (`osSorting`). |
| **Sentence & Word Reordering** | `REORDERING` | Ordenar palabras horizontalmente u oraciones completas verticalmente. |
| **Text Highlighting** | `HIGHLIGHTING` | Resaltado de frases clave o errores gramaticales (`imMarking`). |
| **Audio & Text Matching** | `MATCHING` | Unir con líneas interactivas audios o textos de columnas izquierda/derecha. |
| **Speaking & Voice Recording** | `SPEAKING` | Escuchar la pregunta, seleccionar la respuesta y pronunciar por micrófono virtual. |
| **Presentation / Study** | `PRESENTATION` | Reproducción y avance de pantallas de lectura o estudio. |

---

## Requisitos Previos

1. **Python 3.10 o superior**.
2. **Google Chrome** instalado.
3. **Clave de API gratuita de Google Gemini** (obtenible en [Google AI Studio](https://aistudio.google.com/)).
4. *(Opcional para Speaking)* **VB-Audio Virtual Cable** para transmitir audio al micrófono del navegador (descargable gratis en [vb-audio.com/Cable](https://vb-audio.com/Cable/)).

---

## Inicio Rápido en 1 Clic / 1 Comando (Recomendado)

¡No necesitas configurar nada manualmente! El proyecto incluye un **lanzador maestro interactivo** que automatiza todo el proceso:

* **En Windows (Doble Clic):** Ejecuta el archivo [`start.bat`](start.bat) o corre en consola:
  ```powershell
  python run.py
  ```
* **En Linux / macOS:** Ejecuta [`start.sh`](start.sh) o corre en terminal:
  ```bash
  chmod +x start.sh
  ./start.sh
  ```

### ¿Qué hace el script automáticamente por ti?
1. **Entorno Virtual:** Detecta o crea `.venv` y activa el intérprete aislado.
2. **Dependencias:** Instala automáticamente `requirements.txt` y configura Playwright.
3. **Configuración `.env`:** Si no existe, crea `.env` y te solicita amigablemente tu clave de Gemini por consola si aún no la tienes.
4. **Menú de Navegadores No Invasivo:** Te muestra qué navegadores tienes instalados en tu PC (Google Chrome, Brave, Opera GX, Microsoft Edge, etc.), te permite elegir cuál usar y te pregunta con respeto si deseas que lo abra automáticamente o si prefieres continuar manualmente.
5. **Interfaz Streamlit:** Inicia el servidor web y abre la aplicación en `http://localhost:8501`.

---

## Instalación Manual Paso a Paso (Opcional)

Si prefieres realizar la instalación de forma tradicional paso a paso:

### 1. Clonar el repositorio
```bash
git clone https://github.com/Taborda004/NGL-English.git
cd NGL-English
```

### 2. Crear y activar el entorno virtual
En Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\activate
```
En Linux / macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Configurar variables de entorno
Copia la plantilla `.env.example` para crear tu archivo `.env`:
```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```
Edita `.env` e introduce tu clave gratuita de Gemini:
```env
GEMINI_API_KEY=AIzaSy...tu_clave_aqui...
CHROME_DEBUGGING_PORT=9222
```

> **Aviso de Seguridad:** Tu archivo `.env` nunca debe subirse al repositorio. Ya está incluido en `.gitignore`.

---

## Compatibilidad de Navegadores (Brave, Opera, Edge, Chrome)

El asistente se comunica mediante el protocolo estándar **Chrome DevTools Protocol (CDP)** en el puerto `9222`, lo que significa que es **100% compatible con cualquier navegador basado en Chromium**:
* **Brave Browser**
* **Opera / Opera GX**
* **Microsoft Edge** *(preinstalado en cualquier Windows)*
* **Google Chrome**
* **Vivaldi / Arc**

El lanzador [`run.py`](run.py) lo detecta y abre de forma automática. Si deseas iniciarlo manualmente o forzar tu navegador favorito:

#### Comando con el Lanzador Maestro:
```powershell
python run.py --browser brave     # Forzar Brave
python run.py --browser opera     # Forzar Opera / Opera GX
python run.py --browser edge      # Forzar Microsoft Edge
python run.py --browser chrome    # Forzar Google Chrome
```

#### Comandos Manuales de Inicio por Navegador:

* ** Brave Browser:**
  ```cmd
  "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" --remote-debugging-port=9222 --user-data-dir="C:\brave-dev-profile"
  ```

* ** Opera GX:**
  ```cmd
  "%LOCALAPPDATA%\Programs\Opera GX\launcher.exe" --remote-debugging-port=9222 --user-data-dir="C:\opera-dev-profile"
  ```

* ** Opera Estándar:**
  ```cmd
  "%LOCALAPPDATA%\Programs\Opera\launcher.exe" --remote-debugging-port=9222 --user-data-dir="C:\opera-dev-profile"
  ```

* ** Microsoft Edge:**
  ```cmd
  "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --user-data-dir="C:\edge-dev-profile"
  ```

* ** Google Chrome:**
  ```cmd
  "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome-dev-profile"
  ```

* ** macOS (Brave, Opera o Chrome):**
  ```bash
  /Applications/Brave\ Browser.app/Contents/MacOS/Brave\ Browser --remote-debugging-port=9222 --user-data-dir="/tmp/brave-dev-profile"
  ```

* ** Linux:**
  ```bash
  brave-browser --remote-debugging-port=9222 --user-data-dir="/tmp/brave-dev-profile"
  ```

### Paso 2: Iniciar sesión en National Geographic Learning
En la ventana especial de Chrome que se acaba de abrir:
1. Dirígete a [learn.eltngl.com](https://learn.eltngl.com).
2. Inicia sesión con tus credenciales habituales.
3. Abre la asignación, unidad o examen que deseas resolver.

### Paso 3: Iniciar la Interfaz Web
En tu terminal con el entorno virtual activado:
```bash
streamlit run app.py
```
Abre en tu navegador la dirección indicada (por defecto: `http://localhost:8501`).

### Paso 4: Conectar y Resolver
1. En la barra lateral de la aplicación, haz clic en **"Conectar Navegador"**. Verás el estado en verde `● Browser connected`.
2. Selecciona tu modalidad de trabajo:
   * **Modo Asistido Seguro:** Analiza y rellena la pantalla actual sin enviar nada, permitiéndote comprobar cada respuesta.
   * **Modo Autónomo en Cadena:** Automatiza la resolución continua hasta el final de la actividad o examen.

---

## Configuración de Audio para Ejercicios de Speaking

Para que el asistente pueda responder autónomamente ejercicios de pronunciación en Chrome:

1. Instala el controlador gratuito [VB-Audio Virtual Cable](https://vb-audio.com/Cable/).
2. En la configuración de Windows (o de tu sistema operativo), selecciona **CABLE Input** como salida de audio predeterminada o dispositivo de reproducción secundario.
3. En Google Chrome:
   * Ve a `Configuración > Privacidad y seguridad > Configuración de sitios > Micrófono`.
   * Selecciona **CABLE Output (VB-Audio Virtual Cable)** como el micrófono predeterminado.
4. Cuando el asistente resuelva una pregunta de Speaking:
   * Reproducirá el audio del enunciado para escuchar la pregunta.
   * Seleccionará la opción correcta en la plataforma.
   * Presionará el botón de grabación en Chrome y reproducirá la respuesta sintetizada directamente al micrófono virtual.

---

## Pruebas Automatizadas

El proyecto cuenta con una suite completa de pruebas unitarias y de integración que validan el analizador, el detector de tipos de ejercicio, el runner de automatización y el resolvedor:

```bash
python -m pytest tests/
```

---

## Estructura del Proyecto

```text
NGL-English-Assistant/
├── ai/                     # Integración con Google Gemini y prompts especializados
│   ├── prompts.py          # Plantillas de prompts y directrices pedagógicas
│   └── solver.py           # Resolvedor multimodal (texto, imagen, audio)
├── analyzer/               # Extracción e inspección del DOM
│   ├── content_extractor.py # Extractor de textos, audios y capturas
│   ├── exercise_detector.py # Clasificador heurístico del tipo de ejercicio
│   └── parser.py           # Parser de respuestas generadas
├── automation/             # Motor de ejecución en cadena
│   └── chain_runner.py     # Orquestador del flujo continuo y navegación multi-pantalla
├── browser/                # Conexión CDP con Google Chrome
│   └── browser_manager.py  # Gestor de conexiones y contextos de Playwright
├── config/                 # Configuración del sistema y variables de entorno
│   └── settings.py
├── history/                # Gestor de historial de sesiones
│   └── history_manager.py
├── interaction/            # Manipulación del DOM y modelos MVC
│   ├── form_filler.py      # Inyección y selección en modelos de Avallain
│   └── speech_player.py    # Emisión de voz sintetizada por cable virtual
├── tests/                  # Suite de pruebas unitarias (Pytest)
├── app.py                  # Interfaz gráfica principal (Streamlit)
├── requirements.txt        # Dependencias del proyecto
├── .env.example            # Plantilla de variables de entorno
└── .gitignore              # Protección contra subida de credenciales y archivos temporales
```

---

## Privacidad y Seguridad

* **Sin credenciales almacenadas:** Este software nunca solicita, guarda ni transmite tus datos de usuario o contraseñas. La autenticación ocurre exclusivamente dentro de tu navegador Google Chrome habitual.
* **Procesamiento Local:** La comunicación entre Playwright y Chrome se produce a través de sockets locales (`localhost:9222`).
* **Uso Exclusivo para Respuestas:** Únicamente se envían a la API de Gemini los enunciados de los ejercicios activos para formular las respuestas.

---

## Licencia y Descargo de Responsabilidad

Este proyecto se distribuye bajo la Licencia MIT. Desarrollado con fines educativos y de investigación sobre automatización web e inteligencia artificial multimodal. El uso de esta herramienta queda bajo la responsabilidad exclusiva del usuario final.
