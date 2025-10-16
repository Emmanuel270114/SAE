from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
from typing import List, Dict, Any
from fastapi import HTTPException

from backend.core.templates import templates
from backend.database.connection import get_db
from backend.database.models.Matricula import Matricula
from backend.database.models.CatPeriodo import CatPeriodo as Periodo
from backend.database.models.CatUnidadAcademica import CatUnidadAcademica as Unidad_Academica
from backend.database.models.CatNivel import CatNivel as Nivel
from backend.database.models.CatSemestre import CatSemestre as Semestre
from backend.database.models.CatProgramas import CatProgramas as Programas
from backend.database.models.CatModalidad import CatModalidad as Modalidad
from backend.database.models.CatTurno import CatTurno as Turno
from backend.database.models.CatGrupoEdad import CatGrupoEdad as Grupo_Edad
from backend.database.models.CatTipoIngreso import TipoIngreso as Tipo_Ingreso
from backend.database.models.CatRama import CatRama as Rama
from backend.services.matricula_service import (
    execute_matricula_sp_with_context,
    get_matricula_metadata_from_sp
)
from backend.utils.request import get_request_host
from backend.database.models.Temp_Matricula import Temp_Matricula

router = APIRouter()


@router.get('/consulta')
async def captura_matricula_sp_view(request: Request, db: Session = Depends(get_db)):
    """
    Endpoint principal para la captura de matrícula usando EXCLUSIVAMENTE Stored Procedures.
    Solo accesible para usuarios con rol 'Capturista'.
    TODA la información viene del SP, NO de los modelos ORM.
    """
    # Obtener datos del usuario logueado desde las cookies
    id_unidad_academica = int(request.cookies.get("id_unidad_academica", 0))
    id_nivel = int(request.cookies.get("id_nivel", 0))
    id_rol = int(request.cookies.get("id_rol", 0))
    nombre_rol = request.cookies.get("nombre_rol", "")
    nombre_usuario = request.cookies.get("nombre_usuario", "")
    apellidoP_usuario = request.cookies.get("apellidoP_usuario", "")
    apellidoM_usuario = request.cookies.get("apellidoM_usuario", "")
    nombre_completo = " ".join(filter(None, [nombre_usuario, apellidoP_usuario, apellidoM_usuario]))

    # Validar que el usuario tenga el rol de 'Capturista'
    if nombre_rol.lower() != 'capturista':
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_message": "Acceso denegado: Solo los usuarios con rol 'Capturista' pueden acceder a esta funcionalidad.",
            "redirect_url": "/mod_principal/"
        })

    print(f"\n{'='*60}")
    print(f"CARGANDO VISTA DE MATRÍCULA - TODO DESDE SP")
    print(f"Usuario: {nombre_completo}")
    print(f"ID Unidad Académica: {id_unidad_academica}")
    print(f"ID Nivel: {id_nivel}")
    print(f"{'='*60}")

    # Obtener SOLO período y unidad desde la base de datos (mínimo necesario)
    periodos = db.query(Periodo).all()
    unidades_academicas = db.query(Unidad_Academica).filter(
        Unidad_Academica.Id_Unidad_Academica == id_unidad_academica
    ).all()
    
    # Definir periodo por defecto
    periodo_default_id = 9
    periodo_default_literal = '2025-2026/1'
    unidad_actual = unidades_academicas[0] if unidades_academicas else None

    # Obtener usuario y host para el SP
    usuario_sp = nombre_completo or 'sistema'
    host_sp = get_request_host(request)

    # Obtener TODOS los metadatos desde el SP (con usuario y host)
    metadata = get_matricula_metadata_from_sp(
        db=db,
        id_unidad_academica=id_unidad_academica,
        id_nivel=id_nivel,
        periodo_input=periodo_default_literal,
        default_periodo=periodo_default_literal,
        usuario=usuario_sp,
        host=host_sp
    )

    # Verificar si hubo error
    if 'error' in metadata and metadata['error']:
        print(f"⚠️ Error obteniendo metadatos: {metadata['error']}")

    # Preparar datos para el template
    grupos_edad_labels = metadata.get('grupos_edad', [])
    tipos_ingreso_labels = metadata.get('tipos_ingreso', [])
    programas_labels = metadata.get('programas', [])
    modalidades_labels = metadata.get('modalidades', [])
    semestres_labels = metadata.get('semestres', [])
    turnos_labels = metadata.get('turnos', [])

    # Mapear nombres a objetos de catálogo para obtener IDs
    # Grupos de Edad
    grupos_edad_db = db.query(Grupo_Edad).all()
    grupos_edad_map = {str(g.Grupo_Edad): g for g in grupos_edad_db}
    grupos_edad_formatted = []
    for label in grupos_edad_labels:
        if label in grupos_edad_map:
            g = grupos_edad_map[label]
            grupos_edad_formatted.append({'Id_Grupo_Edad': g.Id_Grupo_Edad, 'Grupo_Edad': g.Grupo_Edad})
    
    # Tipos de Ingreso
    tipos_ingreso_db = db.query(Tipo_Ingreso).all()
    tipos_ingreso_map = {str(t.Tipo_de_Ingreso): t for t in tipos_ingreso_db}
    tipos_ingreso_formatted = []
    for label in tipos_ingreso_labels:
        if label in tipos_ingreso_map:
            t = tipos_ingreso_map[label]
            tipos_ingreso_formatted.append({'Id_Tipo_Ingreso': t.Id_Tipo_Ingreso, 'Tipo_de_Ingreso': t.Tipo_de_Ingreso})
    
    # Programas
    programas_db = db.query(Programas).filter(Programas.Id_Nivel == id_nivel).all()
    programas_map = {str(p.Nombre_Programa): p for p in programas_db}
    programas_formatted = []
    for label in programas_labels:
        if label in programas_map:
            p = programas_map[label]
            programas_formatted.append({
                'Id_Programa': p.Id_Programa,
                'Nombre_Programa': p.Nombre_Programa,
                'Id_Semestre': p.Id_Semestre
            })
    
    # Modalidades
    modalidades_db = db.query(Modalidad).all()
    modalidades_map = {str(m.Modalidad): m for m in modalidades_db}
    modalidades_formatted = []
    for label in modalidades_labels:
        if label in modalidades_map:
            m = modalidades_map[label]
            modalidades_formatted.append({'Id_Modalidad': m.Id_Modalidad, 'Modalidad': m.Modalidad})
    
    # Semestres
    semestres_db = db.query(Semestre).all()
    semestres_map_db = {str(s.Semestre): s for s in semestres_db}
    semestres_formatted = []
    for label in semestres_labels:
        if label in semestres_map_db:
            s = semestres_map_db[label]
            semestres_formatted.append({'Id_Semestre': s.Id_Semestre, 'Semestre': s.Semestre})
    
    # Turnos
    turnos_db = db.query(Turno).all()
    turnos_map = {str(t.Turno): t for t in turnos_db}
    turnos_formatted = []
    for label in turnos_labels:
        if label in turnos_map:
            t = turnos_map[label]
            turnos_formatted.append({'Id_Turno': t.Id_Turno, 'Turno': t.Turno})

    # Construir un mapping simple para semestres
    semestres_map_json_dict = {s['Id_Semestre']: s['Semestre'] for s in semestres_formatted}
    semestres_map_json = json.dumps(semestres_map_json_dict, ensure_ascii=False)

    print(f"\n=== METADATOS ENVIADOS AL FRONTEND ===")
    print(f"Grupos de Edad: {len(grupos_edad_formatted)} -> {[g['Grupo_Edad'] for g in grupos_edad_formatted]}")
    print(f"Tipos de Ingreso: {len(tipos_ingreso_formatted)} -> {[t['Tipo_de_Ingreso'] for t in tipos_ingreso_formatted]}")
    print(f"Programas: {len(programas_formatted)} -> {[p['Nombre_Programa'] for p in programas_formatted]}")
    print(f"Modalidades: {len(modalidades_formatted)}")
    print(f"Semestres: {len(semestres_formatted)}")
    print(f"Turnos: {len(turnos_formatted)}")

    return templates.TemplateResponse("matricula_consulta.html", {
        "request": request,
        "nombre_usuario": nombre_completo,
        "nombre_rol": nombre_rol,
        "id_unidad_academica": id_unidad_academica,
        "id_nivel": id_nivel,
        "id_rol": id_rol,
        "periodos": periodos,
        "unidades_academicas": unidades_academicas,
        "periodo_default_id": periodo_default_id,
        "unidad_actual": unidad_actual,
        "programas": programas_formatted,
        "modalidades": modalidades_formatted,
        "semestres": semestres_formatted,
        "semestres_map_json": semestres_map_json,
        "turnos": turnos_formatted,
        "grupos_edad": grupos_edad_formatted,
        "tipos_ingreso": tipos_ingreso_formatted
    })

# Endpoint para obtener datos existentes usando SP
@router.post("/obtener_datos_existentes_sp")
async def obtener_datos_existentes_sp(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Endpoint para obtener datos existentes usando SP.
    Retorna SOLO las filas del SP sin procesamiento adicional.
    El frontend se encarga de construir la tabla con estos datos.
    """
    try:
        data = await request.json()
        print(f"\n=== DEBUG SP - Parámetros recibidos ===")
        print(f"Datos JSON: {data}")

        # Obtener parámetros del JSON
        periodo = data.get('periodo')
        
        # Obtener datos del usuario desde cookies
        id_unidad_academica = int(request.cookies.get("id_unidad_academica", 0))
        id_nivel = int(request.cookies.get("id_nivel", 0))
        nombre_usuario = request.cookies.get("nombre_usuario", "")
        apellidoP_usuario = request.cookies.get("apellidoP_usuario", "")
        apellidoM_usuario = request.cookies.get("apellidoM_usuario", "")
        nombre_completo = " ".join(filter(None, [nombre_usuario, apellidoP_usuario, apellidoM_usuario]))

        print(f"ID Unidad Académica (cookie): {id_unidad_academica}")
        print(f"ID Nivel (cookie): {id_nivel}")
        print(f"Usuario: {nombre_completo}")

        # Obtener usuario y host para el SP
        usuario_sp = nombre_completo or 'sistema'
        host_sp = get_request_host(request)
        print(f"Host: {host_sp}")

        # Ejecutar SP y obtener metadatos (con usuario y host)
        rows_list, metadata, debug_msg = execute_matricula_sp_with_context(
            db=db,
            id_unidad_academica=id_unidad_academica,
            id_nivel=id_nivel,
            periodo_input=periodo,
            default_periodo='2025-2026/1',
            usuario=usuario_sp,
            host=host_sp
        )
        
        print(f"\n=== RESULTADOS DEL SP ===")
        print(debug_msg)
        print(f"Total de filas: {len(rows_list)}")
        print(f"Metadatos extraídos: {metadata}")

        # Devolver resultado exitoso o error
        if "Error" in debug_msg:
            return {"error": debug_msg}
        else:
            return {
                "rows": rows_list,
                "metadata": metadata,
                "debug": debug_msg
            }

    except Exception as e:
        print(f"ERROR en endpoint SP: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": f"Error al obtener datos existentes: {str(e)}"}

# Endpoint de depuración detallada del SP
@router.get('/debug_sp')
async def debug_sp(request: Request, db: Session = Depends(get_db)):
    """Endpoint temporal para ver qué trae el SP exactamente — detecta UA y nivel desde cookies."""
    try:
        print(f"\n{'='*60}")
        print(f"EJECUTANDO SP (debug) usando cookies del usuario")
        print(f"{'='*60}")

        # Leer cookies del usuario
        id_unidad_academica = int(request.cookies.get("id_unidad_academica", 0))
        id_nivel = int(request.cookies.get("id_nivel", 0))
        nombre_usuario = request.cookies.get("nombre_usuario", "")
        apellidoP_usuario = request.cookies.get("apellidoP_usuario", "")
        apellidoM_usuario = request.cookies.get("apellidoM_usuario", "")
        nombre_completo = " ".join(filter(None, [nombre_usuario, apellidoP_usuario, apellidoM_usuario]))
        periodo = '2025-2026/1'

        print(f"ID Unidad Académica (cookie): {id_unidad_academica}")
        print(f"ID Nivel (cookie): {id_nivel}")
        print(f"Usuario: {nombre_completo}")
        print(f"Periodo (forzado): {periodo}")

        # Obtener usuario y host para el SP
        usuario_sp = nombre_completo or 'sistema'
        host_sp = get_request_host(request)
        print(f"Host: {host_sp}")

        unidad = db.query(Unidad_Academica).filter(Unidad_Academica.Id_Unidad_Academica == id_unidad_academica).first()
        nivel = db.query(Nivel).filter(Nivel.Id_Nivel == id_nivel).first()
        periodo_obj = db.query(Periodo).filter(Periodo.Periodo == periodo).first()

        if not unidad:
            return {"error": f"Unidad Académica con id {id_unidad_academica} no encontrada"}
        if not nivel:
            return {"error": f"Nivel con id {id_nivel} no encontrado"}

        unidad_sigla = unidad.Sigla
        nivel_nombre = nivel.Nivel
        periodo_nombre = periodo_obj.Periodo if periodo_obj else periodo

        print(f"Ejecutando SP con: Unidad={unidad_sigla}, Periodo={periodo_nombre}, Nivel={nivel_nombre}, Usuario={usuario_sp}, Host={host_sp}")

        sql = text("""
            EXEC SP_Consulta_Matricula_Unidad_Academica 
                @UUnidad_Academica = :unidad, 
                @Pperiodo = :periodo, 
                @NNivel = :nivel, 
                @UUsuario = :usuario, 
                @HHost = :host
        """)
        result = db.execute(sql, {
            'unidad': unidad_sigla, 
            'periodo': periodo_nombre, 
            'nivel': nivel_nombre,
            'usuario': usuario_sp,
            'host': host_sp
        })
        rows = result.fetchall()

        print(f"TOTAL DE FILAS DEVUELTAS: {len(rows)}")

        columns = []
        if rows:
            # Analizar el tipo de resultado
            print(f"\nTIPO DE RESULTADO: {type(rows[0])}")
            print(f"PRIMERA FILA RAW: {rows[0]}")

            # Intentar obtener nombres de columnas de diferentes maneras
            try:
                columns = list(rows[0].keys())
                print(f"\nCOLUMNAS DISPONIBLES (método keys) - {len(columns)}:")
                for i, col in enumerate(columns, 1):
                    print(f"  {i:2d}. {col}")
            except Exception as e1:
                print(f"Error con método keys(): {e1}")
                try:
                    columns = list(rows[0]._fields)
                    print(f"\nCOLUMNAS DISPONIBLES (método _fields) - {len(columns)}:")
                    for i, col in enumerate(columns, 1):
                        print(f"  {i:2d}. {col}")
                except Exception as e2:
                    print(f"Error con método _fields: {e2}")
                    attrs = [attr for attr in dir(rows[0]) if not attr.startswith('_')]
                    print(f"MÉTODOS/ATRIBUTOS DISPONIBLES: {attrs}")
                    columns = []

            # Mostrar primera fila completa
            print(f"\nPRIMERA FILA DE DATOS:")
            if columns:
                for col in columns:
                    try:
                        value = getattr(rows[0], col, 'N/A')
                        print(f"  {col}: '{value}' ({type(value).__name__})")
                    except Exception as e:
                        print(f"  {col}: ERROR - {e}")
            else:
                print(f"  No se pudieron obtener columnas, fila raw: {rows[0]}")

            # Mostrar todas las filas (máximo 20 para no saturar)
            print(f"\nTODAS LAS FILAS (máximo 20):")
            for i, row in enumerate(rows[:20], 1):
                print(f"\nFila {i}:")
                if columns:
                    for col in columns:
                        try:
                            value = getattr(row, col, 'N/A')
                            print(f"  {col}: {value}")
                        except Exception as e:
                            print(f"  {col}: ERROR - {e}")
                else:
                    print(f"  Fila raw: {row}")
                print("-" * 40)

            if len(rows) > 20:
                print(f"\n... y {len(rows) - 20} filas más")

            # Análisis de valores únicos por columna
            if columns:
                print(f"\nANÁLISIS DE VALORES ÚNICOS POR COLUMNA:")
                for col in columns:
                    try:
                        unique_values = set()
                        for row in rows:
                            try:
                                value = getattr(row, col, None)
                                if value is not None:
                                    unique_values.add(str(value))
                            except Exception:
                                continue

                        print(f"\n{col}:")
                        if len(unique_values) <= 10:
                            for val in sorted(unique_values):
                                print(f"  - '{val}'")
                        else:
                            sorted_vals = sorted(unique_values)
                            print(f"  Primeros 10 valores de {len(unique_values)} únicos:")
                            for val in sorted_vals[:10]:
                                print(f"  - '{val}'")
                            print(f"  ... y {len(unique_values) - 10} más")
                    except Exception as e:
                        print(f"\nError analizando columna {col}: {e}")
        else:
            print("EL SP NO DEVOLVIÓ DATOS")

        print(f"{'='*60}")

        return {
            "mensaje": f"SP ejecutado - {len(rows)} filas devueltas",
            "total_filas": len(rows),
            "columnas": columns,
            "primera_fila": str(rows[0]) if rows else None
        }

    except Exception as e:
        print(f"ERROR AL EJECUTAR SP: {str(e)}")
        return {"error": str(e)}

@router.get('/semestres_map')
async def semestres_map_sp(db: Session = Depends(get_db)):
    """Endpoint para obtener el mapeo de semestres (Id -> Nombre)"""
    try:
        semestres = db.query(Semestre).all()
        semestres_map = {s.Id_Semestre: s.Semestre for s in semestres}
        return semestres_map
    except Exception as e:
        return {"error": str(e)}

@router.post("/guardar_captura_completa")
async def guardar_captura_completa(request: Request, db: Session = Depends(get_db)):
    """
    Guardar la captura completa de matrícula enviada desde el frontend.
    Convierte el formato del frontend al modelo Temp_Matricula.
    """
    try:
        data = await request.json()
        print(f"\n=== GUARDANDO CAPTURA COMPLETA ===")
        print(f"Datos recibidos: {data}")
        
        # Obtener datos del usuario desde cookies
        nombre_usuario = request.cookies.get("nombre_usuario", "")
        apellidoP_usuario = request.cookies.get("apellidoP_usuario", "")
        apellidoM_usuario = request.cookies.get("apellidoM_usuario", "")
        nombre_completo = " ".join(filter(None, [nombre_usuario, apellidoP_usuario, apellidoM_usuario]))
        
        # Obtener usuario y host
        usuario_sp = nombre_completo or 'sistema'
        host_sp = get_request_host(request)
        
        # Extraer información base
        periodo = data.get('periodo')
        programa = data.get('programa')
        semestre = data.get('semestre')
        modalidad = data.get('modalidad')
        turno = data.get('turno')
        datos_matricula = data.get('datos_matricula', {})
        
        if not datos_matricula:
            return {"error": "No se encontraron datos de matrícula para guardar"}
        
        # Obtener campos válidos del modelo Temp_Matricula
        valid_fields = set(Temp_Matricula.__annotations__.keys())
        print(f"Campos válidos Temp_Matricula: {valid_fields}")
        
        # Obtener nombres desde la base de datos para mapear IDs
        programa_obj = db.query(Programas).filter(Programas.Id_Programa == int(programa)).first()
        modalidad_obj = db.query(Modalidad).filter(Modalidad.Id_Modalidad == int(modalidad)).first()
        turno_obj = db.query(Turno).filter(Turno.Id_Turno == int(turno)).first()
        semestre_obj = db.query(Semestre).filter(Semestre.Id_Semestre == int(semestre)).first()
        
        # Obtener Nombre_Rama desde el programa
        rama_obj = None
        if programa_obj and programa_obj.Id_Rama_Programa:
            rama_obj = db.query(Rama).filter(Rama.Id_Rama == programa_obj.Id_Rama_Programa).first()

        # Obtener sigla de la unidad académica y nivel desde cookies
        id_unidad_academica = int(request.cookies.get("id_unidad_academica", 0))
        id_nivel = int(request.cookies.get("id_nivel", 0))
        
        unidad_obj = db.query(Unidad_Academica).filter(
            Unidad_Academica.Id_Unidad_Academica == id_unidad_academica
        ).first()
        
        nivel_obj = db.query(Nivel).filter(Nivel.Id_Nivel == id_nivel).first()
        
        # Obtener mapeos de grupos de edad y tipos de ingreso para convertir a nombres
        grupos_edad_db = db.query(Grupo_Edad).all()
        grupos_edad_map = {str(g.Id_Grupo_Edad): g.Grupo_Edad for g in grupos_edad_db}
        
        tipos_ingreso_db = db.query(Tipo_Ingreso).all()
        tipos_ingreso_map = {str(t.Id_Tipo_Ingreso): t.Tipo_de_Ingreso for t in tipos_ingreso_db}
        
        registros_insertados = 0
        
        # Procesar cada registro de matrícula
        for key, dato in datos_matricula.items():
            # Mapear grupo_edad ID a nombre completo
            grupo_edad_id = str(dato.get('grupo_edad', ''))
            grupo_edad_nombre = grupos_edad_map.get(grupo_edad_id, grupo_edad_id)
            
            # Mapear tipo_ingreso ID a nombre completo
            tipo_ingreso_id = str(dato.get('tipo_ingreso', ''))
            tipo_ingreso_nombre = tipos_ingreso_map.get(tipo_ingreso_id, tipo_ingreso_id)
            
            # Convertir sexo de M/F a Hombre/Mujer
            sexo_corto = dato.get('sexo', '')
            if sexo_corto == 'M':
                sexo_completo = 'Hombre'
            elif sexo_corto == 'F':
                sexo_completo = 'Mujer'
            else:
                sexo_completo = sexo_corto
            
            # Construir registro para Temp_Matricula
            registro = {
                'Periodo': periodo,
                'Sigla': unidad_obj.Sigla if unidad_obj else 'UNK',
                'Nombre_Programa': programa_obj.Nombre_Programa if programa_obj else '',
                'Nombre_Rama': rama_obj.Nombre_Rama if rama_obj else 'NULL',
                'Nivel': nivel_obj.Nivel if nivel_obj else '',
                'Modalidad': modalidad_obj.Modalidad if modalidad_obj else '',
                'Turno': turno_obj.Turno if turno_obj else '',
                'Semestre': semestre_obj.Semestre if semestre_obj else '',
                'Grupo_Edad': grupo_edad_nombre,
                'Tipo_Ingreso': tipo_ingreso_nombre,
                'Sexo': sexo_completo,
                'Matricula': int(dato.get('matricula', 0))
            }
            
            # Filtrar solo campos válidos
            filtered = {k: v for k, v in registro.items() if k in valid_fields}
            
            if filtered and filtered.get('Matricula', 0) > 0:
                temp_matricula = Temp_Matricula(**filtered)
                db.add(temp_matricula)
                registros_insertados += 1
                print(f"Registro agregado: {filtered}")
        
        db.commit()
        
        return {
            "mensaje": f"Matrícula guardada exitosamente. {registros_insertados} registros insertados.",
            "registros_insertados": registros_insertados
        }
        
    except Exception as e:
        db.rollback()
        print(f"ERROR al guardar captura completa: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al guardar la matrícula: {str(e)}")

@router.post("/guardar_progreso")
def guardar_progreso(datos: List[Dict[str, Any]], db: Session = Depends(get_db)):
    """
    Guardar el progreso de la matrícula en la tabla Temp_Matricula.
    Args:
        datos: Lista de diccionarios con los datos de la matrícula.
        db: Sesión de base de datos.
    Returns:
        Mensaje de éxito o error.
    """
    try:
        # Obtener campos válidos desde el modelo Temp_Matricula
        valid_fields = set()
        # Intentar leer anotaciones (Python typing) si están presentes
        try:
            valid_fields = set(Temp_Matricula.__annotations__.keys())
        except Exception:
            # Fallback: leer atributos públicos definidos en la clase
            valid_fields = {k for k in dir(Temp_Matricula) if not k.startswith('_')}

        print(f"Campos válidos Temp_Matricula: {valid_fields}")

        for dato in datos:
            # Filtrar solo las claves que estén en el modelo
            filtered = {k: v for k, v in dato.items() if k in valid_fields}
            if not filtered:
                # Si no hay campos válidos, saltar
                print(f"Advertencia: entrada sin campos válidos será ignorada: {dato}")
                continue
            temp_matricula = Temp_Matricula(**filtered)
            db.add(temp_matricula)

        db.commit()
        return {"message": "Progreso guardado exitosamente."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al guardar el progreso: {str(e)}")

