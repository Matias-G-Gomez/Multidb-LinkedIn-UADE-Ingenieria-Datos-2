import psycopg2
from pymongo import MongoClient
from datetime import datetime, timezone
import redis
from neo4j import GraphDatabase

# ============================================================
# CONEXIONES
# ============================================================

def conectar_postgres():
    return psycopg2.connect(
        host="localhost", port=5432,
        dbname="linkedin_db", user="admin", password="secret123"
    )

def conectar_mongo():
    cliente = MongoClient("mongodb://localhost:27017/")
    return cliente["linkedin_db"]

def conectar_redis():
    return redis.Redis(host="localhost", port=6380, decode_responses=True)

def conectar_neo4j():
    return GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "secret123"))

# ============================================================
# SETUP MONGODB
# ============================================================

def setup_mongodb(db):
    print("\nVerificando datos en MongoDB...")
    if db.publicaciones.count_documents({}) > 0:
        print(f"  MongoDB ya tiene datos, omitiendo setup inicial.")
        return
    print("  Primera vez, cargando datos iniciales...")
    db.publicaciones.insert_many([
        {"idUsuario": 1, "contenido": "Muy contento de empezar en mi nuevo trabajo!", "tipo": "texto",
         "creadoEn": datetime(2025, 4, 1, tzinfo=timezone.utc), "likes": 15,
         "comentarios": [{"idUsuario": 2, "texto": "Felicitaciones!", "fecha": datetime(2025, 4, 1, tzinfo=timezone.utc)},
                         {"idUsuario": 3, "texto": "Genial!", "fecha": datetime(2025, 4, 2, tzinfo=timezone.utc)}]},
        {"idUsuario": 2, "contenido": "Compartiendo mi experiencia con Python.", "tipo": "articulo",
         "creadoEn": datetime(2025, 3, 15, tzinfo=timezone.utc), "likes": 42,
         "comentarios": [{"idUsuario": 1, "texto": "Muy util!", "fecha": datetime(2025, 3, 16, tzinfo=timezone.utc)}]},
        {"idUsuario": 3, "contenido": "Buscando oportunidades en frontend.", "tipo": "texto",
         "creadoEn": datetime(2025, 2, 10, tzinfo=timezone.utc), "likes": 8, "comentarios": []},
        {"idUsuario": 5, "contenido": "Docker cambio mi forma de trabajar.", "tipo": "texto",
         "creadoEn": datetime(2025, 1, 20, tzinfo=timezone.utc), "likes": 31,
         "comentarios": [{"idUsuario": 4, "texto": "De acuerdo!", "fecha": datetime(2025, 1, 21, tzinfo=timezone.utc)}]}
    ])
    db.mensajes.insert_many([
        {"idRemitente": 1, "idDestinatario": 2, "contenido": "Hola Diego, como estas?",
         "fechaEnvio": datetime(2025, 4, 5, tzinfo=timezone.utc), "leido": True},
        {"idRemitente": 2, "idDestinatario": 1, "contenido": "Todo bien! Nos juntamos?",
         "fechaEnvio": datetime(2025, 4, 5, tzinfo=timezone.utc), "leido": False},
        {"idRemitente": 3, "idDestinatario": 5, "contenido": "Vi tu post sobre Docker, me ayudo mucho.",
         "fechaEnvio": datetime(2025, 4, 6, tzinfo=timezone.utc), "leido": True}
    ])
    print("  Publicaciones y mensajes cargados en MongoDB")

# ============================================================
# SETUP REDIS
# ============================================================

def setup_redis(r):
    print("\nVerificando datos en Redis...")
    if r.exists("habilidades_demandadas"):
        print("  Redis ya tiene datos, omitiendo setup inicial.")
        return
    print("  Primera vez, cargando datos iniciales...")
    for h, p in {"Python": 18, "SQL": 15, "React": 12, "Docker": 10, "Java": 9,
                 "Machine Learning": 7, "Node.js": 6, "AWS": 5, "MongoDB": 4, "Marketing Digital": 3}.items():
        r.zadd("habilidades_demandadas", {h: p})
    for e, p in {"MercadoLibre": 8, "Globant": 7, "Google": 6, "Accenture": 5, "Despegar": 4, "Santander": 3}.items():
        r.zadd("empresas_activas", {e: p})
    for reg, cant in {"Buenos Aires": 5, "Cordoba": 2, "Rosario": 1, "Mendoza": 1}.items():
        r.hset("usuarios_por_region", reg, cant)
    print("  Rankings y conteos cargados en Redis")

# ============================================================
# SETUP NEO4J
# ============================================================

def setup_neo4j(driver):
    print("\nVerificando datos en Neo4j...")
    with driver.session() as session:
        resultado = session.run("MATCH (u:Usuario) RETURN COUNT(u) AS total")
        total = resultado.single()["total"]
        if total > 0:
            print(f"  Neo4j ya tiene {total} nodos, omitiendo setup inicial.")
            return
        print("  Primera vez, cargando datos iniciales...")
        for uid, nombre in [(1,"Matias"),(2,"Diego"),(3,"Valentina"),(4,"Lucas"),
                            (5,"Sofia"),(6,"Andres"),(7,"Camila"),(8,"Facundo")]:
            session.run("CREATE (:Usuario {id: $id, nombre: $nombre})", id=uid, nombre=nombre)
        for u1, u2 in [(1,2),(1,3),(1,5),(2,3),(2,4),(2,6),(3,5),(3,7),(4,6),(4,8),(5,7),(6,8)]:
            session.run("""
                MATCH (a:Usuario {id: $id1}), (b:Usuario {id: $id2})
                CREATE (a)-[:CONECTADO_CON]->(b)
                CREATE (b)-[:CONECTADO_CON]->(a)
            """, id1=u1, id2=u2)
    print("  Nodos y conexiones cargados en Neo4j")

# ============================================================
# HELPERS
# ============================================================

def separador(titulo=""):
    print("\n" + "="*55)
    if titulo:
        print(titulo)
        print("="*55)

def pedir(campo, requerido=True, tipo=str, puede_vacio=False):
    while True:
        valor = input(f"  {campo}: ").strip()
        if valor == "" and puede_vacio:
            return None
        if valor == "" and requerido:
            print(f"  El campo '{campo}' es obligatorio.")
            continue
        if tipo == int:
            try:
                return int(valor)
            except ValueError:
                print("  Debe ser un numero entero.")
                continue
        return valor

def listar_registros(cur, tabla, campos, titulo):
    separador(titulo)
    cur.execute(f"SELECT {', '.join(campos)} FROM {tabla} ORDER BY 1")
    filas = cur.fetchall()
    if not filas:
        print("  No hay registros.")
        return
    for fila in filas:
        print("  " + " | ".join(str(v) if v is not None else "-" for v in fila))

# ============================================================
# SINCRONIZACION CON BASES NOSQL
# ============================================================

def neo4j_crear_usuario(driver, uid, nombre):
    with driver.session() as session:
        session.run("CREATE (:Usuario {id: $id, nombre: $nombre})", id=uid, nombre=nombre)

def neo4j_actualizar_usuario(driver, uid, nombre):
    with driver.session() as session:
        session.run("MATCH (u:Usuario {id: $id}) SET u.nombre = $nombre", id=uid, nombre=nombre)

def neo4j_eliminar_usuario(driver, uid):
    with driver.session() as session:
        session.run("MATCH (u:Usuario {id: $id}) DETACH DELETE u", id=uid)

def redis_agregar_region(r, ubicacion):
    if ubicacion:
        r.hincrby("usuarios_por_region", ubicacion, 1)

def redis_actualizar_region(r, ubicacion_vieja, ubicacion_nueva):
    if ubicacion_vieja:
        actual = int(r.hget("usuarios_por_region", ubicacion_vieja) or 0)
        if actual > 1:
            r.hincrby("usuarios_por_region", ubicacion_vieja, -1)
        else:
            r.hdel("usuarios_por_region", ubicacion_vieja)
    if ubicacion_nueva:
        r.hincrby("usuarios_por_region", ubicacion_nueva, 1)

def redis_eliminar_region(r, ubicacion):
    if ubicacion:
        actual = int(r.hget("usuarios_por_region", ubicacion) or 0)
        if actual > 1:
            r.hincrby("usuarios_por_region", ubicacion, -1)
        else:
            r.hdel("usuarios_por_region", ubicacion)

def redis_agregar_empresa(r, nombre):
    if nombre:
        r.zadd("empresas_activas", {nombre: 0}, nx=True)

def redis_actualizar_empresa(r, nombre_viejo, nombre_nuevo):
    if nombre_viejo and nombre_nuevo and nombre_viejo != nombre_nuevo:
        puntaje = r.zscore("empresas_activas", nombre_viejo) or 0
        r.zrem("empresas_activas", nombre_viejo)
        r.zadd("empresas_activas", {nombre_nuevo: puntaje})

def redis_eliminar_empresa(r, nombre):
    if nombre:
        r.zrem("empresas_activas", nombre)

def redis_agregar_empleo(r, nombre_empresa):
    if nombre_empresa:
        r.zincrby("empresas_activas", 1, nombre_empresa)

def redis_eliminar_empleo(r, nombre_empresa):
    if nombre_empresa:
        actual = r.zscore("empresas_activas", nombre_empresa) or 0
        if actual > 0:
            r.zincrby("empresas_activas", -1, nombre_empresa)

def redis_agregar_habilidad(r, nombre):
    if nombre:
        r.zadd("habilidades_demandadas", {nombre: 0}, nx=True)

def redis_actualizar_habilidad(r, nombre_viejo, nombre_nuevo):
    if nombre_viejo and nombre_nuevo and nombre_viejo != nombre_nuevo:
        puntaje = r.zscore("habilidades_demandadas", nombre_viejo) or 0
        r.zrem("habilidades_demandadas", nombre_viejo)
        r.zadd("habilidades_demandadas", {nombre_nuevo: puntaje})

def redis_eliminar_habilidad(r, nombre):
    if nombre:
        r.zrem("habilidades_demandadas", nombre)

def redis_asignar_habilidad(r, nombre_habilidad):
    if nombre_habilidad:
        r.zincrby("habilidades_demandadas", 1, nombre_habilidad)

def redis_quitar_habilidad(r, nombre_habilidad):
    if nombre_habilidad:
        actual = r.zscore("habilidades_demandadas", nombre_habilidad) or 0
        if actual > 0:
            r.zincrby("habilidades_demandadas", -1, nombre_habilidad)

# ============================================================
# CRUD - USUARIO
# ============================================================

def menu_usuario(pg, driver, r):
    while True:
        separador("GESTION DE USUARIOS")
        print("  1. Listar usuarios")
        print("  2. Crear usuario")
        print("  3. Modificar usuario")
        print("  4. Eliminar usuario")
        print("  5. Conectar dos usuarios")
        print("  6. Eliminar conexion entre usuarios")
        print("  0. Volver")
        op = input("\n  Opcion: ").strip()
        cur = pg.cursor()

        if op == "1":
            listar_registros(cur, "usuario",
                ["idusuario","nombre","apellido","email","fechanacimiento","ubicacion","creadoen"],
                "LISTA DE USUARIOS")

        elif op == "2":
            separador("CREAR USUARIO")
            nombre    = pedir("Nombre")
            apellido  = pedir("Apellido")
            email     = pedir("Email")
            fecha     = pedir("Fecha de nacimiento (YYYY-MM-DD)", puede_vacio=True)
            ubicacion = pedir("Ubicacion", puede_vacio=True)
            cur.execute("""
                INSERT INTO usuario (nombre, apellido, email, fechanacimiento, ubicacion)
                VALUES (%s, %s, %s, %s, %s) RETURNING idusuario
            """, (nombre, apellido, email, fecha, ubicacion))
            nuevo_id = cur.fetchone()[0]
            pg.commit()
            # Sincronizar Neo4j y Redis
            neo4j_crear_usuario(driver, nuevo_id, nombre)
            redis_agregar_region(r, ubicacion)
            print(f"\n  Usuario creado con ID {nuevo_id}.")
            print(f"  Sincronizado en Neo4j (nodo) y Redis (region).")

        elif op == "3":
            listar_registros(cur, "usuario", ["idusuario","nombre","apellido","email","ubicacion"], "USUARIOS")
            uid = pedir("ID del usuario a modificar", tipo=int)
            cur.execute("SELECT nombre, ubicacion FROM usuario WHERE idusuario=%s", (uid,))
            fila = cur.fetchone()
            if not fila:
                print("  Usuario no encontrado.")
                continue
            nombre_actual, ubicacion_actual = fila
            print("  Dejar en blanco para mantener el valor actual:")
            nombre    = pedir("Nuevo nombre", puede_vacio=True)
            apellido  = pedir("Nuevo apellido", puede_vacio=True)
            email     = pedir("Nuevo email", puede_vacio=True)
            ubicacion = pedir("Nueva ubicacion", puede_vacio=True)
            if nombre:    cur.execute("UPDATE usuario SET nombre=%s WHERE idusuario=%s", (nombre, uid))
            if apellido:  cur.execute("UPDATE usuario SET apellido=%s WHERE idusuario=%s", (apellido, uid))
            if email:     cur.execute("UPDATE usuario SET email=%s WHERE idusuario=%s", (email, uid))
            if ubicacion: cur.execute("UPDATE usuario SET ubicacion=%s WHERE idusuario=%s", (ubicacion, uid))
            pg.commit()
            # Sincronizar Neo4j y Redis
            if nombre:
                neo4j_actualizar_usuario(driver, uid, nombre)
            if ubicacion:
                redis_actualizar_region(r, ubicacion_actual, ubicacion)
            print("  Usuario actualizado.")
            print("  Sincronizado en Neo4j y Redis.")

        elif op == "4":
            listar_registros(cur, "usuario", ["idusuario","nombre","apellido","ubicacion"], "USUARIOS")
            uid = pedir("ID del usuario a eliminar", tipo=int)
            cur.execute("SELECT nombre, ubicacion FROM usuario WHERE idusuario=%s", (uid,))
            fila = cur.fetchone()
            if not fila:
                print("  Usuario no encontrado.")
                continue
            nombre_actual, ubicacion_actual = fila
            if input(f"  Confirmar eliminacion del usuario {uid}? (s/n): ").strip().lower() == "s":
                cur.execute("DELETE FROM usuario WHERE idusuario=%s", (uid,))
                pg.commit()
                # Sincronizar Neo4j y Redis
                neo4j_eliminar_usuario(driver, uid)
                redis_eliminar_region(r, ubicacion_actual)
                print("  Usuario eliminado.")
                print("  Sincronizado en Neo4j y Redis.")
            else:
                print("  Cancelado.")

        elif op == "5":
            separador("CONECTAR USUARIOS")
            listar_registros(cur, "usuario", ["idusuario","nombre","apellido"], "USUARIOS")
            uid1 = pedir("ID del primer usuario", tipo=int)
            uid2 = pedir("ID del segundo usuario", tipo=int)
            with driver.session() as session:
                session.run("""
                    MATCH (a:Usuario {id: $id1}), (b:Usuario {id: $id2})
                    MERGE (a)-[:CONECTADO_CON]->(b)
                    MERGE (b)-[:CONECTADO_CON]->(a)
                """, id1=uid1, id2=uid2)
            print(f"  Conexion creada entre usuario {uid1} y usuario {uid2} en Neo4j.")

        elif op == "6":
            separador("ELIMINAR CONEXION")
            listar_registros(cur, "usuario", ["idusuario","nombre","apellido"], "USUARIOS")
            uid1 = pedir("ID del primer usuario", tipo=int)
            uid2 = pedir("ID del segundo usuario", tipo=int)
            with driver.session() as session:
                session.run("""
                    MATCH (a:Usuario {id: $id1})-[r:CONECTADO_CON]-(b:Usuario {id: $id2})
                    DELETE r
                """, id1=uid1, id2=uid2)
            print(f"  Conexion eliminada entre usuario {uid1} y usuario {uid2} en Neo4j.")

        elif op == "0":
            break

# ============================================================
# CRUD - EMPRESA
# ============================================================

def menu_empresa(pg, r):
    while True:
        separador("GESTION DE EMPRESAS")
        print("  1. Listar empresas")
        print("  2. Crear empresa")
        print("  3. Modificar empresa")
        print("  4. Eliminar empresa")
        print("  0. Volver")
        op = input("\n  Opcion: ").strip()
        cur = pg.cursor()

        if op == "1":
            listar_registros(cur, "empresa", ["idempresa","nombre","ubicacion","rubro"], "LISTA DE EMPRESAS")

        elif op == "2":
            separador("CREAR EMPRESA")
            nombre      = pedir("Nombre")
            descripcion = pedir("Descripcion", puede_vacio=True)
            ubicacion   = pedir("Ubicacion", puede_vacio=True)
            rubro       = pedir("Rubro", puede_vacio=True)
            cur.execute("INSERT INTO empresa (nombre, descripcion, ubicacion, rubro) VALUES (%s,%s,%s,%s) RETURNING idempresa",
                        (nombre, descripcion, ubicacion, rubro))
            nuevo_id = cur.fetchone()[0]
            pg.commit()
            # Sincronizar Redis
            redis_agregar_empresa(r, nombre)
            print(f"\n  Empresa creada con ID {nuevo_id}.")
            print(f"  Sincronizado en Redis (ranking empresas).")

        elif op == "3":
            listar_registros(cur, "empresa", ["idempresa","nombre","rubro"], "EMPRESAS")
            eid = pedir("ID de la empresa a modificar", tipo=int)
            cur.execute("SELECT nombre FROM empresa WHERE idempresa=%s", (eid,))
            fila = cur.fetchone()
            if not fila:
                print("  Empresa no encontrada.")
                continue
            nombre_actual = fila[0]
            nombre      = pedir("Nuevo nombre", puede_vacio=True)
            descripcion = pedir("Nueva descripcion", puede_vacio=True)
            ubicacion   = pedir("Nueva ubicacion", puede_vacio=True)
            rubro       = pedir("Nuevo rubro", puede_vacio=True)
            if nombre:      cur.execute("UPDATE empresa SET nombre=%s WHERE idempresa=%s", (nombre, eid))
            if descripcion: cur.execute("UPDATE empresa SET descripcion=%s WHERE idempresa=%s", (descripcion, eid))
            if ubicacion:   cur.execute("UPDATE empresa SET ubicacion=%s WHERE idempresa=%s", (ubicacion, eid))
            if rubro:       cur.execute("UPDATE empresa SET rubro=%s WHERE idempresa=%s", (rubro, eid))
            pg.commit()
            # Sincronizar Redis
            if nombre:
                redis_actualizar_empresa(r, nombre_actual, nombre)
            print("  Empresa actualizada.")
            print("  Sincronizado en Redis.")

        elif op == "4":
            listar_registros(cur, "empresa", ["idempresa","nombre"], "EMPRESAS")
            eid = pedir("ID de la empresa a eliminar", tipo=int)
            cur.execute("SELECT nombre FROM empresa WHERE idempresa=%s", (eid,))
            fila = cur.fetchone()
            if not fila:
                print("  Empresa no encontrada.")
                continue
            nombre_actual = fila[0]
            if input(f"  Confirmar eliminacion? (s/n): ").strip().lower() == "s":
                cur.execute("DELETE FROM empresa WHERE idempresa=%s", (eid,))
                pg.commit()
                # Sincronizar Redis
                redis_eliminar_empresa(r, nombre_actual)
                print("  Empresa eliminada.")
                print("  Sincronizado en Redis.")
            else:
                print("  Cancelado.")

        elif op == "0":
            break

# ============================================================
# CRUD - EMPLEO
# ============================================================

def menu_empleo(pg, r):
    while True:
        separador("GESTION DE EMPLEOS")
        print("  1. Listar empleos")
        print("  2. Crear empleo")
        print("  3. Modificar empleo")
        print("  4. Eliminar empleo")
        print("  0. Volver")
        op = input("\n  Opcion: ").strip()
        cur = pg.cursor()

        if op == "1":
            listar_registros(cur, "empleo",
                ["idempleo","idempresa","titulo","modalidad","ubicacion","fechapublicacion"],
                "LISTA DE EMPLEOS")

        elif op == "2":
            separador("CREAR EMPLEO")
            listar_registros(cur, "empresa", ["idempresa","nombre"], "EMPRESAS DISPONIBLES")
            idempresa   = pedir("ID de la empresa", tipo=int)
            titulo      = pedir("Titulo del puesto")
            descripcion = pedir("Descripcion", puede_vacio=True)
            ubicacion   = pedir("Ubicacion", puede_vacio=True)
            modalidad   = pedir("Modalidad (presencial/remoto/hibrido)", puede_vacio=True)
            cur.execute("""
                INSERT INTO empleo (idempresa, titulo, descripcion, ubicacion, modalidad)
                VALUES (%s,%s,%s,%s,%s) RETURNING idempleo
            """, (idempresa, titulo, descripcion, ubicacion, modalidad))
            nuevo_id = cur.fetchone()[0]
            # Obtener nombre de la empresa para Redis
            cur.execute("SELECT nombre FROM empresa WHERE idempresa=%s", (idempresa,))
            fila = cur.fetchone()
            pg.commit()
            # Sincronizar Redis
            if fila:
                redis_agregar_empleo(r, fila[0])
            print(f"\n  Empleo creado con ID {nuevo_id}.")
            print(f"  Sincronizado en Redis (ranking empresas).")

        elif op == "3":
            listar_registros(cur, "empleo", ["idempleo","titulo","idempresa"], "EMPLEOS")
            eid       = pedir("ID del empleo a modificar", tipo=int)
            titulo    = pedir("Nuevo titulo", puede_vacio=True)
            ubicacion = pedir("Nueva ubicacion", puede_vacio=True)
            modalidad = pedir("Nueva modalidad", puede_vacio=True)
            if titulo:    cur.execute("UPDATE empleo SET titulo=%s WHERE idempleo=%s", (titulo, eid))
            if ubicacion: cur.execute("UPDATE empleo SET ubicacion=%s WHERE idempleo=%s", (ubicacion, eid))
            if modalidad: cur.execute("UPDATE empleo SET modalidad=%s WHERE idempleo=%s", (modalidad, eid))
            pg.commit()
            print("  Empleo actualizado.")

        elif op == "4":
            listar_registros(cur, "empleo", ["idempleo","titulo","idempresa"], "EMPLEOS")
            eid = pedir("ID del empleo a eliminar", tipo=int)
            cur.execute("""
                SELECT e.nombre FROM empleo em
                JOIN empresa e ON e.idempresa = em.idempresa
                WHERE em.idempleo=%s
            """, (eid,))
            fila = cur.fetchone()
            if input(f"  Confirmar eliminacion? (s/n): ").strip().lower() == "s":
                cur.execute("DELETE FROM empleo WHERE idempleo=%s", (eid,))
                pg.commit()
                # Sincronizar Redis
                if fila:
                    redis_eliminar_empleo(r, fila[0])
                print("  Empleo eliminado.")
                print("  Sincronizado en Redis.")
            else:
                print("  Cancelado.")

        elif op == "0":
            break

# ============================================================
# CRUD - POSTULACION
# ============================================================

def menu_postulacion(pg):
    while True:
        separador("GESTION DE POSTULACIONES")
        print("  1. Listar postulaciones")
        print("  2. Crear postulacion")
        print("  3. Modificar estado")
        print("  4. Eliminar postulacion")
        print("  0. Volver")
        op = input("\n  Opcion: ").strip()
        cur = pg.cursor()

        if op == "1":
            listar_registros(cur, "postulacion",
                ["idpostulacion","idusuario","idempleo","fechapostulacion","estado"],
                "LISTA DE POSTULACIONES")

        elif op == "2":
            separador("CREAR POSTULACION")
            listar_registros(cur, "usuario", ["idusuario","nombre","apellido"], "USUARIOS")
            idusuario = pedir("ID del usuario", tipo=int)
            listar_registros(cur, "empleo", ["idempleo","titulo"], "EMPLEOS")
            idempleo  = pedir("ID del empleo", tipo=int)
            estado    = pedir("Estado (pendiente/aceptado/rechazado)", puede_vacio=True) or "pendiente"
            cur.execute("INSERT INTO postulacion (idusuario, idempleo, estado) VALUES (%s,%s,%s) RETURNING idpostulacion",
                        (idusuario, idempleo, estado))
            nuevo_id = cur.fetchone()[0]
            pg.commit()
            print(f"\n  Postulacion creada con ID {nuevo_id}.")

        elif op == "3":
            listar_registros(cur, "postulacion",
                ["idpostulacion","idusuario","idempleo","estado"], "POSTULACIONES")
            pid    = pedir("ID de la postulacion a modificar", tipo=int)
            estado = pedir("Nuevo estado (pendiente/aceptado/rechazado)")
            cur.execute("UPDATE postulacion SET estado=%s WHERE idpostulacion=%s", (estado, pid))
            pg.commit()
            print("  Estado actualizado.")

        elif op == "4":
            listar_registros(cur, "postulacion",
                ["idpostulacion","idusuario","idempleo","estado"], "POSTULACIONES")
            pid = pedir("ID de la postulacion a eliminar", tipo=int)
            if input(f"  Confirmar eliminacion? (s/n): ").strip().lower() == "s":
                cur.execute("DELETE FROM postulacion WHERE idpostulacion=%s", (pid,))
                pg.commit()
                print("  Postulacion eliminada.")
            else:
                print("  Cancelado.")

        elif op == "0":
            break

# ============================================================
# CRUD - EXPERIENCIA LABORAL
# ============================================================

def menu_experiencia(pg):
    while True:
        separador("GESTION DE EXPERIENCIA LABORAL")
        print("  1. Listar experiencias")
        print("  2. Crear experiencia")
        print("  3. Modificar experiencia")
        print("  4. Eliminar experiencia")
        print("  0. Volver")
        op = input("\n  Opcion: ").strip()
        cur = pg.cursor()

        if op == "1":
            listar_registros(cur, "experiencia_laboral",
                ["idexperiencia","idusuario","idempresa","puesto","fechainicio","fechafin"],
                "LISTA DE EXPERIENCIAS")

        elif op == "2":
            separador("CREAR EXPERIENCIA LABORAL")
            listar_registros(cur, "usuario", ["idusuario","nombre","apellido"], "USUARIOS")
            idusuario   = pedir("ID del usuario", tipo=int)
            listar_registros(cur, "empresa", ["idempresa","nombre"], "EMPRESAS")
            idempresa   = pedir("ID de la empresa", tipo=int)
            puesto      = pedir("Puesto")
            finicio     = pedir("Fecha de inicio (YYYY-MM-DD)")
            ffin        = pedir("Fecha de fin (YYYY-MM-DD, Enter si sigue activo)", puede_vacio=True)
            descripcion = pedir("Descripcion", puede_vacio=True)
            cur.execute("""
                INSERT INTO experiencia_laboral (idusuario, idempresa, puesto, fechainicio, fechafin, descripcion)
                VALUES (%s,%s,%s,%s,%s,%s) RETURNING idexperiencia
            """, (idusuario, idempresa, puesto, finicio, ffin, descripcion))
            nuevo_id = cur.fetchone()[0]
            pg.commit()
            print(f"\n  Experiencia creada con ID {nuevo_id}.")

        elif op == "3":
            listar_registros(cur, "experiencia_laboral",
                ["idexperiencia","idusuario","puesto"], "EXPERIENCIAS")
            eid    = pedir("ID de la experiencia a modificar", tipo=int)
            puesto = pedir("Nuevo puesto", puede_vacio=True)
            ffin   = pedir("Nueva fecha de fin (YYYY-MM-DD)", puede_vacio=True)
            desc   = pedir("Nueva descripcion", puede_vacio=True)
            if puesto: cur.execute("UPDATE experiencia_laboral SET puesto=%s WHERE idexperiencia=%s", (puesto, eid))
            if ffin:   cur.execute("UPDATE experiencia_laboral SET fechafin=%s WHERE idexperiencia=%s", (ffin, eid))
            if desc:   cur.execute("UPDATE experiencia_laboral SET descripcion=%s WHERE idexperiencia=%s", (desc, eid))
            pg.commit()
            print("  Experiencia actualizada.")

        elif op == "4":
            listar_registros(cur, "experiencia_laboral",
                ["idexperiencia","idusuario","puesto"], "EXPERIENCIAS")
            eid = pedir("ID de la experiencia a eliminar", tipo=int)
            if input(f"  Confirmar eliminacion? (s/n): ").strip().lower() == "s":
                cur.execute("DELETE FROM experiencia_laboral WHERE idexperiencia=%s", (eid,))
                pg.commit()
                print("  Experiencia eliminada.")
            else:
                print("  Cancelado.")

        elif op == "0":
            break

# ============================================================
# CRUD - EDUCACION
# ============================================================

def menu_educacion(pg):
    while True:
        separador("GESTION DE EDUCACION")
        print("  1. Listar educacion")
        print("  2. Crear educacion")
        print("  3. Modificar educacion")
        print("  4. Eliminar educacion")
        print("  0. Volver")
        op = input("\n  Opcion: ").strip()
        cur = pg.cursor()

        if op == "1":
            listar_registros(cur, "educacion",
                ["ideducacion","idusuario","institucion","titulo","fechainicio","fechafin"],
                "LISTA DE EDUCACION")

        elif op == "2":
            separador("CREAR EDUCACION")
            listar_registros(cur, "usuario", ["idusuario","nombre","apellido"], "USUARIOS")
            idusuario   = pedir("ID del usuario", tipo=int)
            institucion = pedir("Institucion")
            titulo      = pedir("Titulo")
            finicio     = pedir("Fecha de inicio (YYYY-MM-DD)")
            ffin        = pedir("Fecha de fin (YYYY-MM-DD, Enter si sigue activo)", puede_vacio=True)
            cur.execute("""
                INSERT INTO educacion (idusuario, institucion, titulo, fechainicio, fechafin)
                VALUES (%s,%s,%s,%s,%s) RETURNING ideducacion
            """, (idusuario, institucion, titulo, finicio, ffin))
            nuevo_id = cur.fetchone()[0]
            pg.commit()
            print(f"\n  Educacion creada con ID {nuevo_id}.")

        elif op == "3":
            listar_registros(cur, "educacion",
                ["ideducacion","idusuario","institucion","titulo"], "EDUCACION")
            eid         = pedir("ID del registro a modificar", tipo=int)
            institucion = pedir("Nueva institucion", puede_vacio=True)
            titulo      = pedir("Nuevo titulo", puede_vacio=True)
            ffin        = pedir("Nueva fecha de fin (YYYY-MM-DD)", puede_vacio=True)
            if institucion: cur.execute("UPDATE educacion SET institucion=%s WHERE ideducacion=%s", (institucion, eid))
            if titulo:      cur.execute("UPDATE educacion SET titulo=%s WHERE ideducacion=%s", (titulo, eid))
            if ffin:        cur.execute("UPDATE educacion SET fechafin=%s WHERE ideducacion=%s", (ffin, eid))
            pg.commit()
            print("  Educacion actualizada.")

        elif op == "4":
            listar_registros(cur, "educacion",
                ["ideducacion","idusuario","institucion","titulo"], "EDUCACION")
            eid = pedir("ID del registro a eliminar", tipo=int)
            if input(f"  Confirmar eliminacion? (s/n): ").strip().lower() == "s":
                cur.execute("DELETE FROM educacion WHERE ideducacion=%s", (eid,))
                pg.commit()
                print("  Registro eliminado.")
            else:
                print("  Cancelado.")

        elif op == "0":
            break

# ============================================================
# CRUD - HABILIDAD
# ============================================================

def menu_habilidad(pg, r):
    while True:
        separador("GESTION DE HABILIDADES")
        print("  1. Listar habilidades")
        print("  2. Crear habilidad")
        print("  3. Modificar habilidad")
        print("  4. Eliminar habilidad")
        print("  0. Volver")
        op = input("\n  Opcion: ").strip()
        cur = pg.cursor()

        if op == "1":
            listar_registros(cur, "habilidad", ["idhabilidad","nombre"], "LISTA DE HABILIDADES")

        elif op == "2":
            separador("CREAR HABILIDAD")
            nombre = pedir("Nombre de la habilidad")
            cur.execute("INSERT INTO habilidad (nombre) VALUES (%s) RETURNING idhabilidad", (nombre,))
            nuevo_id = cur.fetchone()[0]
            pg.commit()
            # Sincronizar Redis
            redis_agregar_habilidad(r, nombre)
            print(f"\n  Habilidad creada con ID {nuevo_id}.")
            print(f"  Sincronizado en Redis (ranking habilidades).")

        elif op == "3":
            listar_registros(cur, "habilidad", ["idhabilidad","nombre"], "HABILIDADES")
            hid    = pedir("ID de la habilidad a modificar", tipo=int)
            cur.execute("SELECT nombre FROM habilidad WHERE idhabilidad=%s", (hid,))
            fila = cur.fetchone()
            if not fila:
                print("  Habilidad no encontrada.")
                continue
            nombre_actual = fila[0]
            nombre = pedir("Nuevo nombre")
            cur.execute("UPDATE habilidad SET nombre=%s WHERE idhabilidad=%s", (nombre, hid))
            pg.commit()
            # Sincronizar Redis
            redis_actualizar_habilidad(r, nombre_actual, nombre)
            print("  Habilidad actualizada.")
            print("  Sincronizado en Redis.")

        elif op == "4":
            listar_registros(cur, "habilidad", ["idhabilidad","nombre"], "HABILIDADES")
            hid = pedir("ID de la habilidad a eliminar", tipo=int)
            cur.execute("SELECT nombre FROM habilidad WHERE idhabilidad=%s", (hid,))
            fila = cur.fetchone()
            if not fila:
                print("  Habilidad no encontrada.")
                continue
            nombre_actual = fila[0]
            if input(f"  Confirmar eliminacion? (s/n): ").strip().lower() == "s":
                cur.execute("DELETE FROM habilidad WHERE idhabilidad=%s", (hid,))
                pg.commit()
                # Sincronizar Redis
                redis_eliminar_habilidad(r, nombre_actual)
                print("  Habilidad eliminada.")
                print("  Sincronizado en Redis.")
            else:
                print("  Cancelado.")

        elif op == "0":
            break

# ============================================================
# CRUD - USUARIO_HABILIDAD
# ============================================================

def menu_usuario_habilidad(pg, r):
    while True:
        separador("GESTION DE HABILIDADES POR USUARIO")
        print("  1. Listar asignaciones")
        print("  2. Asignar habilidad a usuario")
        print("  3. Eliminar asignacion")
        print("  0. Volver")
        op = input("\n  Opcion: ").strip()
        cur = pg.cursor()

        if op == "1":
            separador("HABILIDADES POR USUARIO")
            cur.execute("""
                SELECT u.nombre || ' ' || u.apellido AS usuario, h.nombre AS habilidad
                FROM usuario_habilidad uh
                JOIN usuario u ON u.idusuario = uh.idusuario
                JOIN habilidad h ON h.idhabilidad = uh.idhabilidad
                ORDER BY u.apellido, h.nombre
            """)
            filas = cur.fetchall()
            if not filas:
                print("  No hay asignaciones.")
            for fila in filas:
                print(f"  {fila[0]} -> {fila[1]}")

        elif op == "2":
            listar_registros(cur, "usuario", ["idusuario","nombre","apellido"], "USUARIOS")
            idusuario   = pedir("ID del usuario", tipo=int)
            listar_registros(cur, "habilidad", ["idhabilidad","nombre"], "HABILIDADES")
            idhabilidad = pedir("ID de la habilidad", tipo=int)
            cur.execute("SELECT nombre FROM habilidad WHERE idhabilidad=%s", (idhabilidad,))
            fila = cur.fetchone()
            try:
                cur.execute("INSERT INTO usuario_habilidad (idusuario, idhabilidad) VALUES (%s,%s)",
                            (idusuario, idhabilidad))
                pg.commit()
                # Sincronizar Redis
                if fila:
                    redis_asignar_habilidad(r, fila[0])
                print("  Habilidad asignada correctamente.")
                print("  Sincronizado en Redis (ranking habilidades).")
            except Exception:
                pg.rollback()
                print("  Esa asignacion ya existe.")

        elif op == "3":
            listar_registros(cur, "usuario", ["idusuario","nombre","apellido"], "USUARIOS")
            idusuario   = pedir("ID del usuario", tipo=int)
            listar_registros(cur, "habilidad", ["idhabilidad","nombre"], "HABILIDADES")
            idhabilidad = pedir("ID de la habilidad a quitar", tipo=int)
            cur.execute("SELECT nombre FROM habilidad WHERE idhabilidad=%s", (idhabilidad,))
            fila = cur.fetchone()
            cur.execute("DELETE FROM usuario_habilidad WHERE idusuario=%s AND idhabilidad=%s",
                        (idusuario, idhabilidad))
            pg.commit()
            # Sincronizar Redis
            if fila:
                redis_quitar_habilidad(r, fila[0])
            print("  Asignacion eliminada.")
            print("  Sincronizado en Redis.")

        elif op == "0":
            break

# ============================================================
# CASOS DE USO
# ============================================================

def cu1_usuarios_ultimo_anio(pg):
    separador("CU 1 - Cuantos usuarios se registraron en el ultimo ano")
    print("Base usada: PostgreSQL")
    cur = pg.cursor()
    cur.execute("""
        SELECT COUNT(*) AS total,
               TO_CHAR(DATE_TRUNC('month', "creadoen"), 'Mon YYYY') AS mes
        FROM usuario
        WHERE "creadoen" >= NOW() - INTERVAL '2 years'
        GROUP BY DATE_TRUNC('month', "creadoen")
        ORDER BY DATE_TRUNC('month', "creadoen")
    """)
    filas = cur.fetchall()
    total = sum(f[0] for f in filas)
    print(f"\n  Total de usuarios registrados: {total}")
    print("\n  Desglose por mes:")
    for cantidad, mes in filas:
        print(f"  - {mes}: {cantidad} usuario(s)")

def cu2_habilidades_demandadas(r):
    separador("CU 2 - Que habilidades son mas solicitadas")
    print("Base usada: Redis")
    top = r.zrevrange("habilidades_demandadas", 0, 4, withscores=True)
    print("\n  Top 5 habilidades mas demandadas:")
    for i, (habilidad, puntaje) in enumerate(top, 1):
        print(f"  {i}. {habilidad} - {int(puntaje)} ofertas")

def cu3_empresas_activas(r):
    separador("CU 3 - Que empresas estan contratando mas")
    print("Base usada: Redis")
    top = r.zrevrange("empresas_activas", 0, 4, withscores=True)
    print("\n  Top 5 empresas que mas contratan:")
    for i, (empresa, puntaje) in enumerate(top, 1):
        print(f"  {i}. {empresa} - {int(puntaje)} ofertas activas")

def cu4_recomendaciones_usuario(db):
    separador("CU 4 - Cuantas recomendaciones recibio un usuario")
    print("Base usada: MongoDB")
    id_usuario = int(input("  Ingresa el ID del usuario: ").strip())
    total_likes = list(db.publicaciones.aggregate([
        {"$match": {"idUsuario": id_usuario}},
        {"$group": {"_id": None, "total_likes": {"$sum": "$likes"}}}
    ]))
    total = total_likes[0]["total_likes"] if total_likes else 0
    res_com = list(db.publicaciones.aggregate([
        {"$match": {"idUsuario": id_usuario}},
        {"$project": {"cant": {"$size": "$comentarios"}}},
        {"$group": {"_id": None, "total": {"$sum": "$cant"}}}
    ]))
    comentarios = res_com[0]["total"] if res_com else 0
    print(f"\n  Usuario ID {id_usuario}:")
    print(f"  - Likes recibidos: {total}")
    print(f"  - Comentarios recibidos: {comentarios}")

def cu5_crecimiento_regional(r):
    separador("CU 5 - Crecimiento por region geografica")
    print("Base usada: Redis")
    regiones = r.hgetall("usuarios_por_region")
    print("\n  Usuarios por region:")
    for region, cantidad in sorted(regiones.items(), key=lambda x: -int(x[1])):
        print(f"  - {region}: {cantidad} usuario(s)")

def cu6_conexiones_y_amigos_comunes(driver):
    separador("CU 6 - Usuarios con +2 conexiones Y +1 amigo en comun")
    print("Base usada: Neo4j")
    print("Nota: umbrales bajos por datos de prueba (reales: 500 conexiones y 10 amigos)")
    with driver.session() as session:
        result = session.run("""
            MATCH (yo:Usuario {id: 1})-[:CONECTADO_CON]-(amigo)
            MATCH (candidato:Usuario)-[:CONECTADO_CON]-(amigo)
            WHERE candidato <> yo AND NOT (yo)-[:CONECTADO_CON]-(candidato)
            WITH candidato, COUNT(DISTINCT amigo) AS enComun
            WHERE enComun >= 1
            MATCH (candidato)-[r:CONECTADO_CON]-()
            WITH candidato, enComun, COUNT(r) AS totalConexiones
            WHERE totalConexiones >= 2
            RETURN candidato.nombre AS nombre, enComun, totalConexiones
            ORDER BY enComun DESC
        """)
        filas = result.data()
        if filas:
            print("\n  Candidatos encontrados:")
            for f in filas:
                print(f"  - {f['nombre']}: {f['totalConexiones']} conexiones, {f['enComun']} amigo(s) en comun")
        else:
            print("\n  No se encontraron candidatos.")

def cu7_habilidades_por_sector(r):
    separador("CU 7 - Habilidades en tecnologia O marketing")
    print("Base usada: Redis")
    sectores = {
        "Tecnologia": ["Python","SQL","React","Docker","Java","Machine Learning","Node.js","AWS","MongoDB"],
        "Marketing":  ["Marketing Digital"]
    }
    print("\n  Habilidades demandadas por sector:")
    for sector, habilidades in sectores.items():
        print(f"\n  [{sector}]")
        for h in habilidades:
            puntaje = r.zscore("habilidades_demandadas", h)
            if puntaje:
                print(f"  - {h}: {int(puntaje)} ofertas")

# ============================================================
# MENU CASOS DE USO
# ============================================================

def menu_casos_de_uso(pg, db, r, driver):
    while True:
        separador("CASOS DE USO")
        print("  1. Usuarios registrados en el ultimo ano           [PostgreSQL]")
        print("  2. Habilidades mas solicitadas                     [Redis]")
        print("  3. Empresas que mas contratan                      [Redis]")
        print("  4. Recomendaciones de un usuario                   [MongoDB]")
        print("  5. Crecimiento por region geografica               [Redis]")
        print("  6. Usuarios con +500 conexiones y amigos en comun  [Neo4j]")
        print("  7. Habilidades en tecnologia O marketing           [Redis]")
        print("  0. Volver")
        op = input("\n  Opcion: ").strip()

        if op == "1":   cu1_usuarios_ultimo_anio(pg)
        elif op == "2": cu2_habilidades_demandadas(r)
        elif op == "3": cu3_empresas_activas(r)
        elif op == "4": cu4_recomendaciones_usuario(db)
        elif op == "5": cu5_crecimiento_regional(r)
        elif op == "6": cu6_conexiones_y_amigos_comunes(driver)
        elif op == "7": cu7_habilidades_por_sector(r)
        elif op == "0": break
        else:           print("  Opcion invalida.")

        if op != "0":
            input("\n  Presiona Enter para continuar...")


# ============================================================
# MENU MONGODB
# ============================================================

def menu_mongodb(pg, db):
    while True:
        separador("PUBLICACIONES Y MENSAJES - MongoDB")
        print("  1. Ver todas las publicaciones")
        print("  2. Ver publicaciones de un usuario")
        print("  3. Crear publicacion")
        print("  4. Eliminar publicacion")
        print("  5. Ver mensajes de un usuario")
        print("  6. Enviar mensaje")
        print("  7. Dar like a una publicacion")
        print("  8. Agregar comentario a una publicacion")
        print("  0. Volver")
        op = input("\n  Opcion: ").strip()

        if op == "1":
            separador("TODAS LAS PUBLICACIONES")
            pubs = list(db.publicaciones.find().sort("creadoEn", -1))
            if not pubs:
                print("  No hay publicaciones.")
            for p in pubs:
                print(f"\n  Usuario {p['idUsuario']} | {p.get('tipo','texto')} | {p['creadoEn'].strftime('%d/%m/%Y')}")
                print(f"  {p['contenido']}")
                print(f"  Likes: {p.get('likes', 0)} | Comentarios: {len(p.get('comentarios', []))}")
                for c in p.get("comentarios", []):
                    print(f"    > Usuario {c['idUsuario']}: {c['texto']}")

        elif op == "2":
            cur = pg.cursor()
            listar_registros(cur, "usuario", ["idusuario","nombre","apellido"], "USUARIOS")
            uid = int(input("  ID del usuario: ").strip())
            separador(f"PUBLICACIONES DEL USUARIO {uid}")
            pubs = list(db.publicaciones.find({"idUsuario": uid}).sort("creadoEn", -1))
            if not pubs:
                print("  Este usuario no tiene publicaciones.")
            for p in pubs:
                print(f"\n  {p.get('tipo','texto')} | {p['creadoEn'].strftime('%d/%m/%Y')}")
                print(f"  {p['contenido']}")
                print(f"  Likes: {p.get('likes', 0)} | Comentarios: {len(p.get('comentarios', []))}")
                for c in p.get("comentarios", []):
                    print(f"    > Usuario {c['idUsuario']}: {c['texto']}")

        elif op == "3":
            separador("CREAR PUBLICACION")
            cur = pg.cursor()
            listar_registros(cur, "usuario", ["idusuario","nombre","apellido"], "USUARIOS")
            uid       = int(input("  ID del usuario: ").strip())
            contenido = pedir("Contenido")
            tipo      = pedir("Tipo (texto/articulo/imagen)", puede_vacio=True) or "texto"
            db.publicaciones.insert_one({
                "idUsuario": uid,
                "contenido": contenido,
                "tipo": tipo,
                "creadoEn": datetime.now(timezone.utc),
                "likes": 0,
                "comentarios": []
            })
            print("  Publicacion creada en MongoDB.")

        elif op == "4":
            separador("ELIMINAR PUBLICACION")
            cur = pg.cursor()
            listar_registros(cur, "usuario", ["idusuario","nombre","apellido"], "USUARIOS")
            uid  = int(input("  ID del usuario dueno de la publicacion: ").strip())
            pubs = list(db.publicaciones.find({"idUsuario": uid}))
            if not pubs:
                print("  Este usuario no tiene publicaciones.")
            else:
                for i, p in enumerate(pubs):
                    print(f"  {i+1}. {p['contenido'][:60]} | {p['creadoEn'].strftime('%d/%m/%Y')}")
                idx = int(input("  Numero de publicacion a eliminar: ").strip()) - 1
                if 0 <= idx < len(pubs):
                    db.publicaciones.delete_one({"_id": pubs[idx]["_id"]})
                    print("  Publicacion eliminada.")
                else:
                    print("  Numero invalido.")

        elif op == "5":
            separador("MENSAJES")
            cur = pg.cursor()
            listar_registros(cur, "usuario", ["idusuario","nombre","apellido"], "USUARIOS")
            uid  = int(input("  ID del usuario: ").strip())
            msgs = list(db.mensajes.find({
                "$or": [{"idRemitente": uid}, {"idDestinatario": uid}]
            }).sort("fechaEnvio", 1))
            if not msgs:
                print("  No hay mensajes.")
            for m in msgs:
                direccion = ">>>" if m["idRemitente"] == uid else "<<<"
                leido     = "leido" if m.get("leido") else "no leido"
                print(f"  {direccion} Usuario {m['idRemitente']} -> {m['idDestinatario']} | {m['fechaEnvio'].strftime('%d/%m/%Y %H:%M')} | {leido}")
                print(f"      {m['contenido']}")

        elif op == "6":
            separador("ENVIAR MENSAJE")
            cur = pg.cursor()
            listar_registros(cur, "usuario", ["idusuario","nombre","apellido"], "USUARIOS")
            remitente    = int(input("  ID del remitente: ").strip())
            destinatario = int(input("  ID del destinatario: ").strip())
            contenido    = pedir("Mensaje")
            db.mensajes.insert_one({
                "idRemitente":    remitente,
                "idDestinatario": destinatario,
                "contenido":      contenido,
                "fechaEnvio":     datetime.now(timezone.utc),
                "leido":          False
            })
            print("  Mensaje enviado y guardado en MongoDB.")

        elif op == "7":
            separador("DAR LIKE A UNA PUBLICACION")
            cur = pg.cursor()
            listar_registros(cur, "usuario", ["idusuario","nombre","apellido"], "USUARIOS")
            uid  = int(input("  ID del usuario dueno de la publicacion: ").strip())
            pubs = list(db.publicaciones.find({"idUsuario": uid}))
            if not pubs:
                print("  Este usuario no tiene publicaciones.")
            else:
                for i, p in enumerate(pubs):
                    print(f"  {i+1}. {p['contenido'][:60]} | Likes: {p.get('likes',0)}")
                idx = int(input("  Numero de publicacion: ").strip()) - 1
                if 0 <= idx < len(pubs):
                    db.publicaciones.update_one(
                        {"_id": pubs[idx]["_id"]},
                        {"$inc": {"likes": 1}}
                    )
                    print("  Like agregado.")
                else:
                    print("  Numero invalido.")

        elif op == "8":
            separador("AGREGAR COMENTARIO A UNA PUBLICACION")
            cur = pg.cursor()
            listar_registros(cur, "usuario", ["idusuario","nombre","apellido"], "USUARIOS")
            uid_pub  = int(input("  ID del usuario dueno de la publicacion: ").strip())
            pubs = list(db.publicaciones.find({"idUsuario": uid_pub}))
            if not pubs:
                print("  Este usuario no tiene publicaciones.")
            else:
                for i, p in enumerate(pubs):
                    print(f"  {i+1}. {p['contenido'][:60]} | Comentarios: {len(p.get('comentarios',[]))}")
                idx = int(input("  Numero de publicacion: ").strip()) - 1
                if 0 <= idx < len(pubs):
                    listar_registros(cur, "usuario", ["idusuario","nombre","apellido"], "USUARIOS")
                    uid_com  = int(input("  ID del usuario que comenta: ").strip())
                    texto    = pedir("Comentario")
                    db.publicaciones.update_one(
                        {"_id": pubs[idx]["_id"]},
                        {"$push": {"comentarios": {
                            "idUsuario": uid_com,
                            "texto": texto,
                            "fecha": datetime.now(timezone.utc)
                        }}}
                    )
                    print("  Comentario agregado.")
                else:
                    print("  Numero invalido.")


        elif op == "0":
            break
        else:
            print("  Opcion invalida.")

        if op != "0":
            input("\n  Presiona Enter para continuar...")



# ============================================================
# MENU PRINCIPAL
# ============================================================

def menu_principal(pg, db, r, driver):
    while True:
        separador("LINKEDIN TP - MENU PRINCIPAL")
        print("  1. Gestionar")
        print("  2. Casos de uso")
        print("  0. Salir")
        op = input("\n  Opcion: ").strip()

        if op == "1":
            while True:
                separador("GESTIONAR")
                print("  1. Gestionar usuarios")
                print("  2. Gestionar empresas")
                print("  3. Gestionar empleos")
                print("  4. Gestionar postulaciones")
                print("  5. Gestionar experiencia laboral")
                print("  6. Gestionar educacion")
                print("  7. Gestionar habilidades")
                print("  8. Gestionar habilidades por usuario")
                print("  9. Gestionar publicaciones y mensajes")
                print("  0. Volver")
                op2 = input("\n  Opcion: ").strip()

                if op2 == "1":   menu_usuario(pg, driver, r)
                elif op2 == "2": menu_empresa(pg, r)
                elif op2 == "3": menu_empleo(pg, r)
                elif op2 == "4": menu_postulacion(pg)
                elif op2 == "5": menu_experiencia(pg)
                elif op2 == "6": menu_educacion(pg)
                elif op2 == "7": menu_habilidad(pg, r)
                elif op2 == "8": menu_usuario_habilidad(pg, r)
                elif op2 == "9": menu_mongodb(pg, db)
                elif op2 == "0": break
                else:            print("  Opcion invalida.")

        elif op == "2":
            menu_casos_de_uso(pg, db, r, driver)

        elif op == "0":
            print("\n  Cerrando conexiones...")
            pg.close()
            driver.close()
            print("  Hasta luego.")
            break
        else:
            print("  Opcion invalida.")

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    separador("LINKEDIN TP - Bases de Datos Relacionales y NoSQL")
    print("\nConectando a las bases de datos...")
    pg     = conectar_postgres()
    db     = conectar_mongo()
    r      = conectar_redis()
    driver = conectar_neo4j()
    print("PostgreSQL conectado")
    print("MongoDB conectado")
    print("Redis conectado")
    print("Neo4j conectado")

    setup_mongodb(db)
    setup_redis(r)
    setup_neo4j(driver)

    menu_principal(pg, db, r, driver)