## Fuentes de datos

### Mecanismo de acceso

Lectura directa de la base de datos relacional PostgreSQL con los datos de ITACA. La conexión se configura con variables de entorno definidas en un fichero `.env` (que no debe subirse al repositorio):

```text
POSTGRES_HOST=
POSTGRES_PORT=
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=
```

El script solo realiza **consultas de lectura** (`SELECT`). No modifica ni borra nada en PostgreSQL.

### Tablas

| Tabla | Datos |
|---|---|
| `alumnos` | `Anyo`, `NIA`, `sexo`, `nacionalidad`, `provincia`, `municipio`, `ensenanza`, `curso`, `grupo`, `turno`, `linea`, `modalidad`, `repite`, `estado_matricula`, `tipo_matricula`, `fecha_matricula`, `fecha_ingreso_centro` |
| `calificaciones` | `Anyo`, `evaluacion`, `alumno`, `ensenanza`, `curso`, `contenido`, `bloque_contenido`, `nota_numerica`, `tipo_nota` |
| `contenidos` | `Anyo`, `codigo`, `nombre_cas`, `nombre_val`, `ensenanza`, `curso` |
| `cursos` | `Anyo`, `codigo`, `nombre_cas`, `nombre_val`, `abreviatura`, `ensenanza`, `padre` |
| `grupos` | `Anyo`, `Grupo`, `Nombre_Grupo`, `Turno`, `Modalidad`, `Capacidad` |

Todas las tablas tienen una columna `anyo`, que se usa para decidir qué datos se importan.

## Estructura de carpetas

```text
proyecto/
├── .env                      # Credenciales (no se sube a Git)
└── ingesta/
    ├── data/
    │   ├── control/
    │   │   └── ultima_ingesta_db.txt   # Año de la última ingesta
    │   └── raw/
    │       ├── alumnos.jsonl
    │       ├── calificaciones.jsonl
    │       ├── contenidos.jsonl
    │       ├── cursos.jsonl
    │       └── grupos.jsonl
    └── scripts/
        └── ingesta_itaca_bd.py
```

## Preparación del entorno

```bash
cd proyecto
python -m venv .venv
source .venv/bin/activate      # En Windows: .venv\Scripts\activate
pip install python-dotenv psycopg2-binary pandas
```

Además de la biblioteca estándar (`os`, `json`, `hashlib`, `logging`, `datetime`), el script necesita `python-dotenv`, `psycopg2` y `pandas`.

## Ejecución

```bash
python ingesta/scripts/ingesta_itaca_bd.py
```

Las rutas (`data/raw`, `data/control`) son relativas, por lo que el script debe ejecutarse desde la carpeta que contiene `data/`.

## Funcionamiento del script

1. **Conecta con PostgreSQL** usando las variables del `.env`. Si falla, lo registra y termina sin hacer nada más.
2. **Lee el año de la última ingesta** desde `data/control/ultima_ingesta_db.txt`. Si el fichero no existe o está vacío, usa `2020` por defecto.
3. **Recorre las tablas** definidas en `TABLAS`.
4. **Extrae los datos** con `SELECT * FROM <tabla> WHERE anyo >= '<ultima_ejecucion>'`.
5. **Anonimiza el NIA** en las columnas `nia` y `alumno` (ver siguiente apartado).
6. **Elimina del `.jsonl` los años que se van a reimportar**: las filas con `anyo >= ultima_ejecucion`, para evitar duplicados.
7. **Guarda el resultado** en `data/raw/<tabla>.jsonl`: las filas históricas conservadas más las filas nuevas (un registro JSON por línea, UTF-8, `ensure_ascii=False`).
8. **Actualiza el fichero de control** con el año actual, solo si todas las tablas se han procesado sin errores.

### Funciones principales

| Función | Responsabilidad |
|---|---|
| `conexionBD` | Abre la conexión con PostgreSQL |
| `obtener_ultima_ejecucion` | Lee el año de la última ingesta (por defecto `2020`) |
| `extraer_campos` | Devuelve las columnas de una tabla definidas en `VARIABLES` como cadena para el `SELECT`. Si la tabla no existe o no tiene campos, devuelve `None` |
| `extraer_tabla` | Consulta una tabla con las columnas de `extraer_campos`, filtrando por `anyo` |
| `eliminar_anyos` | Descarta del `.jsonl` las filas con `anyo >= ultima_ejecucion` y devuelve las anteriores |
| `guardar_tabla` | Reescribe el `.jsonl` con las filas históricas y las nuevas |
| `anonimizar_nia` | Sustituye el NIA por un identificador anónimo |
| `anonimizar_dataframe` | Aplica la anonimización a las columnas `nia` y `alumno` |
| `recorrerTablas` | Orquesta la extracción, anonimización y guardado de todas las tablas |
| `guardar_fecha_ingesta` | Escribe el año actual en el fichero de control |

## Carga incremental sin duplicados

Para que ejecutar el script varias veces no duplique datos, cada ejecución **reemplaza** los datos del intervalo importado en lugar de añadirlos:

- **Primera ejecución:** no existe el fichero de control, así que se importa desde `2020` hasta el último año disponible.
- **Siguientes ejecuciones:** se importan los datos con `anyo >= ultima_ejecucion`. Antes de escribirlos, se eliminan del `.jsonl` las filas de ese mismo intervalo.
- **Años anteriores:** no se modifican. Las filas con `anyo < ultima_ejecucion` se conservan tal cual.

Ejemplo: si la última ingesta fue en 2026, en una nueva ejecución se borran del `.jsonl` solo las filas de 2026 y se vuelven a importar los datos actualizados de ese año. Los datos de 2020 a 2025 permanecen intactos.

## Anonimización del NIA

El NIA es un dato identificativo, por lo que se sustituye antes de guardar nada en disco:

```python
def anonimizar_nia(nia: str) -> str:
    return hashlib.sha256(str(nia).strip().encode()).hexdigest()[:10]
```

- Se aplica a las columnas incluidas en `COLUMNAS_NIA` (`nia` y `alumno`), por lo que afecta a `alumnos` y `calificaciones`.
- La función es **determinista**: un mismo NIA genera siempre el mismo identificador, incluso entre ejecuciones, por lo que las tablas siguen pudiendo cruzarse.
- Durante la ejecución se usa un diccionario en memoria (`MAPA_NIA`) para no recalcular el hash de un NIA ya procesado. **No se guarda en disco**, así que no queda rastro del dato original.
- Los valores nulos se mantienen como `None`.
- El NIA original solo existe en PostgreSQL. En los `.jsonl` aparece únicamente el identificador anónimo.

## Manejo de errores y logging

- `logging` en nivel `INFO`: informa de las filas conservadas, eliminadas y guardadas por tabla.
- `WARNING` cuando una tabla no devuelve datos (no se guarda y su fichero no se toca) o cuando hubo errores y no se actualiza el fichero de control.
- `ERROR` si falla una consulta: se hace `rollback`, se marca la ejecución como incompleta y se continúa con las demás tablas.
- Si hay algún error, **no se actualiza** `ultima_ingesta_db.txt`, de modo que la siguiente ejecución repite el mismo intervalo.
- Aviso de pandas (`UserWarning: pandas only supports SQLAlchemy connectable`): es informativo, no afecta a los datos.

## Limitaciones conocidas

- `anyo` se compara **como texto**, igual que en la consulta. Funciona con años de 4 dígitos (`"2026"`).
- El fichero de control guarda el **año natural** de la ejecución, que no tiene por qué coincidir con el último año presente en la base de datos.
- Si una tabla no devuelve filas, su `.jsonl` se deja tal cual.
- No hay transacción sobre los ficheros: si el proceso se interrumpe mientras reescribe un `.jsonl`, este puede quedar incompleto. Para regenerarlo, basta con borrar `data/raw/*.jsonl` y `data/control/ultima_ingesta_db.txt` y ejecutar de nuevo.

## Verificación

Tras ejecutar el script, comprobar que:

- [x] Existe un `.jsonl` por tabla en `data/raw/`.
- [x] No aparece ningún NIA real en los `.jsonl`.
- [x] El NIA anonimizado coincide entre `alumnos` y `calificaciones` para el mismo alumno.
- [x] Una segunda ejecución no aumenta el número de líneas de los `.jsonl` (no hay duplicados).
- [x] Los años anteriores a `ultima_ejecucion` no han cambiado entre ejecuciones.
- [x] `data/control/ultima_ingesta_db.txt` contiene el año esperado.