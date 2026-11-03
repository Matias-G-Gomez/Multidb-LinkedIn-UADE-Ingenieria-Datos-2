"""
Carga los datos de demostración en las cuatro bases en la nube.
Se ejecuta una sola vez desde tu compu (o cuando quieras reiniciar la demo):

    python cargar_datos.py

Usa las mismas variables de entorno que la API (archivo .env).
"""
import os
import random
from datetime import datetime, timezone

import psycopg2
import redis
from dotenv import load_dotenv
from neo4j import GraphDatabase
from pymongo import MongoClient

load_dotenv()

# Algunos proveedores de internet no resuelven las direcciones mongodb+srv:// de Atlas.
# Se usan DNS públicos para evitar el error "querySrv ECONNREFUSED" al correr el script en local.
try:
    import dns.resolver
    dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
    dns.resolver.default_resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
except ImportError:
    pass
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQL_INICIAL = os.path.join(BASE_DIR, "..", "init-scripts", "postgres_init.sql")

# Tamaño del grafo de demostración (el TP original usa 600 usuarios con 520 conexiones;
# acá se usa un grafo más chico para que las consultas respondan rápido en el plan gratuito)
USUARIOS_GRAFO = 150
CONEXIONES_POR_USUARIO = 40


def cargar_postgres():
    print("PostgreSQL: creando tablas y datos...")
    conn = psycopg2.connect(os.environ["POSTGRES_URL"])
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("""
            DROP TABLE IF EXISTS usuario_habilidad, habilidad, educacion, experiencia_laboral,
                                 postulacion, empleo, empresa, usuario CASCADE
        """)
        with open(SQL_INICIAL, encoding="utf-8") as f:
            cur.execute(f.read())
        cur.execute("SELECT COUNT(*) FROM usuario")
        print(f"  {cur.fetchone()[0]} usuarios cargados")
    conn.close()


def cargar_mongo():
    print("MongoDB: cargando publicaciones y mensajes...")
    db = MongoClient(os.environ["MONGO_URI"])[os.getenv("MONGO_DB", "linkedin_db")]
    db.publicaciones.drop()
    db.mensajes.drop()
    utc = timezone.utc
    db.publicaciones.insert_many([
        {"idUsuario": 1, "contenido": "Muy contento de empezar en mi nuevo trabajo!", "tipo": "texto",
         "creadoEn": datetime(2025, 4, 1, tzinfo=utc), "likes": 15,
         "comentarios": [{"idUsuario": 2, "texto": "Felicitaciones!", "fecha": datetime(2025, 4, 1, tzinfo=utc)},
                         {"idUsuario": 3, "texto": "Genial!", "fecha": datetime(2025, 4, 2, tzinfo=utc)}]},
        {"idUsuario": 2, "contenido": "Compartiendo mi experiencia con Python.", "tipo": "articulo",
         "creadoEn": datetime(2025, 3, 15, tzinfo=utc), "likes": 42,
         "comentarios": [{"idUsuario": 1, "texto": "Muy util!", "fecha": datetime(2025, 3, 16, tzinfo=utc)}]},
        {"idUsuario": 3, "contenido": "Buscando oportunidades en frontend.", "tipo": "texto",
         "creadoEn": datetime(2025, 2, 10, tzinfo=utc), "likes": 8, "comentarios": []},
        {"idUsuario": 5, "contenido": "Docker cambio mi forma de trabajar.", "tipo": "texto",
         "creadoEn": datetime(2025, 1, 20, tzinfo=utc), "likes": 31,
         "comentarios": [{"idUsuario": 4, "texto": "De acuerdo!", "fecha": datetime(2025, 1, 21, tzinfo=utc)}]},
    ])
    db.mensajes.insert_many([
        {"idRemitente": 1, "idDestinatario": 2, "contenido": "Hola Diego, como estas?",
         "fechaEnvio": datetime(2025, 4, 5, tzinfo=utc), "leido": True},
        {"idRemitente": 2, "idDestinatario": 1, "contenido": "Todo bien! Nos juntamos?",
         "fechaEnvio": datetime(2025, 4, 5, tzinfo=utc), "leido": False},
        {"idRemitente": 3, "idDestinatario": 5, "contenido": "Vi tu post sobre Docker, me ayudo mucho.",
         "fechaEnvio": datetime(2025, 4, 6, tzinfo=utc), "leido": True},
    ])
    print(f"  {db.publicaciones.count_documents({})} publicaciones cargadas")


def cargar_redis():
    print("Redis: cargando rankings y conteos...")
    r = redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    r.delete("habilidades_demandadas", "empresas_activas", "usuarios_por_region")
    r.zadd("habilidades_demandadas", {"Python": 18, "SQL": 15, "React": 12, "Docker": 10, "Java": 9,
                                      "Machine Learning": 7, "Node.js": 6, "AWS": 5, "MongoDB": 4,
                                      "Marketing Digital": 3})
    r.zadd("empresas_activas", {"MercadoLibre": 8, "Globant": 7, "Google": 6, "Accenture": 5,
                                "Despegar": 4, "Santander": 3})
    r.hset("usuarios_por_region", mapping={"Buenos Aires": 5, "Cordoba": 2, "Rosario": 1, "Mendoza": 1})
    print(f"  {r.zcard('habilidades_demandadas')} habilidades cargadas")


def cargar_neo4j():
    print("Neo4j: creando el grafo de usuarios...")
    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]),
    )
    with driver.session() as s:
        # Solo borra nodos :Usuario, así no toca otros datos que haya en la misma base
        s.run("MATCH (u:Usuario) DETACH DELETE u")

        # Usuarios principales del TP y sus conexiones
        base = [(1, "Matias"), (2, "Diego"), (3, "Valentina"), (4, "Lucas"),
                (5, "Sofia"), (6, "Andres"), (7, "Camila"), (8, "Facundo")]
        s.run("UNWIND $usuarios AS u CREATE (:Usuario {id: u[0], nombre: u[1]})", usuarios=base)
        pares = [(1, 2), (1, 3), (1, 5), (2, 3), (2, 4), (2, 6), (3, 5), (3, 7), (4, 6), (4, 8), (5, 7), (6, 8)]
        s.run("""
            UNWIND $pares AS p
            MATCH (a:Usuario {id: p[0]}), (b:Usuario {id: p[1]})
            CREATE (a)-[:CONECTADO_CON]->(b), (b)-[:CONECTADO_CON]->(a)
        """, pares=pares)

        # Usuarios generados para el caso de uso 6 (semilla fija: siempre el mismo grafo)
        nombres = ["Juan", "Maria", "Carlos", "Ana", "Pedro", "Laura", "Miguel", "Sofia", "Jorge", "Lucia",
                   "Roberto", "Valeria", "Fernando", "Natalia", "Gabriel", "Daniela", "Alejandro", "Camila",
                   "Sebastian", "Paola", "Nicolas", "Romina", "Andres", "Florencia", "Martin", "Agustina",
                   "Federico", "Carolina", "Ignacio", "Vanesa", "Marcos", "Jimena", "Pablo", "Silvina",
                   "Ricardo", "Veronica"]
        random.seed(42)
        ids = list(range(100, 100 + USUARIOS_GRAFO))
        s.run("UNWIND $usuarios AS u CREATE (:Usuario {id: u.id, nombre: u.nombre})",
              usuarios=[{"id": uid, "nombre": f"{nombres[i % len(nombres)]}_{i}"} for i, uid in enumerate(ids)])
        s.run("CREATE INDEX usuario_id IF NOT EXISTS FOR (u:Usuario) ON (u.id)")

        conexiones = set()
        for uid in ids:
            for otro in random.sample([x for x in ids if x != uid], CONEXIONES_POR_USUARIO):
                conexiones.add((min(uid, otro), max(uid, otro)))
        conexiones = [list(c) for c in conexiones]
        for i in range(0, len(conexiones), 1000):
            s.run("""
                UNWIND $pares AS p
                MATCH (a:Usuario {id: p[0]}), (b:Usuario {id: p[1]})
                CREATE (a)-[:CONECTADO_CON]->(b), (b)-[:CONECTADO_CON]->(a)
            """, pares=conexiones[i:i + 1000])
        total = s.run("MATCH (u:Usuario) RETURN COUNT(u) AS t").single()["t"]
        print(f"  {total} usuarios y {len(conexiones) + len(pares)} conexiones cargadas")
    driver.close()


if __name__ == "__main__":
    cargar_postgres()
    cargar_mongo()
    cargar_redis()
    cargar_neo4j()
    print("\nListo: las cuatro bases tienen los datos de demostración.")
