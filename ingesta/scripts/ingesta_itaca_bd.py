import os
from dotenv import load_dotenv
import psycopg2
import logging
import pandas as pd
from datetime import date
import json
import hashlib
import warnings

load_dotenv()

warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingesta_itaca_bd")


TABLAS = ["alumnos", "calificaciones", "contenidos", "cursos"]
COLUMNAS_NIA = ["nia", "alumno"]
MAPA_NIA = {}

VARIABLES = {
    "ALUMNOS": [
        "anyo", "nia", "sexo", "nacionalidad", "provincia", "municipio",
        "ensenanza", "curso", "grupo", "turno", "linea", "modalidad",
        "repite", "estado_matricula", "tipo_matricula", "fecha_matricula",
        "fecha_ingreso_centro",
    ],
    "CONTENIDOS": [
        "anyo", "codigo", "nombre_cas", "nombre_val", "ensenanza", "curso",
    ],
    "CALIFICACIONES": [
        "anyo", "evaluacion", "alumno", "ensenanza", "curso", "contenido",
        "bloque_contenido", "nota_numerica", "tipo_nota",
    ],
    "CURSOS": [
        "anyo", "codigo", "nombre_cas", "nombre_val", "abreviatura",
        "ensenanza", "padre",
    ],
}

def conexionBD():
    try:
        conexion = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT"),
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
        )
    except Exception as e:
        logger.info("Error de conexion con la base de datos")
        conexion = None

    return conexion


def obtener_ultima_ejecucion():
    try:
        with open("data/control/ultima_ingesta_db.txt") as f:
            anyo = f.read().strip()
            if not anyo:
                anyo = "2020"

    except FileNotFoundError:
        logger.info(
            "Archivo de control no encontrado. Se utilizará el año por defecto."
        )
        anyo = "2020"
    return anyo

def extraer_campos(tabla: str):
    campos = VARIABLES.get(tabla.upper())
    if not campos: 
        logger.info(f"No hay variables definidas para la tabla {tabla}")
        return None
    
    return ", ".join(campos)
    
def extraer_tabla(conexion, ultima_ejecucion: str, tabla: str):
    variables = extraer_campos(tabla)
    if variables is None:
        return None
    query = f"SELECT {variables} FROM {tabla} WHERE anyo >= '{ultima_ejecucion}'"
    try:
        res = pd.read_sql_query(query, conexion)
    except Exception as e:
        logger.error(f"Error al ejecutar la consulta: {e}")
        conexion.rollback()
        res = None
    return res


def eliminar_anyos(tabla: str, ultima_ejecucion: str):
    """
    Elimina del fichero de la tabla las filas con anyo >= ultima_ejecucion.
    Devuelve las filas que se conservan (años anteriores).
    """
    ruta = f"data/raw/{tabla}.jsonl"

    filas_antiguas = []
    eliminadas = 0

    if os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as file:
            for linea in file:
                if linea.strip() == "":
                    continue
                fila = json.loads(linea)
                if str(fila["anyo"]) < ultima_ejecucion:
                    filas_antiguas.append(linea)
                else:
                    eliminadas += 1

    logger.info(
        f"{tabla}: {eliminadas} filas con anyo >= {ultima_ejecucion} eliminadas"
    )
    return filas_antiguas


def guardar_tabla(res, tabla: str, ultima_ejecucion: str):
    os.makedirs("data/raw", exist_ok=True)
    ruta = f"data/raw/{tabla}.jsonl"

    # 1) ELIMINACIÓN: se hace en su propia función
    filas_antiguas = eliminar_anyos(tabla, ultima_ejecucion)

    # 2) INSERCIÓN: reescribimos el fichero con las antiguas + las nuevas
    with open(ruta, "w", encoding="utf-8") as file:
        for linea in filas_antiguas:
            file.write(linea)
        for fila in res.to_dict(orient="records"):
            file.write(json.dumps(fila, default=str, ensure_ascii=False) + "\n")

    logger.info(
        f"{tabla}: {len(filas_antiguas)} filas anteriores conservadas, "
        f"{len(res)} filas nuevas guardadas"
    )


def anonimizar_nia(nia: str) -> str:
    return hashlib.sha256(str(nia).strip().encode()).hexdigest()[:10]


def anonimizar_dataframe(df: pd.DataFrame, tabla: str) -> pd.DataFrame:

    columnas = []

    for col in COLUMNAS_NIA:
        if col in df.columns:
            columnas.append(col)

    if len(columnas) == 0:
        return df

    df = df.copy()

    for col in columnas:
        nuevos_valores = []
        for nia in df[col]:
            if pd.isna(nia):
                nuevos_valores.append(None)
                continue

            # Si no está en el mapa global, se calcula y se guarda
            if nia not in MAPA_NIA:
                MAPA_NIA[nia] = anonimizar_nia(nia)

            nuevos_valores.append(MAPA_NIA[nia])
        df[col] = nuevos_valores

    logger.info(f"NIA anonimizado en la tabla {tabla} (columnas: {columnas})")
    return df


def recorrerTablas(conexion, ultima_ejecucion: str):
    todo_ok = True
    for tabla in TABLAS:
        res = extraer_tabla(conexion, ultima_ejecucion, tabla)
        if res is None:
            todo_ok = False
            continue
        if res.empty:
            logger.warning(f"Sin datos para {tabla}, no se guarda")
            continue
        res = anonimizar_dataframe(res, tabla)
        guardar_tabla(res, tabla, ultima_ejecucion)
    return todo_ok


def guardar_fecha_ingesta():
    os.makedirs("data/control", exist_ok=True)
    anyo_actual = date.today().year
    with open("data/control/ultima_ingesta_db.txt", "w") as f:
        f.write(str(anyo_actual))


def main():
    conexion = conexionBD()
    if conexion:
        ultima_ejecucion = obtener_ultima_ejecucion()
        if recorrerTablas(conexion, ultima_ejecucion):
            guardar_fecha_ingesta()
        else:
            logger.warning("Hubo errores: no se actualiza la fecha de control")
        conexion.close()

if __name__ == "__main__":
    main()