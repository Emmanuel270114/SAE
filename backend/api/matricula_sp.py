from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import json

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
from backend.services.matricula_service import (
    execute_matricula_sp_with_context,
    get_matricula_metadata_from_sp
)
from backend.utils.request import get_request_host

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
                @Unidad_Academica = :unidad, 
                @Pperiodo = :periodo, 
                @nivel = :nivel, 
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


@router.post('/guardar_captura_completa')
async def guardar_captura_completa(request: Request, db: Session = Depends(get_db)):
    """
    Endpoint para guardar la captura completa de matrícula con la nueva estructura.
    """
    try:
        # Obtener datos del usuario logueado desde las cookies
        id_unidad_academica = int(request.cookies.get("id_unidad_academica", 0))
        id_nivel = int(request.cookies.get("id_nivel", 0))
        id_usuario = int(request.cookies.get("id_usuario", 0))
        
        # Obtener datos del cuerpo de la petición
        data = await request.json()
        
        periodo = data.get('periodo')
        programa = data.get('programa')
        semestre = data.get('semestre')
        modalidad = data.get('modalidad')
        turno = data.get('turno')
        datos_matricula = data.get('datos_matricula', {})
        
        if not all([periodo, programa, semestre, modalidad, turno]):
            return {"error": "Faltan datos obligatorios en la solicitud"}
        
        # Eliminar registros existentes para esta combinación
        db.query(Matricula).filter(
            Matricula.Id_Periodo == periodo,
            Matricula.Id_Programa == programa,
            Matricula.Id_Semestre == semestre,
            Matricula.Id_Modalidad == modalidad,
            Matricula.Id_Turno == turno,
            Matricula.Id_Unidad_Academica == id_unidad_academica,
            Matricula.Id_Nivel == id_nivel
        ).delete()
        
        # Insertar nuevos registros
        registros_creados = 0
        for key, data_item in datos_matricula.items():
            tipo_ingreso = int(data_item['tipo_ingreso'])
            grupo_edad = int(data_item['grupo_edad'])
            sexo = data_item['sexo']
            matricula_valor = int(data_item['matricula'])
            
            # Determinar Id_Sexo (1 = Masculino, 2 = Femenino)
            id_sexo = 1 if sexo == 'M' else 2
            
            # Crear nuevo registro de matrícula
            nueva_matricula = Matricula(
                Id_Periodo=periodo,
                Id_Unidad_Academica=id_unidad_academica,
                Id_Programa=programa,
                Id_Nivel=id_nivel,
                Id_Semestre=semestre,
                Id_Modalidad=modalidad,
                Id_Turno=turno,
                Id_Tipo_Ingreso=tipo_ingreso,
                Id_Grupo_Edad=grupo_edad,
                Id_Sexo=id_sexo,
                Matricula=matricula_valor,
                Id_Usuario=id_usuario
            )
            
            db.add(nueva_matricula)
            registros_creados += 1
        
        # Confirmar los cambios
        db.commit()
        
        return {
            "mensaje": f"Matrícula guardada exitosamente. Se crearon {registros_creados} registros.",
            "registros_creados": registros_creados
        }
        
    except Exception as e:
        db.rollback()
        return {"error": f"Error al guardar la matrícula: {str(e)}"}

