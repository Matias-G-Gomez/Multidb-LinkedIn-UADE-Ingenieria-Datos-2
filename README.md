# LinkedIn TP — Sistema de Gestión de Red Profesional

Trabajo Práctico de Ingeniería de Datos 2 — UADE 2026

Sistema de gestión de datos para una red profesional tipo LinkedIn, implementado con bases de datos relacionales y no relacionales integradas en contenedores Docker. La aplicación expone un menú interactivo en Python para gestionar entidades y ejecutar casos de uso analíticos, con sincronización automática entre bases de datos.

---

## Tecnologías utilizadas

| Tecnología | Rol en el sistema |
|---|---|
| PostgreSQL 15 | Base relacional — entidades del modelo de negocio |
| MongoDB 7 | Base de documentos — publicaciones y mensajes |
| Redis 7 | Base clave-valor en memoria — rankings y conteos |
| Neo4j 5 | Base de grafos — red de conexiones entre usuarios |
| Python 3 | Aplicación principal e intermediario entre bases |
| Docker Compose | Orquestación de contenedores |

---

## Arquitectura

El sistema utiliza cuatro bases de datos, cada una en su propio contenedor Docker. Python se conecta a todas simultáneamente y garantiza la sincronización entre ellas en cada operación.

```
App Python
    |
    |---> PostgreSQL  (entidades del DLR con integridad referencial)
    |---> MongoDB     (publicaciones y mensajes con documentos embebidos)
    |---> Redis       (rankings en Sorted Set y conteos en Hash)
    |---> Neo4j       (grafo de conexiones entre usuarios)
```

Criterio de distribución:
- Datos de negocio con relaciones estructuradas: PostgreSQL
- Casos de uso analíticos: MongoDB, Redis o Neo4j según la naturaleza de la consulta

---

## Requisitos previos

- Docker Desktop instalado y corriendo
- Python 3 instalado
- Librerías Python necesarias:

```
pip install psycopg2-binary pymongo redis neo4j
```

---

## Instalación y puesta en marcha

1. Clonar el repositorio:

```
git clone https://github.com/TU_USUARIO/TU_REPO.git
cd linkedin-tp
```

2. Levantar los contenedores:

```
docker compose up -d
```

La primera vez descarga las imágenes (puede tardar unos minutos). Verificar que todos estén corriendo:

```
docker compose ps
```

Todos los contenedores deben aparecer con estado healthy o running.

3. Ejecutar la aplicación:

```
python app/main.py
```

El programa se conecta automáticamente a las cuatro bases, verifica si ya tienen datos cargados y los inicializa si es necesario.

---

## Interfaces visuales

Una vez levantados los contenedores, las interfaces gráficas de cada base están disponibles en el navegador:

| Base | URL | Credenciales |
|---|---|---|
| Neo4j Browser | http://localhost:7474 | neo4j / secret123 |
| Mongo Express | http://localhost:8081 | sin credenciales |
| Redis Commander | http://localhost:8082 | sin credenciales |
| pgAdmin | http://localhost:8083 | admin@admin.com / secret123 |

Para conectar pgAdmin a la base: click derecho en Servers, Register Server, y completar con Host: postgres, Port: 5432, Database: linkedin_db, Username: admin, Password: secret123.

---

## Estructura del proyecto

```
linkedin-tp/
    docker-compose.yml          Orquestación de los 7 contenedores
    generar_datos_neo4j.py      Script para generar datos masivos en Neo4j (CU6)
    app/
        main.py                 Aplicación principal con menú interactivo
    init-scripts/
        postgres_init.sql       Creación de tablas y datos de prueba
```

---

## Menú de la aplicación

El menú principal está dividido en dos secciones:

**Gestionar** — permite crear, modificar y eliminar entidades:
- Usuarios, Empresas, Empleos, Postulaciones
- Experiencia laboral, Educación, Habilidades
- Habilidades por usuario, Habilidades por empleo
- Publicaciones y mensajes

Cada operación actualiza automáticamente todas las bases afectadas. Por ejemplo, crear un usuario inserta en PostgreSQL, crea el nodo en Neo4j e incrementa el conteo de región en Redis.

**Casos de uso** — ejecuta las siete consultas analíticas del sistema.

---

## Casos de uso

| CU | Descripción | Base |
|---|---|---|
| CU1 | Usuarios registrados en el último año | PostgreSQL |
| CU2 | Habilidades más solicitadas en ofertas de trabajo | Redis |
| CU3 | Empresas que más contratan | Redis |
| CU4 | Recomendaciones recibidas por un usuario | MongoDB |
| CU5 | Crecimiento de usuarios por región geográfica | Redis |
| CU6 | Pares de usuarios con más de 500 conexiones y 10 amigos en común | Neo4j |
| CU7 | Habilidades demandadas en tecnología o marketing | Redis |

---

## Generación de datos para CU6

El caso de uso 6 requiere usuarios con más de 500 conexiones para demostrar el traversal de grafos con datos reales. Para generarlos:

```
python generar_datos_neo4j.py
```

El script crea 600 usuarios con IDs desde 100 en adelante y los conecta con más de 500 conexiones aleatorias cada uno. Los 8 usuarios originales no se modifican. El proceso puede tardar varios minutos.

---

## Puertos utilizados

| Servicio | Puerto externo | Puerto interno | Nota |
|---|---|---|---|
| PostgreSQL | 5432 | 5432 | Puerto estándar |
| MongoDB | 27018 | 27017 | 27017 ocupado por instalación local |
| Redis | 6380 | 6379 | 6379 ocupado por instalación local |
| Neo4j Browser | 7474 | 7474 | Puerto estándar |
| Neo4j Bolt | 7687 | 7687 | Puerto estándar |
| pgAdmin | 8083 | 80 | Interfaz web |
| Mongo Express | 8081 | 8081 | Interfaz web |
| Redis Commander | 8082 | 8081 | Interfaz web |

---

## Sincronización entre bases de datos

Las bases no se comunican entre sí directamente. Python actúa como único intermediario y ejecuta las actualizaciones necesarias en cada base de forma secuencial después de cada operación. La persistencia está garantizada por volúmenes Docker que sobreviven a reinicios de contenedores.

---

## Materia y grupo

Ingeniería de Datos 2 — UADE 2026 — Grupo 2
