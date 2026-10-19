# NGL English Assistant

Asistente inteligente y autonomo disenado para analizar, resolver y verificar ejercicios y examenes de ingles en la plataforma National Geographic Learning (NGL / Avallain) (`learn.eltngl.com`).

Se conecta a tu navegador habitual (Google Chrome, Brave, Opera GX o Edge) mediante el protocolo estandar Chrome DevTools (CDP). No almacena contrasenas de la plataforma, resuelve mediante modelos de Google Gemini y completa las actividades con alta precision.

---

## Guia Rapida: Como Clonar y Ejecutar en 3 Pasos

El proyecto cuenta con un sistema de auto-reproduccion completa. No necesitas crear entornos virtuales ni instalar paquetes manualmente.

### Paso 1: Clonar el repositorio
Abre una terminal o consola y ejecuta:
```bash
git clone https://github.com/Taborda004/NGL-English.git
cd NGL-English
```

### Paso 2: Iniciar el programa

* **En Windows (Doble Clic):**
  Haz doble clic en el archivo `start.bat` (o ejecuta en consola `python run.py`).

* **En macOS o Linux:**
  Abre la terminal en la carpeta del proyecto y ejecuta:
  ```bash
  ./start.sh
  ```
  *(O ejecuta directamente `python3 run.py`).*

El script automatizado se encargara de:
1. Crear el entorno virtual `.venv` aislado si no existe.
2. Instalar todas las dependencias necesarias de `requirements.txt`.
3. Configurar Playwright y el navegador de forma silenciosa.
4. Crear tu archivo de configuracion `.env`.
5. Iniciar la aplicacion web en tu navegador (`http://localhost:8501`).

### Paso 3: Solicitar Acceso (Solo la primera vez)
1. Al abrir la interfaz, ve a la pestana **"Solicitar Acceso (Nuevo Usuario)"**.
2. Escribe tu nombre completo y correo electronico.
3. Presiona **"Enviar Solicitud de Acceso"**.
4. Tu identificador unico de equipo (HWID) se enviara a la nube para que el propietario autorice tu dispositivo.

---

## Flujo del Administrador: Como Aprobar Usuarios desde el Celular

El autor o administrador (**Taborda004**) puede autorizar o revocar accesos en cualquier momento sin costo alguno:

1. **Abrir el panel movil en el celular:**
   Ingresa desde cualquier navegador (Safari o Chrome en tu telefono) a:
   [https://taborda004.github.io/NGL-English/](https://taborda004.github.io/NGL-English/)
2. **Identificate:**
   Introduce tu Clave Maestra de Administrador (tu telefono la recordara para proximas ocasiones).
3. **Aprobar en 1 Toque:**
   - En la seccion **Solicitudes Pendientes**, toca el boton verde **`[Aprobar Acceso (1-Clic)]`**.
   - O utiliza el menu desplegable de cada usuario para cambiar su estado a `Aprobado (Activo)`, `Pendiente` o `Revocado (Suspendido)`.
4. El usuario queda autorizado de inmediato para entrar en su aplicacion.

---

## Como Usar el Asistente con tus Tareas de NGL

Una vez autorizado el acceso:

1. **Abre tu asignacion:**
   En la ventana de Chrome que abrio el asistente, ve a [learn.eltngl.com](https://learn.eltngl.com), inicia sesion con tus credenciales de estudiante y abre la actividad o examen que deseas resolver.
2. **Conecta el asistente:**
   En la interfaz web del asistente (`http://localhost:8501`), haz clic en **"Conectar Navegador"**. Veras la confirmacion de conexion en la barra lateral.
3. **Elige tu modo de resolucion:**
   * **Modo Asistido Seguro (Revisar antes de enviar):** El asistente analiza la pantalla, selecciona las respuestas y rellena los campos, permitiendote revisarlas antes de enviar.
   * **Modo Autonomo en Cadena:** El asistente resuelve pantalla tras pantalla de forma continua y automatizada hasta terminar la actividad o el examen completo.

---

## Tipos de Ejercicios Soportados

| Tipo de Ejercicio | Identificador | Descripcion |
|---|---|---|
| Fill in the Blanks | `FILL_BLANK` | Rellenar huecos y cajas de texto (`input.textGapItem__input`). |
| Multiple Choice | `MULTIPLE_CHOICE` | Opcion multiple con radio buttons o casillas (`choice_interaction`). |
| Drag and Drop | `DRAG_AND_DROP` | Fichas de palabras arrastrables a huecos (`om-text-gap__target-item`). |
| Dropdown Menus | `DROPDOWN` | Seleccion de opciones en menus desplegables (`listbox`). |
| Sorting | `SORTING` | Clasificacion de fichas en columnas y categorias (`osSorting`). |
| Sentence & Word Reordering | `REORDERING` | Ordenar palabras horizontalmente u oraciones completas verticalmente. |
| Text Highlighting | `HIGHLIGHTING` | Resaltado de frases clave o errores gramaticales (`imMarking`). |
| Audio & Text Matching | `MATCHING` | Unir con lineas interactivas audios o textos de columnas izquierda/derecha. |
| Speaking & Voice Recording | `SPEAKING` | Escuchar la pregunta, seleccionar la respuesta y pronunciar por microfono virtual. |
| Presentation / Study | `PRESENTATION` | Reproduccion y avance de pantallas de lectura o estudio. |

---

## Compatibilidad de Navegadores Chromium

El asistente detecta automaticamente los navegadores instalados en tu computadora y te permite elegir con cual trabajar:
* Google Chrome
* Brave Browser
* Opera / Opera GX
* Microsoft Edge
* Vivaldi / Chromium

### Forzar un navegador especifico por consola (Opcional):
```bash
python run.py --browser chrome    # Usar Google Chrome
python run.py --browser brave     # Usar Brave Browser
python run.py --browser opera     # Usar Opera / Opera GX
python run.py --browser edge      # Usar Microsoft Edge
```

---

## Configuracion de Audio para Ejercicios de Pronunciacion (Speaking)

Para que el asistente responda preguntas de grabacion de voz de manera automatica:

1. Descarga e instala el controlador gratuito [VB-Audio Virtual Cable](https://vb-audio.com/Cable/).
2. En la configuracion de sonido de tu sistema operativo, elige **CABLE Input** como salida de reproduccion secundaria.
3. En Google Chrome:
   - Ve a `Configuracion > Privacidad y seguridad > Configuracion de sitios > Microfono`.
   - Selecciona **CABLE Output (VB-Audio Virtual Cable)** como microfono predeterminado.
4. El asistente sintetizara la respuesta nativamente en ingles y transmitira el audio directamente al microfono de la plataforma.

---

## Preguntas Frecuentes y Solucion de Problemas

### 1. "Python no se reconoce como un comando interno o externo"
- **Causa:** Python no esta agregado al PATH del sistema.
- **Solucion:** Descarga Python 3.10 o superior desde [python.org](https://www.python.org/) y durante la instalacion asegurate de marcar la casilla **"Add python.exe to PATH"**.

### 2. "Donde obtengo mi clave de Gemini API?"
- Puedes obtener una clave de API gratuita en [Google AI Studio](https://aistudio.google.com/).
- El lanzador te la solicitara amablemente por consola la primera vez, o puedes escribirla en el archivo `.env`:
  ```env
  GEMINI_API_KEY=tu_clave_aqui
  ```

### 3. "Que pasa si cambio de computadora?"
- El acceso queda vinculado al hardware del primer equipo autorizado.
- Si compras o cambias de equipo legitimamente, contacta al propietario para que presione el boton **`[Reset PC]`** en el panel de control movil. Esto te permitira vincular tu nueva maquina al iniciar sesion.

### 4. "Violacion de seguridad y clonacion detectada"
- Este mensaje aparece si se intenta usar la misma cuenta en dos computadoras distintas simultaneamente o si se copia la carpeta de instalacion a otra maquina. Las credenciales son personales e intransferibles.

---

## Verificacion y Pruebas Automatizadas

Para comprobar el correcto funcionamiento de todos los modulos y la seguridad anti-clonacion:

```bash
# Ejecutar todas las pruebas del proyecto
python -m pytest tests/

# Ejecutar especificamente la suite de auditoria de seguridad
python -m pytest tests/test_security_audit.py -v
```

---

## Estructura del Proyecto

```text
NGL-English-Assistant/
├── .github/workflows/      # Despliegue automatico del panel movil en GitHub Pages
├── ai/                     # Integracion con Google Gemini y modelos multimodales
├── analyzer/               # Extraccion e inspeccion del DOM de NGL / Avallain
├── auth/                   # Modulos de autorizacion, HWID y Firebase Cloud Auth
├── automation/             # Motor de navegacion y resolucion continua multi-pantalla
├── browser/                # Controlador CDP para Chrome, Brave, Opera y Edge
├── config/                 # Configuraciones globales del sistema
├── docs/                   # Portal web administrativo para celular (GitHub Pages)
├── history/                # Historial de actividades y respuestas
├── interaction/            # Manipulacion de controles y emision de voz
├── tests/                  # Suite completa de pruebas unitarias y de seguridad
├── admin.html              # Panel web local de administracion
├── app.py                  # Interfaz grafica de usuario (Streamlit)
├── build_dist.py           # Compilador a ejecutable binario (.exe)
├── open_admin.py           # Acceso directo para abrir el panel de administracion
├── requirements.txt        # Dependencias de Python
├── run.bat                 # Lanzador para Windows (batch)
├── run.py                  # Orquestador maestro multiplataforma
├── run.sh                  # Lanzador para macOS y Linux (bash)
├── start.bat               # Acceso directo en 1 clic para Windows
├── start.sh                # Acceso directo en 1 clic para macOS y Linux
├── .env.example            # Plantilla limpia de variables de entorno
└── .gitignore              # Proteccion estricta de secretos y temporales
```

---

## Privacidad y Seguridad de Datos

* **Sin almacenamiento de credenciales:** El software no pide ni almacena contrasenas de tu institucion ni de NGL. La autenticacion se hace directamente en tu navegador personal.
* **Procesamiento Local:** Las conexiones de automatizacion ocurren estrictamente dentro de tu computadora a traves del puerto local `localhost:9222`.
* **Cifrado de Extremo a Extremo:** Toda la verificacion de licencias viaja mediante HTTPS cifrado contra Firebase Realtime Database.
