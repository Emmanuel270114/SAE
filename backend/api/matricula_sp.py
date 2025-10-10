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

router = APIRouter()


@router.get('/consulta', response_class=None)
async def captura_matricula_sp_view(request: Request, db: Session = Depends(get_db)):
    """
    Endpoint para servir la página de captura de matrícula usando SP.
    Solo accesible para usuarios con rol 'Capturista'.
    Idéntico a captura_matricula.html pero usa SP para obtener datos existentes.
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
    
    # Obtener grupos de edad que pertenezcan al nivel del usuario (sin repetir)
    grupos_edad_ids = db.query(Matricula.Id_Grupo_Edad).filter(
        Matricula.Id_Nivel == id_nivel,
        Matricula.Id_Unidad_Academica == id_unidad_academica
    ).distinct().all()
    grupos_edad_ids_list = [g.Id_Grupo_Edad for g in grupos_edad_ids]
    
    if grupos_edad_ids_list:
        grupos_edad = db.query(Grupo_Edad).filter(Grupo_Edad.Id_Grupo_Edad.in_(grupos_edad_ids_list)).all()
    else:
        grupos_edad = []
    
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

    # Definir periodo por defecto (Id_Periodo = 9) y la unidad académica actual
    periodo_default_id = 9
    unidad_actual = unidades_academicas[0] if unidades_academicas else None

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
        "turnos": turnos,
        "grupos_edad": grupos_edad,
        "tipos_ingreso": tipos_ingreso
    })

# Endpoint para obtener datos existentes usando SP
@router.post("/obtener_datos_existentes_sp")
async def obtener_datos_existentes_sp(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Endpoint para obtener datos existentes usando SP - con logs detallados.
    """
    try:
        data = await request.json()
        print(f"\n=== DEBUG SP - Parámetros recibidos ===")
        print(f"Datos JSON: {data}")

        # Obtener parámetros del JSON
        periodo = data.get('periodo') or '2025-2026/1'  # default
        programa = data.get('programa')
        modalidad = data.get('modalidad')
        semestre = data.get('semestre')
        turno = data.get('turno')

        # Obtener datos del usuario desde cookies (usar UA y Nivel del usuario que inició sesión)
        id_unidad_academica = int(request.cookies.get("id_unidad_academica", 0))
        id_nivel = int(request.cookies.get("id_nivel", 0))

        print(f"ID Unidad Académica (cookie): {id_unidad_academica}")
        print(f"ID Nivel (cookie): {id_nivel}")

        # Validar y obtener nombres para el SP usando ORM
        unidad = db.query(Unidad_Academica).filter(Unidad_Academica.Id_Unidad_Academica == id_unidad_academica).first()
        nivel = db.query(Nivel).filter(Nivel.Id_Nivel == id_nivel).first()
        # periodo puede venir como Id (e.g., '9') o como literal ('2025-2026/1')
        periodo_obj = None
        if periodo:
            try:
                # intentar interpretar como Id
                periodo_id = int(periodo)
                periodo_obj = db.query(Periodo).filter(Periodo.Id_Periodo == periodo_id).first()
            except Exception:
                # no es numérico, buscar por literal
                periodo_obj = db.query(Periodo).filter(Periodo.Periodo == periodo).first()

        if not unidad:
            print(f"Error: Unidad Académica con id {id_unidad_academica} no encontrada")
            return {"error": "Unidad Académica no encontrada"}
        if not nivel:
            print(f"Error: Nivel con id {id_nivel} no encontrado")
            return {"error": "Nivel no encontrado"}
        if not periodo_obj:
            print(f"Aviso: Periodo '{periodo}' no encontrado en CatPeriodo, se usará literal")

        unidad_sigla = unidad.Sigla
        nivel_nombre = nivel.Nivel
        periodo_nombre = periodo_obj.Periodo if periodo_obj else periodo

        print(f"Parámetros resueltos para SP:")
        print(f"  - Unidad (sigla): {unidad_sigla}")
        print(f"  - Periodo: {periodo_nombre}")
        print(f"  - Nivel: {nivel_nombre}")

        # Ejecutar el SP con parámetros seguros (evitar concatenación de strings)
        # Nota: SQL Server acepta named parameters con :name usando text(); adaptador puede variar.
        sql = text("EXEC SP_Consulta_Matricula_Unidad_Academica @Unidad_Academica = :unidad, @periodo = :periodo, @nivel = :nivel")
        result = db.execute(sql, {'unidad': unidad_sigla, 'periodo': periodo_nombre, 'nivel': nivel_nombre})
        rows = result.fetchall()

        # Obtener nombres de columnas si el driver los provee
        try:
            columns = result.keys()
        except Exception:
            columns = []

        print(f"\n=== RESULTADOS DEL SP ===")
        print(f"Total de filas devueltas: {len(rows)}")

        def safe_row_to_dict(row, cols=None):
            # row puede ser Row, namedtuple, tuple, list, etc.
            # Priorizar mapping API si existe
            try:
                if hasattr(row, '_mapping'):
                    return dict(row._mapping)
            except Exception:
                pass
            try:
                if hasattr(row, '_asdict'):
                    return row._asdict()
            except Exception:
                pass
            # Si es tupla/lista, usar cols para mapear
            try:
                if isinstance(row, (list, tuple)) and cols:
                    return {cols[i]: row[i] for i in range(min(len(cols), len(row)))}
            except Exception:
                pass
            # Fallback: intentar dict(row)
            try:
                return dict(row)
            except Exception:
                # última opción: inspeccionar atributos públicos
                rd = {}
                for attr in dir(row):
                    if not attr.startswith('_') and not callable(getattr(row, attr)):
                        try:
                            rd[attr] = getattr(row, attr)
                        except Exception:
                            continue
                return rd

        if rows:
            # Mostrar estructura de la primera fila
            first_row = safe_row_to_dict(rows[0], columns)
            print(f"\nEstructura de datos (primera fila):")
            for key, value in first_row.items():
                print(f"  - {key}: {value} ({type(value).__name__})")

            # Mostrar primeras 5 filas completas
            print(f"\nPrimeras 5 filas de datos:")
            for i, row in enumerate(rows[:5]):
                row_dict = safe_row_to_dict(row, columns)
                print(f"Fila {i+1}: {row_dict}")

            # Mostrar valores únicos de campos importantes
            tipos_ingreso = set()
            grupos_edad = set()
            sexos = set()
            programas = set()
            modalidades = set()
            semestres = set()
            turnos = set()

            for row in rows:
                row_dict = safe_row_to_dict(row, columns)
                if 'Tipo_de_Ingreso' in row_dict:
                    tipos_ingreso.add(row_dict['Tipo_de_Ingreso'])
                if 'Grupo_Edad' in row_dict:
                    grupos_edad.add(row_dict['Grupo_Edad'])
                if 'Sexo' in row_dict:
                    sexos.add(row_dict['Sexo'])
                if 'Nombre_Programa' in row_dict:
                    programas.add(row_dict['Nombre_Programa'])
                if 'Modalidad' in row_dict:
                    modalidades.add(row_dict['Modalidad'])
                if 'Semestre' in row_dict:
                    semestres.add(row_dict['Semestre'])
                if 'Turno' in row_dict:
                    turnos.add(row_dict['Turno'])

            print(f"\nValores únicos encontrados:")
            print(f"  - Tipos de Ingreso: {sorted(tipos_ingreso)}")
            print(f"  - Grupos de Edad: {sorted(grupos_edad)}")
            print(f"  - Sexos: {sorted(sexos)}")
            print(f"  - Programas: {sorted(programas)}")
            print(f"  - Modalidades: {sorted(modalidades)}")
            print(f"  - Semestres: {sorted(semestres)}")
            print(f"  - Turnos: {sorted(turnos)}")

        # Normalizar filas a listas de dicts serializables
        rows_list = []
        for row in rows:
            try:
                row_dict = safe_row_to_dict(row, columns)

                # Convertir tipos no serializables a string cuando sea necesario
                for k, v in list(row_dict.items()):
                    if isinstance(v, (bytes, bytearray)):
                        try:
                            row_dict[k] = v.decode('utf-8', errors='ignore')
                        except Exception:
                            row_dict[k] = str(v)
                    elif not isinstance(v, (str, int, float, bool, type(None))):
                        row_dict[k] = str(v)

                rows_list.append(row_dict)
            except Exception:
                continue

        # Preparar mapeos desde las tablas de catálogo para resolver nombres a IDs
        tipos_db = db.query(Tipo_Ingreso).all()
        tipos_by_id = {t.Id_Tipo_Ingreso: t for t in tipos_db}
        tipos_by_name = {str(t.Tipo_de_Ingreso).strip().lower(): t for t in tipos_db}

        grupos_db = db.query(Grupo_Edad).all()
        grupos_by_id = {g.Id_Grupo_Edad: g for g in grupos_db}
        grupos_by_name = {str(g.Grupo_Edad).strip().lower(): g for g in grupos_db}

        sexos_db = db.query(Sexo).all()
        sexos_by_id = {s.Id_Sexo: s for s in sexos_db}
        sexos_by_name = {str(getattr(s, 'Sexo', '')).strip().lower(): s for s in sexos_db}

        def get_first(rowd, candidates):
            for c in candidates:
                if c in rowd and rowd[c] is not None:
                    return rowd[c]
            return None

        def normalize_sexo(val):
            if val is None:
                return None
            try:
                if isinstance(val, (int, float)):
                    if int(val) == 1:
                        return 'M'
                    if int(val) == 2:
                        return 'F'
            except Exception:
                pass
            s = str(val).strip().lower()
            if not s:
                return None
            if s.startswith('m'):
                return 'M'
            if s.startswith('f'):
                return 'F'
            # try matching spanish words
            if 'mas' in s:
                return 'M'
            if 'fem' in s:
                return 'F'
            # fallback: first char
            return s[0].upper()

        datos_map = {}
        # candidatos posibles de columnas en el row_dict
        tipo_id_cands = ['Id_Tipo_Ingreso', 'Id_TipoIngreso', 'IdTipoIngreso', 'Tipo_Id']
        tipo_name_cands = ['Tipo_de_Ingreso', 'TipoIngreso', 'Tipo_Ingreso', 'Tipo']

        grupo_id_cands = ['Id_Grupo_Edad', 'Id_GrupoEdad', 'IdGrupoEdad']
        grupo_name_cands = ['Grupo_Edad', 'GrupoEdad', 'Grupo']

        sexo_id_cands = ['Id_Sexo', 'IdSexo']
        sexo_name_cands = ['Sexo', 'Nombre_Sexo', 'Genero']

        matricula_cands = ['Matricula', 'Total', 'Cantidad', 'Numero', 'Valor']

        for rd in rows_list:
            try:
                tipo_id = get_first(rd, tipo_id_cands)
                if tipo_id is None:
                    tipo_name = get_first(rd, tipo_name_cands)
                    if tipo_name:
                        tipo_obj = tipos_by_name.get(str(tipo_name).strip().lower())
                        tipo_id = tipo_obj.Id_Tipo_Ingreso if tipo_obj else None

                grupo_id = get_first(rd, grupo_id_cands)
                if grupo_id is None:
                    grupo_name = get_first(rd, grupo_name_cands)
                    if grupo_name:
                        grupo_obj = grupos_by_name.get(str(grupo_name).strip().lower())
                        grupo_id = grupo_obj.Id_Grupo_Edad if grupo_obj else None

                sexo_val = get_first(rd, sexo_id_cands) or get_first(rd, sexo_name_cands)
                sexo_norm = normalize_sexo(sexo_val)

                # Obtener valor de matrícula
                matricula_val = get_first(rd, matricula_cands)
                try:
                    matricula_val = int(matricula_val) if matricula_val is not None else 0
                except Exception:
                    try:
                        matricula_val = int(float(matricula_val))
                    except Exception:
                        matricula_val = 0

                if tipo_id is None or grupo_id is None or sexo_norm is None:
                    # no podemos mapear esta fila a una celda; saltarla
                    continue

                key = f"{int(tipo_id)}_{int(grupo_id)}_{sexo_norm}"
                # Si hay múltiples filas para la misma clave, sumamos
                datos_map[key] = datos_map.get(key, 0) + matricula_val
            except Exception:
                continue

        return {"datos": datos_map, "rows": rows_list, "debug": f"SP ejecutado correctamente, {len(rows)} filas devueltas"}

    except Exception as e:
        print(f"ERROR en SP: {str(e)}")
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

