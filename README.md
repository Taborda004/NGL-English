# NGL English Assistant

Asistente inteligente y autonomo disenado para analizar, resolver y verificar ejercicios y examenes de ingles en la plataforma National Geographic Learning (NGL / Avallain) (`learn.eltngl.com`).

Se conecta a tu sesion activa de Google Chrome o navegadores basados en Chromium mediante el protocolo Chrome DevTools (CDP) sin almacenar credenciales de usuario. Extrae el contexto interactivo (textos, audios, imagenes y modelos de datos MVC de la plataforma), resuelve mediante modelos de Google Gemini y completa los ejercicios garantizando maxima precision.

---

## Caracteristicas Principales

* **Modo Autonomo en Cadena:** Resuelve continuamente ejercicio tras ejercicio dentro de asignaciones completas o examenes multi-pantalla (Unit Tests de hasta 25 pantallas), verificando la finalizacion y avanzando automaticamente.
* **Modo Asistido Seguro (Sin Enviar):** Resuelve y rellena las respuestas en el formulario del navegador para que el usuario pueda revisarlas antes de enviar manualmente.
* **Soporte de Ejercicios de Pronunciacion (Speaking):**
  * Reproduce el audio de la pregunta para que el estudiante escuche el dialogo o enunciado.
  * Selecciona de forma exacta la opcion correcta en el modelo MVC interno de Avallain y en el DOM.
  * Emite voz en ingles sintetizada de forma nativa a traves de VB-Audio Virtual Cable, permitiendo que el navegador capture el audio real a traves del microfono.
* **Resolucion Multimodal con Gemini:** Combina transcripciones, audio MP3, capturas de pantalla y texto DOM estructurado para un analisis contextual riguroso.
* **Parada de Seguridad Inteligente:** Si la confianza de la inteligencia artificial es inferior al umbral configurado o se detecta un comportamiento inesperado, la ejecucion se pausa de inmediato.
* **Sistema de Autorizacion y Licenciamiento Autonomo en la Nube:**
  * Proteccion integral anti-clonacion y anti-distribucion no autorizada.
  * Vinculacion estricta 1:1 a hardware fisico inmutable (HWID multi-plataforma: Windows, macOS y Linux).
  * Solicitud de acceso automatizada: los nuevos usuarios introducen su correo y nombre desde el portal web integrado.
  * Panel de administracion movil en la nube: el propietario (Taborda004) aprueba solicitudes en 1 solo clic o cambia estados mediante selectores desplegables desde cualquier celular en `https://taborda004.github.io/NGL-English/`.

---

## Tipos de Ejercicios Soportados

| Tipo de Ejercicio | Identificador | Descripcion |
|---|---|---|
| Fill in the Blanks | `FILL_BLANK` | Rellenar huecos y cajas de texto (`input.textGapItem__input`). |
| Multiple Choice | `MULTIPLE_CHOICE` | Opcion multiple con radio buttons o casillas (`choice_interaction`). |
| Drag and Drop | `DRAG_AND_DROP` | Fichas de palabras arrastrables a huecos (`om-text-gap__target-item`). |
| Dropdown Menus | `DROPDOWN` | Seleccion de opciones en menus desplegables (`listbox`). |
| Sorting | `SORTING` | Clasificacion de fichas en columnas y categorias (`osSorting`). |
| Sentence and Word Reordering | `REORDERING` | Ordenar palabras horizontalmente u oraciones completas verticalmente. |
| Text Highlighting | `HIGHLIGHTING` | Resaltado de frases clave o errores gramaticales (`imMarking`). |
| Audio and Text Matching | `MATCHING` | Unir con lineas interactivas audios o textos de columnas izquierda/derecha. |
| Speaking and Voice Recording | `SPEAKING` | Escuchar la pregunta, seleccionar la respuesta y pronunciar por microfono virtual. |
| Presentation / Study | `PRESENTATION` | Reproduccion y avance de pantallas de lectura o estudio. |

---

## Requisitos del Sistema

1. **Python 3.10 o superior**.
2. **Navegador Chromium**: Google Chrome, Brave Browser, Opera GX o Microsoft Edge.
3. **Clave de API de Google Gemini**: Obtenible de forma gratuita en [Google AI Studio](https://aistudio.google.com/).
4. *(Opcional para Speaking)*: Controlador de audio virtual **VB-Audio Virtual Cable** (gratuito en [vb-audio.com/Cable](https://vb-audio.com/Cable/)).

---

## Inicio Rapido en 1 Clic (Recomendado para Produccion)

El repositorio incluye lanzadores automatizados que configuran el entorno virtual, instalan dependencias y preparan el navegador sin requerir comandos complejos:

### En Windows
Haz doble clic en `start.bat` (o `run.bat`), o ejecuta en consola:
```powershell
python run.py
```

### En macOS / Linux
Otorga permisos de ejecucion y corre `start.sh` (o `run.sh`):
```bash
chmod +x start.sh run.sh
./start.sh
```

### Acciones que el Lanzador Realiza Automaticamente:
1. **Entorno Virtual:** Detecta o crea `.venv` y activa el interprete aislado.
2. **Dependencias:** Instala los paquetes de `requirements.txt` y configura Playwright Chromium si no estuviesen instalados.
3. **Configuracion de Entorno:** Si no existe `.env`, genera uno a partir de `.env.example` y solicita tu clave de Gemini si falta.
4. **Deteccion de Navegadores:** Detecta si Chrome, Brave, Opera GX o Edge estan instalados, permitiendo seleccionarlos sin configuraciones invasivas.
5. **Servidor Streamlit:** Inicia el servidor web local y abre la interfaz grafica en `http://localhost:8501`.

---

## Flujo de Licenciamiento y Aprobacion de Usuarios

El software implementa un control de acceso autonomo para proteger la propiedad intelectual contra clonaciones o comparticion indebida de credenciales:

### 1. Usuario Solicitante (Alumno / Cliente)
1. Al clonar y ejecutar el programa, se abrira el **Portal de Acceso y Licenciamiento**.
2. En la pestana **"Solicitar Acceso (Nuevo Usuario)"**, el usuario introduce su nombre, correo electronico y nota opcional (ej: grupo o curso).
3. El sistema captura de manera transparente el identificador inmutable de hardware (HWID) de su maquina y registra la peticion en la nube con estado `PENDIENTE`.
4. El software permanecera bloqueado hasta que el propietario autorice el acceso.

### 2. Propietario (Taborda004) - Aprobacion desde Celular o PC
El propietario puede gestionar todas las solicitudes a costo cero desde cualquier lugar:
* **Desde el Celular (Nube):** Abre el enlace oficial [https://taborda004.github.io/NGL-English/](https://taborda004.github.io/NGL-English/) desde Safari o Chrome.
* **Aprobacion Inmediata:** Toca el boton verde **`[Aprobar Acceso (1-Clic)]`** o cambia el estado en el menu desplegable a `Aprobado (Activo)`.
* **Desde la Aplicacion de Escritorio:** En la barra lateral, marca la casilla "Abrir Panel de Control" para gestionar usuarios directamente.

### 3. Proteccion Estricta Anti-Clonacion (Node-Locking)
* Cuando el usuario aprobado inicia sesion, su cuenta queda ligada a su HWID fisico.
* Si el usuario comparte su correo o si un tercero clona el repositorio e intenta usar credenciales ajenas en otra computadora, el sistema detecta la discrepancia de hardware y bloquea el acceso de inmediato:
  > *"Violacion de seguridad y clonacion detectada: Esta cuenta esta vinculada a otro equipo fisico. No esta permitido compartir credenciales ni clonar cuentas en otras maquinas."*
* Si un usuario cambia legitimamente de computadora, el administrador puede presionar el boton **`[Reset PC]`** en el panel para autorizar la nueva vinculacion.

---

## Compatibilidad de Navegadores Chromium

El asistente se comunica mediante el protocolo estandar **Chrome DevTools Protocol (CDP)** en el puerto `9222`:
* Brave Browser
* Opera / Opera GX
* Microsoft Edge
* Google Chrome
* Vivaldi / Arc

### Forzar un Navegador Especifico por Linea de Comandos:
```powershell
python run.py --browser brave     # Forzar Brave
python run.py --browser opera     # Forzar Opera / Opera GX
python run.py --browser edge      # Forzar Microsoft Edge
python run.py --browser chrome    # Forzar Google Chrome
```

---

## Configuracion de Audio para Ejercicios de Speaking

Para resolver de manera desatendida preguntas de pronunciacion en el navegador:
1. Instala el controlador gratuito [VB-Audio Virtual Cable](https://vb-audio.com/Cable/).
2. En el panel de sonido del sistema operativo, configura **CABLE Input** como salida de audio o dispositivo secundario.
3. En el navegador: ve a `Configuracion > Privacidad y seguridad > Microfono` y selecciona **CABLE Output (VB-Audio Virtual Cable)**.
4. El asistente sintetizara la respuesta nativamente en ingles y transmitira la voz por el cable virtual directamente al microfono de la plataforma.

---

## Suite de Pruebas y Auditoria de Seguridad

El proyecto cuenta con un conjunto exhaustivo de pruebas unitarias, de integracion y de hacking etico:

```bash
# Ejecutar todas las pruebas del sistema
python -m pytest tests/

# Ejecutar especificamente la auditoria de seguridad
python -m pytest tests/test_security_audit.py -v
```

---

## Estructura del Repositorio

```text
NGL-English-Assistant/
├── .github/workflows/      # Despliegue continuo de GitHub Pages para administracion movil
├── ai/                     # Integracion con Google Gemini y prompts pedagogicos
│   ├── prompts.py          # Plantillas estructuradas de prompts
│   └── solver.py           # Resolvedor multimodal (texto, imagen, audio)
├── analyzer/               # Inspeccion y analisis semantico del DOM
│   ├── content_extractor.py # Extractor de elementos interactivos
│   ├── exercise_detector.py # Clasificador heuristico de ejercicios
│   └── parser.py           # Parser y validador de respuestas
├── auth/                   # Sistema de seguridad, HWID y autenticacion en la nube
│   ├── admin_ui.py         # Interfaz Streamlit del portal de login y panel maestro
│   ├── cloud_auth.py       # Gestor de solicitudes, aprobaciones y base de datos
│   └── license_manager.py  # Generacion multi-plataforma de HWID y firmas HMAC
├── automation/             # Motor de ejecucion continua multi-pantalla
│   └── chain_runner.py     # Orquestador del flujo autonomo
├── browser/                # Controlador de sesiones Chromium y CDP
│   ├── browser_manager.py  # Gestor de contextos de Playwright
│   └── page_detector.py    # Detector de asignaciones y estado de pantalla
├── config/                 # Configuraciones globales y variables de entorno
│   └── settings.py
├── docs/                   # Portal web administrativo para aprobacion movil (GitHub Pages)
│   └── index.html
├── history/                # Registro persistente de sesiones y respuestas
├── interaction/            # Manipulacion de controles y modelos MVC de Avallain
│   ├── form_filler.py      # Inyeccion precisa de respuestas en el DOM
│   └── speech_player.py    # Emision de voz sintetizada por microfono virtual
├── tests/                  # Suite completa de pruebas y auditoria de seguridad
├── admin.html              # Panel web local de administracion
├── app.py                  # Interfaz grafica principal de usuario (Streamlit)
├── open_admin.py           # Lanzador directo del portal administrativo en navegador
├── requirements.txt        # Dependencias de produccion de Python
├── run.bat                 # Lanzador rapido para Windows
├── run.py                  # Orquestador maestro multiplataforma
├── run.sh                  # Lanzador rapido para macOS y Linux
├── start.bat               # Acceso directo para Windows
├── start.sh                # Acceso directo para macOS y Linux
├── .env.example            # Plantilla limpia de variables de entorno
└── .gitignore              # Exclusion estricta de secretos y archivos temporales
```

---

## Privacidad y Cumplimiento

* **Credenciales Locales:** Este software no solicita ni almacena contraseñas de la plataforma educativa. La sesion se autentica directamente en el navegador personal del usuario.
* **Procesamiento de Datos:** La comunicacion entre el software y el navegador se efectua de manera estricta a traves de sockets locales (`127.0.0.1:9222`).
* **Proteccion de Claves:** Ninguna clave de API privada o credencial de administracion se incluye en el control de versiones.
