# Gmail Cleaner

Herramienta local en Python para **inventariar, analizar y limpiar una cuenta de Gmail** mediante la Gmail API.

Gmail Cleaner está diseñado con una separación clara entre:

1. **Inventario** → recopila información de los mensajes.
2. **Análisis y selección** → permite filtrar y exportar los mensajes que se quieren procesar.
3. **Ejecución** → mueve a la papelera exactamente los mensajes incluidos en el CSV seleccionado.

El proyecto está pensado para ejecutarse localmente y utiliza OAuth de Google. No requiere almacenar las credenciales de Gmail en ningún servidor externo.

---

## Características

* Inventario de mensajes de Gmail en CSV.
* Inventario parcial o completo del buzón.
* Reanudación de inventarios interrumpidos.
* Control de velocidad de peticiones para evitar exceder las cuotas de Gmail API.
* Reintentos automáticos ante errores temporales y límites de cuota.
* Información del remitente, destinatario, asunto, fecha, etiquetas y tamaño.
* Detección de adjuntos.
* Análisis por remitente.
* Análisis por dominio.
* Filtros por remitente y dominio.
* Ordenación por fecha o tamaño.
* Exportación de mensajes seleccionados a otro CSV.
* Modo `dry-run` antes de modificar Gmail.
* Envío explícito de mensajes seleccionados a la papelera.
* El borrado permanente no forma parte del proyecto.
* Datos locales y credenciales excluidos de Git mediante `.gitignore`.

---

## Arquitectura

El flujo principal es:

```text
                    Gmail
                      │
                      ▼
              ┌───────────────┐
              │   Inventario  │
              │  inventory.py │
              └───────┬───────┘
                      │
                      ▼
              data/inventory.csv
                      │
                      ▼
              ┌───────────────┐
              │    Análisis   │
              │  analyzer.py  │
              └───────┬───────┘
                      │
             filtros / selección
                      │
                      ▼
              data/to_delete.csv
                      │
                      ▼
              ┌───────────────┐
              │    Cleaner    │
              │  cleaner.py   │
              └───────┬───────┘
                      │
                      ▼
               Gmail → Papelera
```

La idea fundamental es que **el cleaner no decide qué mensajes eliminar**.

`to_delete.csv` representa una selección explícita y confiable. Si un mensaje está en ese archivo, `clean_inventory --delete` lo procesa.

---

## Requisitos

* Python 3.11 o superior.
* Una cuenta de Google/Gmail.
* Un proyecto de Google Cloud.
* Gmail API habilitada.
* Un cliente OAuth de tipo aplicación de escritorio.

El proyecto se ha desarrollado y probado con Python 3.14.

---

# Instalación

Clona el repositorio:

```bash
git clone <REPOSITORY_URL>
cd gmail-cleaner
```

Crea un entorno virtual:

```bash
python3 -m venv .venv
```

Actívalo:

```bash
source .venv/bin/activate
```

Instala el proyecto:

```bash
pip install -e .
```

Comprueba que los comandos están disponibles:

```bash
save_to_csv --help
analyze_inventory --help
clean_inventory --help
```

---

# Configuración de Google Cloud

Gmail Cleaner utiliza OAuth 2.0 para acceder a Gmail.

## 1. Crear un proyecto

Accede a Google Cloud Console y crea un proyecto nuevo.

Por ejemplo:

```text
Gmail Cleaner
```

## 2. Habilitar Gmail API

Dentro del proyecto:

```text
APIs y servicios
→ Biblioteca
→ Gmail API
→ Habilitar
```

## 3. Configurar OAuth

En Google Cloud:

```text
Google Auth Platform
```

Configura la aplicación como una aplicación externa.

Para uso personal no es necesario publicar la aplicación para empezar a utilizarla.

Añade tu cuenta de Gmail como usuario de prueba.

## 4. Crear credenciales OAuth

Crea un cliente OAuth:

```text
Tipo de aplicación:
Aplicación de escritorio
```

Descarga el archivo JSON de credenciales.

Renómbralo:

```text
credentials.json
```

y colócalo en la raíz del proyecto:

```text
gmail-cleaner/
├── credentials.json
├── pyproject.toml
├── README.md
└── src/
```

**No publiques nunca este archivo.**

Está incluido en `.gitignore`.

---

# OAuth

La primera vez que se ejecuta una operación que necesita acceder a Gmail, el programa abrirá el flujo de autorización de Google.

Después de autorizar el acceso, se crea:

```text
credentials/token.json
```

El token se reutiliza en ejecuciones posteriores.

El proyecto solicita actualmente:

```text
https://www.googleapis.com/auth/gmail.modify
```

Este permiso permite leer y modificar mensajes de Gmail, incluyendo moverlos a la papelera.

Las credenciales y tokens son datos privados y están excluidos de Git.

---

# Primer uso

Una vez configurado OAuth, puedes generar un inventario.

Por defecto:

```bash
save_to_csv
```

procesa hasta 100 mensajes y genera:

```text
data/inventory.csv
```

También puedes indicar explícitamente la cantidad:

```bash
save_to_csv -c 500
```

El parámetro `-c` significa **count**.

Por ejemplo:

```bash
save_to_csv -c 1000
```

procesa hasta 1000 mensajes nuevos.

---

# Inventario completo

Para inventariar todo el buzón:

```bash
save_to_csv --all
```

En este modo el programa no depende de un contador aproximado del buzón.

Recorre las páginas devueltas por Gmail API mediante `messages.list()` hasta llegar al final.

Esto permite construir el inventario real a partir de los mensajes que Gmail devuelve.

El resultado se guarda en:

```text
data/inventory.csv
```

---

# Reanudar un inventario

Los inventarios pueden interrumpirse.

Por ejemplo:

```bash
save_to_csv --all --resume
```

El programa lee los IDs que ya están presentes en el CSV y evita volver a procesarlos.

Durante la reanudación se muestran mensajes como:

```text
Mensajes ya procesados: 5000
Se omitirán los mensajes ya presentes en el CSV.
```

El programa continúa recorriendo Gmail hasta encontrar los mensajes que todavía no están en el inventario.

Esto es especialmente importante en buzones grandes, ya que la Gmail API tiene límites de cuota y generar un inventario completo puede tardar bastante.

---

# Sobrescribir un inventario

Si el archivo de salida ya existe, el programa no lo sobrescribe accidentalmente.

Por ejemplo:

```bash
save_to_csv -c 100
```

puede mostrar:

```text
ERROR: El archivo ya existe: data/inventory.csv
Usa --force para sobrescribirlo o --resume para continuar.
```

Para empezar un inventario nuevo:

```bash
save_to_csv -c 100 --force
```

Para un inventario completo nuevo:

```bash
save_to_csv --all --force
```

**Atención:** `--force` sobrescribe el CSV existente.

---

# Archivo de inventario

El inventario contiene información como:

```text
id
thread_id
from
to
subject
date
labels
snippet
size
has_attachments
attachment_count
```

Ejemplo:

```csv
id,thread_id,from,to,subject,date,labels,snippet,size,has_attachments,attachment_count
abc123,abc123,"Example <example@example.com>","user@gmail.com","Example subject",...,INBOX,...,90856,False,0
```

El `id` de Gmail es especialmente importante porque identifica el mensaje que posteriormente puede procesarse.

---

# Analizar un inventario

El comando:

```bash
analyze_inventory
```

analiza:

```text
data/inventory.csv
```

Por defecto muestra:

* mensajes analizados;
* principales remitentes;
* principales dominios;
* estadísticas de adjuntos;
* tamaño total;
* mensajes más grandes.

También puedes especificar otro inventario:

```bash
analyze_inventory data/inventory.csv
```

---

# Filtrar por remitente

Para buscar mensajes de un remitente:

```bash
analyze_inventory --sender example@example.com
```

También se pueden especificar varios remitentes separados por comas:

```bash
analyze_inventory \
    --sender example@example.com,other@example.com
```

El filtro no modifica Gmail.

---

# Filtrar por dominio

Por ejemplo:

```bash
analyze_inventory --domain linkedin.com
```

También puede utilizarse junto con `--list`:

```bash
analyze_inventory \
    --domain linkedin.com \
    --list
```

Esto muestra los mensajes encontrados.

---

# Listar mensajes

El parámetro:

```bash
--list
```

muestra los mensajes que cumplen los filtros.

Ejemplo:

```bash
analyze_inventory \
    --domain amazon.es \
    --list
```

---

# Limitar resultados

Puedes limitar el número de mensajes mostrados:

```bash
analyze_inventory \
    --domain amazon.es \
    --list \
    --limit 50
```

---

# Ordenar resultados

Se puede ordenar por tamaño:

```bash
analyze_inventory \
    --list \
    --sort size
```

o por fecha:

```bash
analyze_inventory \
    --list \
    --sort date
```

---

# Exportar una selección

Los resultados filtrados pueden exportarse a otro CSV.

Por ejemplo:

```bash
analyze_inventory \
    --domain linkedin.com \
    --list \
    --export data/to_delete.csv
```

El archivo generado contiene los mensajes que cumplen el filtro.

Por ejemplo:

```text
data/to_delete.csv
```

Este archivo representa la selección que posteriormente podrá procesarse.

---

# Flujo recomendado para eliminar mensajes

La recomendación general es:

```text
1. Crear inventario
2. Analizar
3. Seleccionar
4. Exportar selección
5. Ejecutar dry-run
6. Revisar
7. Enviar a papelera
```

Ejemplo:

```bash
save_to_csv --all
```

Después:

```bash
analyze_inventory \
    --domain example.com \
    --list \
    --export data/to_delete.csv
```

Comprobar la selección:

```bash
clean_inventory \
    data/to_delete.csv \
    --dry-run
```

Y solo después ejecutar:

```bash
clean_inventory \
    data/to_delete.csv \
    --delete
```

---

# Dry-run

El modo `dry-run` permite comprobar qué mensajes serían procesados sin modificar Gmail.

```bash
clean_inventory --dry-run
```

Por defecto utiliza:

```text
data/to_delete.csv
```

También se puede especificar otro archivo:

```bash
clean_inventory data/test.csv --dry-run
```

El programa muestra los mensajes seleccionados y termina sin realizar modificaciones.

Ejemplo:

```text
=== DRY-RUN ===
Archivo: data/to_delete.csv
Mensajes seleccionados: 10

Mensajes que se enviarían a la papelera:

...

DRY-RUN: se procesarían 10 mensajes.
No se ha modificado Gmail.
```

---

# Enviar mensajes a la papelera

Cuando la selección ha sido revisada:

```bash
clean_inventory --delete
```

Antes de modificar Gmail, el programa solicita confirmación explícita:

```text
Escribe 'SI' para confirmar:
```

Solo la respuesta exacta:

```text
SI
```

continúa con la operación.

Los mensajes se mueven a la papelera de Gmail.

**Gmail Cleaner no realiza borrado permanente.**

La operación utiliza la etiqueta:

```text
TRASH
```

mediante Gmail API.

Los mensajes permanecen sujetos a las reglas normales de la papelera de Gmail.

---

# Separación entre selección y ejecución

Una característica importante del proyecto es que `cleaner.py` no intenta decidir qué mensajes son basura.

Por ejemplo, una futura regla podría seleccionar:

```text
Todos los mensajes de example.com sin adjuntos
```

y producir:

```text
data/to_delete.csv
```

Una regla diferente podría seleccionar:

```text
Mensajes de example.com con adjuntos
```

y decidir conservarlos.

El cleaner únicamente procesa lo que aparece en el CSV seleccionado.

Esto evita mezclar:

```text
criterios de selección
```

con:

```text
operaciones destructivas
```

y permite revisar la selección antes de modificar Gmail.

---

# Cuotas y rendimiento de Gmail API

Gmail API aplica límites de cuota.

Las operaciones de inventario utilizan principalmente:

```text
messages.list()
messages.get()
```

`messages.get()` tiene un coste de cuota considerablemente superior a `messages.list()`.

Por este motivo, inventariar miles de mensajes puede tardar bastante.

Gmail Cleaner incorpora un `RateLimiter` para espaciar las peticiones.

La configuración actual utiliza aproximadamente:

```text
100 operaciones por minuto
```

para reducir el riesgo de superar las cuotas disponibles.

El programa también incorpora reintentos ante determinados errores de comunicación y límites de cuota.

---

# Inventarios grandes

En un buzón grande, no se recomienda asumir que el inventario completo terminará inmediatamente.

Por ejemplo:

```bash
save_to_csv --all
```

puede tardar considerablemente dependiendo de:

* número de mensajes;
* cuota disponible;
* latencia de la API;
* velocidad de las respuestas de Google;
* interrupciones de red;
* límites temporales de cuota.

Si el proceso se interrumpe, puede continuarse mediante:

```bash
save_to_csv --all --resume
```

El CSV funciona como punto de recuperación porque los IDs ya procesados se conservan.

---

# Seguridad

Gmail Cleaner trabaja con datos privados de una cuenta de Gmail.

Nunca debes subir al repositorio:

```text
credentials.json
token.json
client_secret*.json
data/*.csv
```

Estos archivos están excluidos mediante `.gitignore`.

Especialmente importante:

```text
credentials.json
```

contiene las credenciales del cliente OAuth.

Y:

```text
credentials/token.json
```

contiene información de autorización de la cuenta.

No publiques ninguno de ellos.

---

# Datos locales

Los inventarios y selecciones se guardan localmente en:

```text
data/
```

El contenido de `data/` está excluido de Git excepto:

```text
data/.gitkeep
```

Esto evita publicar accidentalmente:

* direcciones de correo;
* asuntos;
* snippets;
* IDs de Gmail;
* información privada;
* metadatos de mensajes.

---

# Estructura del proyecto

```text
gmail-cleaner/
│
├── credentials/
│   └── token.json              # Local, ignorado por Git
│
├── data/
│   ├── .gitkeep
│   ├── inventory.csv           # Local, ignorado por Git
│   └── to_delete.csv           # Local, ignorado por Git
│
├── src/
│   └── gmail_cleaner/
│       ├── __init__.py
│       ├── analyzer.py
│       ├── cleaner.py
│       ├── cli.py
│       ├── gmail_api.py
│       └── inventory.py
│
├── .gitignore
├── LICENSE
├── README.md
└── pyproject.toml
```

---

# Componentes

## `gmail_api.py`

Gestiona:

* credenciales OAuth;
* renovación del token;
* creación del cliente Gmail API.

## `inventory.py`

Gestiona:

* recorrido de mensajes;
* recuperación de metadatos;
* detección de adjuntos;
* control de velocidad;
* reintentos;
* inventarios completos;
* reanudación.

## `analyzer.py`

Gestiona:

* lectura del inventario;
* filtros;
* análisis por remitente;
* análisis por dominio;
* estadísticas;
* ordenación;
* exportación de selecciones.

## `cleaner.py`

Gestiona:

* lectura de `to_delete.csv`;
* `dry-run`;
* confirmación;
* envío de mensajes a la papelera.

## `cli.py`

Expone los comandos de línea de órdenes:

```text
save_to_csv
analyze_inventory
clean_inventory
```

---

# Comandos disponibles

## Inventario

```bash
save_to_csv
```

Inventario por defecto de 100 mensajes.

```bash
save_to_csv -c 500
```

Procesa hasta 500 mensajes.

```bash
save_to_csv --all
```

Procesa todo el buzón.

```bash
save_to_csv --all --resume
```

Reanuda un inventario.

```bash
save_to_csv --all --force
```

Crea un inventario completo desde cero.

```bash
save_to_csv -c 100 -o data/custom.csv
```

Utiliza un archivo de salida diferente.

---

## Análisis

```bash
analyze_inventory
```

```bash
analyze_inventory --sender example@example.com
```

```bash
analyze_inventory --sender a@example.com,b@example.com
```

```bash
analyze_inventory --domain example.com
```

```bash
analyze_inventory --list
```

```bash
analyze_inventory --limit 20
```

```bash
analyze_inventory --sort size
```

```bash
analyze_inventory --sort date
```

```bash
analyze_inventory \
    --domain example.com \
    --list \
    --export data/to_delete.csv
```

---

## Limpieza

Dry-run:

```bash
clean_inventory --dry-run
```

Con archivo específico:

```bash
clean_inventory data/to_delete.csv --dry-run
```

Enviar a papelera:

```bash
clean_inventory --delete
```

Con archivo específico:

```bash
clean_inventory data/to_delete.csv --delete
```

---

# Limitaciones actuales

Gmail Cleaner es una herramienta local de limpieza y actualmente no pretende ser un cliente completo de Gmail.

Entre las limitaciones actuales:

* No existe una interfaz gráfica.
* No elimina mensajes permanentemente.
* La selección avanzada de mensajes se realiza mediante filtros y exportaciones.
* El inventario completo puede tardar en cuentas grandes debido a las cuotas de Gmail API.
* El proyecto depende de la disponibilidad de Gmail API.
* La detección de adjuntos se basa en la estructura MIME proporcionada por Gmail API.
* El token OAuth debe mantenerse localmente.
* La aplicación debe configurarse en Google Cloud antes del primer uso.

---

# Desarrollo

Para comprobar la sintaxis del proyecto:

```bash
python3 -m py_compile src/gmail_cleaner/*.py
```

Para consultar la ayuda:

```bash
save_to_csv --help
analyze_inventory --help
clean_inventory --help
```

El proyecto utiliza `setuptools` y está definido mediante `pyproject.toml`.

---

# Filosofía del proyecto

Gmail Cleaner intenta mantener una separación sencilla entre:

```text
descubrir
   ↓
analizar
   ↓
decidir
   ↓
revisar
   ↓
ejecutar
```

La herramienta no intenta adivinar qué correos debe eliminar.

El usuario determina los criterios y la selección final.

Una vez que una selección ha sido exportada a `to_delete.csv`, ese archivo representa explícitamente los mensajes que se han decidido procesar.

El `dry-run` proporciona una última comprobación antes de modificar Gmail.

---

# Licencia

Este proyecto se distribuye bajo la licencia MIT.

Consulta el archivo:

```text
LICENSE
```

para conocer los términos completos.

---

## Disclaimer

Esta herramienta interactúa directamente con una cuenta de Gmail y puede modificar mensajes.

Utilízala bajo tu propia responsabilidad.

Se recomienda revisar siempre los resultados mediante `--dry-run` antes de ejecutar una operación sobre un conjunto importante de mensajes.
