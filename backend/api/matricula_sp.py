from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import json

from backend.core.templates import templates
from backend.database.connection import get_db
from backend.database.models.Matricula import Matricula
from backend.database.models.CatPeriodo import CatPeriodo as Periodo
from backend.database.models.CatUnidadAcademica import CatUnidadAcademica as Unidad_Academica
from backend.database.models.CatProgramas import CatProgramas as Programas
from backend.database.models.CatRama import CatRama as Rama
from backend.database.models.CatNivel import CatNivel as Nivel
from backend.database.models.CatModalidad import CatModalidad as Modalidad
from backend.database.models.CatTurno import CatTurno as Turno
from backend.database.models.CatSemestre import CatSemestre as Semestre
from backend.database.models.CatGrupoEdad import CatGrupoEdad as Grupo_Edad
from backend.database.models.CatTipoIngreso import TipoIngreso as Tipo_Ingreso
from backend.database.models.CatSexo import CatSexo as Sexo
from backend.services.matricula_service import execute_matricula_sp_with_context

router = APIRouter()


@router.get('/consulta')
async def captura_matricula_sp_view(request: Request, db: Session = Depends(get_db)):
    """
    Endpoint principal para la captura de matrícula usando Stored Procedures.
    Solo accesible para usuarios con rol 'Capturista'.
    Utiliza SP para obtener datos existentes y permite captura con validaciones mejoradas.
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

    # Obtener datos para los filtros desde la base de datos
    periodos = db.query(Periodo).all()
    unidades_academicas = db.query(Unidad_Academica).filter(Unidad_Academica.Id_Unidad_Academica == id_unidad_academica).all()
    # Filtrar programas por la Unidad Académica del usuario usando la tabla Matricula
    programas_ids = db.query(Matricula.Id_Programa).filter(Matricula.Id_Unidad_Academica == id_unidad_academica).distinct().all()
    programa_ids_list = [p.Id_Programa for p in programas_ids]
    if programa_ids_list:
        programas = db.query(Programas).filter(Programas.Id_Programa.in_(programa_ids_list), Programas.Id_Nivel == id_nivel).all()
    else:
        programas = []
    modalidades = db.query(Modalidad).all()
    semestres = db.query(Semestre).all()
    turnos = db.query(Turno).all()
    
    # Obtener grupos de edad dinámicamente del SP
    try:
        # Ejecutar SP para obtener grupos de edad disponibles
        rows_sp, _, _ = execute_matricula_sp_with_context(
            db=db,
            id_unidad_academica=id_unidad_academica,
            id_nivel=id_nivel,
            periodo_input='2025-2026/1',
            default_periodo='2025-2026/1'
        )
        
        # Extraer IDs únicos de grupos de edad del SP
        grupos_edad_ids_from_sp = set()
        for row in rows_sp:
            # Buscar columnas que contengan información de grupo de edad
            for key, value in row.items():
                if 'grupo' in key.lower() and 'edad' in key.lower() and 'id' in key.lower():
                    if value is not None:
                        try:
                            grupos_edad_ids_from_sp.add(int(value))
                        except (ValueError, TypeError):
                            pass
        
        # Obtener objetos de grupos de edad basados en IDs del SP
        if grupos_edad_ids_from_sp:
            grupos_edad = db.query(Grupo_Edad).filter(
                Grupo_Edad.Id_Grupo_Edad.in_(list(grupos_edad_ids_from_sp))
            ).all()
            print(f"Grupos de edad obtenidos del SP: {len(grupos_edad)}")
            for grupo in grupos_edad:
                print(f"- ID: {grupo.Id_Grupo_Edad}, Grupo: {grupo.Grupo_Edad}")
        else:
            # Fallback: obtener todos los grupos de edad
            grupos_edad = db.query(Grupo_Edad).all()
            print(f"Usando todos los grupos de edad como fallback: {len(grupos_edad)}")
    except Exception as e:
        print(f"Error obteniendo grupos de edad del SP: {e}")
        # Fallback: obtener todos los grupos de edad
        grupos_edad = db.query(Grupo_Edad).all()
    
    # Obtener tipos de ingreso usando solo ORM
    try:
        tipos_ingreso = db.query(Tipo_Ingreso).all()
        print(f"Tipos de ingreso obtenidos: {len(tipos_ingreso)}")
        for tipo in tipos_ingreso:
            print(f"- ID: {tipo.Id_Tipo_Ingreso}, Nombre: {tipo.Tipo_de_Ingreso}")
                
    except Exception as e:
        print(f"Error al obtener tipos de ingreso: {e}")
        tipos_ingreso = []
    
    # Construir un mapping simple id -> etiqueta de semestre serializado a JSON
    semestres_map = {s.Id_Semestre: s.Semestre for s in semestres}
    semestres_map_json = json.dumps(semestres_map, ensure_ascii=False)

    # Convertir turnos a lista de diccionarios para serialización JSON
    turnos_list = [{"Id_Turno": t.Id_Turno, "Turno": t.Turno} for t in turnos]

    # Definir periodo por defecto (Id_Periodo = 9) y la unidad académica actual
    periodo_default_id = 9
    unidad_actual = unidades_academicas[0] if unidades_academicas else None

    # Convertir grupos de edad a diccionarios para serialización JSON
    grupos_edad_dicts = [{"Id_Grupo_Edad": g.Id_Grupo_Edad, "Grupo_Edad": g.Grupo_Edad} for g in grupos_edad]

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
        "programas": programas,
        "modalidades": modalidades,
        "semestres": semestres,
        "semestres_map_json": semestres_map_json,
        "turnos": turnos_list,
        "grupos_edad": grupos_edad_dicts,
        "tipos_ingreso": tipos_ingreso
    })

# Endpoint para obtener datos existentes usando SP
@router.post("/obtener_datos_existentes_sp")
async def obtener_datos_existentes_sp(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Endpoint para obtener datos existentes usando SP - refactorizado para usar servicio centralizado.
    """
    try:
        data = await request.json()
        print(f"\n=== DEBUG SP - Parámetros recibidos ===")
        print(f"Datos JSON: {data}")

        # Obtener parámetros del JSON
        periodo = data.get('periodo')
        
        # Obtener datos del usuario desde cookies (usar UA y Nivel del usuario que inició sesión)
        id_unidad_academica = int(request.cookies.get("id_unidad_academica", 0))
        id_nivel = int(request.cookies.get("id_nivel", 0))

        print(f"ID Unidad Académica (cookie): {id_unidad_academica}")
        print(f"ID Nivel (cookie): {id_nivel}")

        # Usar servicio centralizado para ejecutar SP
        rows_list, datos_map, debug_msg = execute_matricula_sp_with_context(
            db=db,
            id_unidad_academica=id_unidad_academica,
            id_nivel=id_nivel,
            periodo_input=periodo,
            default_periodo='2025-2026/1'
        )
        
        print(f"\n=== RESULTADOS DEL SP ===")
        print(debug_msg)

        if rows_list:
            # Mostrar estructura de la primera fila
            first_row = rows_list[0]
            print(f"\nEstructura de datos (primera fila):")
            for key, value in first_row.items():
                print(f"  - {key}: {value} ({type(value).__name__})")

            # Mostrar primeras 5 filas completas
            print(f"\nPrimeras 5 filas de datos:")
            for i, row_dict in enumerate(rows_list[:5]):
                print(f"Fila {i+1}: {row_dict}")

        # Manejar valores NULL para mostrar campos vacíos en lugar de 0
        rows_processed = []
        for row in rows_list:
            processed_row = {}
            for key, value in row.items():
                # Si el valor es NULL o None, convertirlo a cadena vacía
                if value is None or (isinstance(value, str) and value.upper() == 'NULL'):
                    processed_row[key] = ""
                else:
                    processed_row[key] = value
            rows_processed.append(processed_row)

        # Log de valores únicos detectados por columna
        print("\n=== ANÁLISIS DE VALORES ÚNICOS POR COLUMNA ===")
        if rows_processed:
            for col in rows_processed[0].keys():
                unique_values = set()
                for row in rows_processed:
                    if row[col] is not None and row[col] != "":
                        unique_values.add(str(row[col]))
                print(f"Columna '{col}': {len(unique_values)} valores únicos -> {sorted(unique_values)}")
        else:
            print("No hay filas para analizar valores únicos.")

        # Devolver resultado exitoso o error
        if "Error" in debug_msg:
            return {"error": debug_msg}
        else:
            return {"datos": datos_map, "rows": rows_processed, "debug": debug_msg}

    except Exception as e:
        print(f"ERROR en endpoint SP: {str(e)}")
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
        periodo = '2025-2026/1'

        print(f"ID Unidad Académica (cookie): {id_unidad_academica}")
        print(f"ID Nivel (cookie): {id_nivel}")
        print(f"Periodo (forzado): {periodo}")

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

        print(f"Ejecutando SP con: Unidad={unidad_sigla}, Periodo={periodo_nombre}, Nivel={nivel_nombre}")

        sql = text("EXEC SP_Consulta_Matricula_Unidad_Academica @Unidad_Academica = :unidad, @periodo = :periodo, @nivel = :nivel")
        result = db.execute(sql, {'unidad': unidad_sigla, 'periodo': periodo_nombre, 'nivel': nivel_nombre})
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

