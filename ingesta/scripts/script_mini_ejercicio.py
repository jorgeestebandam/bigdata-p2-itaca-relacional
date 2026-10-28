import psycopg2
import pandas as pd
import os
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv() 

def conexionBD():
    try:
        conexion = psycopg2.connect(
            host="127.0.0.1",
            port=5432,
            dbname= os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
        )
    except Exception as e:
        print(f"Error al conectar a la base de datos: {e}")
        conexion = None

    return conexion


def obtener_ultima_ejecucion():
    
    try:
        with open("data/control/ultima_ingesta_calificaciones.txt") as f:
            anyo = f.read().strip()
            if not anyo:
                anyo = "2020"

    except FileNotFoundError:
        print("Archivo de control no encontrado. Se utilizará el año por defecto.")
        anyo = "2020"

    return anyo


def guardar_fecha_ingesta() -> None:
    anyo_actual = date.today().year
    with open("data/control/ultima_ingesta_calificaciones.txt", "w") as f:
        f.write(str(anyo_actual))


def obtener_calificaciones(conexion, anyo_ultima_ejecucion):
    query = f"SELECT * FROM calificaciones WHERE anyo > '{anyo_ultima_ejecucion}'"
    try:
        res = pd.read_sql_query(query, conexion)
    except Exception as e:
        print(f"Error al ejecutar la consulta: {e}")
        res = pd.DataFrame()  # Retorna un DataFrame vacío en caso de error
    return res

def guardar_calificaciones_csv(calificaciones):
    if calificaciones.empty:
        print("No hay calificaciones para guardar.")
        return

    ruta = "data/raw/mini_ejercicio/calificaciones.csv"
    os.makedirs("data/raw/mini_ejercicio", exist_ok=True)
    existe = os.path.exists(ruta)

    calificaciones.to_csv(ruta, mode="a", header=not existe, index=False)
    print(f"Calificaciones añadidas a {ruta}")


if __name__ == "__main__":
   conexion = conexionBD()

   if conexion:
       print("Conexión exitosa a la base de datos.")
       anyo_ultima_ejecucion = obtener_ultima_ejecucion()
       print(f"Última ejecución: {anyo_ultima_ejecucion}")
       calificaciones = obtener_calificaciones(conexion, anyo_ultima_ejecucion)

       if calificaciones.empty:
              print("No se encontraron calificaciones nuevas desde la última ejecución.")
       else:
          guardar_calificaciones_csv(calificaciones)
          guardar_fecha_ingesta()
