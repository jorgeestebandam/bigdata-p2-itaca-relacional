# Proyecto 2 · Analítica académica ITACA (relacional)

> Análisis de datos académicos a partir de una base de datos PostgreSQL (réplica de ITACA) vía JDBC.

## Descripción y objetivo

El mismo objetivo que el [Proyecto 1](https://github.com/jorgeestebandam/bigdata-p1-itaca), pero partiendo de una base de datos **PostgreSQL** (réplica de **ITACA**) accedida mediante **JDBC**, en lugar de ficheros XML.

Se mantiene el mismo modelo de datos (alumnado, cursos, módulos y calificaciones) y el mismo dashboard final. Cambian el origen de los datos y el almacenamiento intermedio.

> [!NOTE]
> Los datos de alumnado deben estar siempre anonimizados.

## Arquitectura

*Diagrama provisional del Bloque 0. Se actualizará al terminar cada bloque.*

```mermaid
graph LR
    A[(PostgreSQL ITACA)] -->|JDBC| B[Ingesta]
    B --> C[ETL]
    C --> D[(Almacenamiento intermedio)]
    D --> E[Dashboard]
```

## Fuentes de datos

| Fuente | URL / origen | Formato | Frecuencia de actualización | Licencia | Última ingesta |
|---|---|---|---|---|---|
| Réplica PostgreSQL de ITACA | Conexión JDBC | Base de datos relacional | Pendiente | Pendiente | Pendiente |

## Estructura del repositorio

| Carpeta | Contenido |
|---|---|
| `ingesta/` | Extracción de datos desde PostgreSQL mediante JDBC |
| `etl/` | Transformación, limpieza y carga en el almacenamiento intermedio |
| `dashboard/` | Visualización y análisis de los datos |
| `docs/` | Capturas y diagramas |

## Cómo desplegar el entorno

Pendiente de completar cuando se defina la conexión a PostgreSQL y el almacenamiento intermedio.

## Bitácora de prácticas

### Bloque 0 · Entorno

**Objetivo:** dejar preparado el repositorio Git independiente del proyecto, con su estructura de carpetas, `.gitignore` y README inicial.

**Pasos realizados:**

1. Creación del repositorio con `git init` y la rama `main`.
2. Creación de las carpetas `ingesta/`, `etl/`, `dashboard/` y `docs/`.
3. Configuración del `.gitignore`.
4. Redacción del README inicial.
5. Primer commit y publicación en GitHub.

**Problemas encontrados y solución:** ninguno por ahora.

**Resultado:** repositorio publicado en GitHub con la estructura inicial.

## Equipo

- Jorge Esteban García