from neo4j import GraphDatabase
import random

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "secret123"))

TOTAL_USUARIOS = 600
CONEXIONES_POR_USUARIO = 520  # asegura que superen 500

nombres = [
    "Juan", "Maria", "Carlos", "Ana", "Pedro", "Laura", "Miguel", "Sofia",
    "Jorge", "Lucia", "Roberto", "Valeria", "Fernando", "Natalia", "Gabriel",
    "Daniela", "Alejandro", "Camila", "Sebastian", "Paola", "Nicolas", "Romina",
    "Andres", "Florencia", "Martin", "Agustina", "Federico", "Carolina", "Ignacio",
    "Vanesa", "Marcos", "Jimena", "Pablo", "Silvina", "Ricardo", "Veronica"
]

def generar_nombre(i):
    base = nombres[i % len(nombres)]
    return f"{base}_{i}"

print("Conectando a Neo4j...")

with driver.session() as session:

    # Borrar solo los usuarios generados anteriormente (los que tienen id >= 100)
    session.run("MATCH (u:Usuario) WHERE u.id >= 100 DETACH DELETE u")
    print("Usuarios anteriores limpiados.")

    # Crear 600 usuarios nuevos con IDs desde 100
    print(f"Creando {TOTAL_USUARIOS} usuarios...")
    for i in range(TOTAL_USUARIOS):
        uid = 100 + i
        nombre = generar_nombre(i)
        session.run("CREATE (:Usuario {id: $id, nombre: $nombre})", id=uid, nombre=nombre)

    print("Usuarios creados.")

    # Obtener todos los IDs de usuarios generados
    result = session.run("MATCH (u:Usuario) WHERE u.id >= 100 RETURN u.id AS id")
    ids = [r["id"] for r in result]

    print(f"Creando conexiones (cada usuario conectado con ~{CONEXIONES_POR_USUARIO} otros)...")

    # Para cada usuario, conectarlo con 520 usuarios aleatorios distintos
    for uid in ids:
        candidatos = [x for x in ids if x != uid]
        elegidos = random.sample(candidatos, min(CONEXIONES_POR_USUARIO, len(candidatos)))
        for otro in elegidos:
            session.run("""
                MATCH (a:Usuario {id: $id1}), (b:Usuario {id: $id2})
                MERGE (a)-[:CONECTADO_CON]->(b)
                MERGE (b)-[:CONECTADO_CON]->(a)
            """, id1=uid, id2=otro)

        if ids.index(uid) % 50 == 0:
            print(f"  Procesados {ids.index(uid)}/{len(ids)} usuarios...")

print("Datos generados correctamente.")
print(f"Total usuarios en el sistema con id >= 100: {len(ids)}")
print("Ahora ejecuta el CU6 desde main.py para ver los resultados.")

driver.close()
