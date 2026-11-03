"""
API web del sistema de red profesional multimodelo.
Expone los 7 casos de uso del TP para verlos desde una página web.
Cada caso de uso consulta la base que mejor se adapta a su tipo de dato.
"""
import os
from collections import OrderedDict

import psycopg2
import redis
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from neo4j import GraphDatabase
from pymongo import MongoClient

load_dotenv()

app = FastAPI(title="Red Profesional Multimodelo")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# CONEXIONES (los datos salen de variables de entorno)
# ============================================================

def conectar_postgres():
    return psycopg2.connect(os.environ["POSTGRES_URL"])

mongo_db = MongoClient(os.environ["MONGO_URI"])[os.getenv("MONGO_DB", "linkedin_db")]
redis_db = redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
neo4j_driver = GraphDatabase.driver(
    os.environ["NEO4J_URI"],
    auth=(os.getenv("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]),
)

def consulta_pg(sql, params=None):
    conn = conectar_postgres()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()

# ============================================================
# RESUMEN GENERAL
# ============================================================

@app.get("/api/resumen")
def resumen():
    usuarios, empresas, empleos = consulta_pg(
        "SELECT (SELECT COUNT(*) FROM usuario), (SELECT COUNT(*) FROM empresa), (SELECT COUNT(*) FROM empleo)"
    )[0]
    with neo4j_driver.session() as s:
        grafo = s.run(
            "MATCH (u:Usuario) WITH COUNT(u) AS nodos "
            "MATCH (:Usuario)-[r:CONECTADO_CON]->(:Usuario) RETURN nodos, COUNT(r) AS relaciones"
        ).single()
    return {
        "postgres": {"usuarios": usuarios, "empresas": empresas, "empleos": empleos},
        "mongo": {
            "publicaciones": mongo_db.publicaciones.count_documents({}),
            "mensajes": mongo_db.mensajes.count_documents({}),
        },
        "redis": {
            "habilidades": redis_db.zcard("habilidades_demandadas"),
            "empresas": redis_db.zcard("empresas_activas"),
            "regiones": redis_db.hlen("usuarios_por_region"),
        },
        "neo4j": {"usuarios": grafo["nodos"], "conexiones": grafo["relaciones"] // 2},
    }

# ============================================================
# CASOS DE USO
# ============================================================

@app.get("/api/cu1")
def cu1_usuarios_por_mes():
    """PostgreSQL: usuarios registrados, agrupados por mes."""
    filas = consulta_pg("""
        SELECT TO_CHAR(DATE_TRUNC('month', creadoen), 'YYYY-MM') AS mes, COUNT(*) AS total
        FROM usuario
        GROUP BY DATE_TRUNC('month', creadoen)
        ORDER BY DATE_TRUNC('month', creadoen)
    """)
    meses = [{"mes": m, "cantidad": c} for m, c in filas]
    return {"total": sum(m["cantidad"] for m in meses), "meses": meses}

@app.get("/api/cu2")
def cu2_habilidades_demandadas():
    """Redis: ranking de habilidades en un Sorted Set."""
    top = redis_db.zrevrange("habilidades_demandadas", 0, 4, withscores=True)
    return [{"nombre": h, "valor": int(p)} for h, p in top]

@app.get("/api/cu3")
def cu3_empresas_activas():
    """Redis: ranking de empresas que más contratan."""
    top = redis_db.zrevrange("empresas_activas", 0, 4, withscores=True)
    return [{"nombre": e, "valor": int(p)} for e, p in top]

@app.get("/api/usuarios")
def usuarios():
    filas = consulta_pg("SELECT idusuario, nombre, apellido FROM usuario ORDER BY idusuario")
    return [{"id": i, "nombre": f"{n} {a}"} for i, n, a in filas]

def a_json(valor):
    """Convierte fechas a texto para poder devolver el documento tal como está en MongoDB."""
    if isinstance(valor, dict):
        return {k: a_json(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [a_json(v) for v in valor]
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    return valor

@app.get("/api/cu4")
def cu4_recomendaciones(id_usuario: int = Query(..., alias="id")):
    """MongoDB: likes y comentarios recibidos en las publicaciones de un usuario.
    Los nombres de quienes comentan salen de PostgreSQL, unidos por el id de usuario."""
    publicaciones = list(mongo_db.publicaciones.find({"idUsuario": id_usuario}, {"_id": 0}).sort("creadoEn", -1))
    nombres = {i: f"{n} {a}" for i, n, a in consulta_pg("SELECT idusuario, nombre, apellido FROM usuario")}
    return {
        "likes": sum(p.get("likes", 0) for p in publicaciones),
        "comentarios": sum(len(p.get("comentarios", [])) for p in publicaciones),
        "publicaciones": [
            {
                "contenido": p["contenido"],
                "tipo": p.get("tipo", ""),
                "fecha": a_json(p.get("creadoEn")),
                "likes": p.get("likes", 0),
                "comentarios": [
                    {
                        "autor": nombres.get(c.get("idUsuario"), f"Usuario {c.get('idUsuario')}"),
                        "texto": c.get("texto", ""),
                        "fecha": a_json(c.get("fecha")),
                    }
                    for c in p.get("comentarios", [])
                ],
                "documento": a_json(p),
            }
            for p in publicaciones
        ],
    }

@app.get("/api/cu5")
def cu5_crecimiento_regional():
    """Redis: cantidad de usuarios por región en un Hash."""
    regiones = redis_db.hgetall("usuarios_por_region")
    orden = sorted(regiones.items(), key=lambda x: -int(x[1]))
    return [{"nombre": r, "valor": int(c)} for r, c in orden]

@app.get("/api/cu6")
def cu6_conexiones_y_amigos_comunes(
    min_conexiones: int = Query(70, ge=1),
    min_comun: int = Query(45, ge=1),
):
    """Neo4j: pares de usuarios muy conectados que comparten muchos contactos.
    Cada usuario tiene guardada su cantidad de conexiones (propiedad grado) para filtrar rápido,
    y Neo4j recorre los caminos a -> amigo en común -> b contando cuántos hay por par."""
    consulta = """
        MATCH (a:Usuario) WHERE a.grado >= $minCon
        MATCH (a)-[:CONECTADO_CON]->(c:Usuario)-[:CONECTADO_CON]->(b:Usuario)
        WHERE b.grado >= $minCon AND a.id < b.id
        WITH a, b, COUNT(c) AS enComun
        WHERE enComun >= $minComun
        RETURN a.nombre AS usuario1, b.nombre AS usuario2, enComun,
               a.grado AS gradoA, b.grado AS gradoB
        ORDER BY enComun DESC, usuario1, usuario2
        LIMIT 10
    """
    try:
        with neo4j_driver.session() as s:
            return s.run(consulta, minCon=min_conexiones, minComun=min_comun).data()
    except Exception as error:
        print("Error en el caso de uso 6:", error)
        raise HTTPException(
            status_code=503,
            detail="La consulta al grafo no pudo completarse. Probá de nuevo en unos segundos o con valores más altos.",
        )

@app.get("/api/red")
def red_base():
    """Neo4j: los usuarios principales y sus conexiones, para dibujar el grafo."""
    with neo4j_driver.session() as s:
        nodos = s.run("MATCH (u:Usuario) WHERE u.id < 100 RETURN u.id AS id, u.nombre AS nombre ORDER BY id").data()
        aristas = s.run(
            "MATCH (a:Usuario)-[:CONECTADO_CON]->(b:Usuario) "
            "WHERE a.id < 100 AND b.id < 100 AND a.id < b.id RETURN a.id AS a, b.id AS b"
        ).data()
    return {"nodos": nodos, "aristas": aristas}

@app.get("/api/cu7")
def cu7_habilidades_por_sector():
    """Redis: habilidades demandadas en tecnología o marketing."""
    sectores = OrderedDict([
        ("Tecnología", ["Python", "SQL", "React", "Docker", "Java", "Machine Learning", "Node.js", "AWS", "MongoDB"]),
        ("Marketing", ["Marketing Digital"]),
    ])
    resultado = []
    for sector, habilidades in sectores.items():
        items = []
        for h in habilidades:
            puntaje = redis_db.zscore("habilidades_demandadas", h)
            if puntaje:
                items.append({"nombre": h, "valor": int(puntaje)})
        resultado.append({"sector": sector, "habilidades": sorted(items, key=lambda i: -i["valor"])})
    return resultado

# ============================================================
# PÁGINA WEB
# ============================================================

@app.get("/")
def inicio():
    return FileResponse(os.path.join(BASE_DIR, "static", "index.html"))

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
