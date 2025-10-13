"""Servicio para operaciones de matrícula usando CRUD centralizado."""

from backend.crud.Matricula import (
    get_matricula_by_filters,
    get_distinct_programa_ids_by_unidad,
    get_distinct_grupo_edad_ids_by_unidad_nivel,
    execute_sp_consulta_matricula,
    resolve_periodo_by_id_or_literal,
    get_unidad_and_nivel_info,
    safe_row_to_dict,
)
from backend.database.models.CatTipoIngreso import TipoIngreso as Tipo_Ingreso
from backend.database.models.CatGrupoEdad import CatGrupoEdad as Grupo_Edad
from backend.database.models.CatSexo import CatSexo as Sexo

from sqlalchemy.orm import Session
from typing import Dict, List, Any, Optional, Tuple


def get_programas_ids_for_unidad(db: Session, id_unidad_academica: int) -> List[int]:
    """Obtener lista de IDs de programas disponibles para una unidad académica."""
    return get_distinct_programa_ids_by_unidad(db, id_unidad_academica)


def get_grupos_edad_ids_for_unidad_nivel(db: Session, id_unidad_academica: int, id_nivel: int) -> List[int]:
    """Obtener lista de IDs de grupos de edad para una unidad académica y nivel."""
    return get_distinct_grupo_edad_ids_by_unidad_nivel(db, id_unidad_academica, id_nivel)


def execute_matricula_sp_with_context(
    db: Session,
    id_unidad_academica: int,
    id_nivel: int,
    periodo_input: Optional[str] = None,
    default_periodo: str = "2025-2026/1"
) -> Tuple[List[Dict[str, Any]], Dict[str, int], str]:
    """
    Ejecutar SP de matrícula con contexto de usuario y devolver datos normalizados.
    
    Args:
        db: Sesión de base de datos
        id_unidad_academica: ID de la unidad académica del usuario
        id_nivel: ID del nivel del usuario
        periodo_input: Periodo como ID o literal (opcional)
        default_periodo: Periodo por defecto
        
    Returns:
        Tuple[List[Dict], Dict[str, int], str]: (filas_sp, datos_mapa, mensaje_debug)
    """
    try:
        # Resolver información de unidad y nivel
        unidad_sigla, nivel_nombre = get_unidad_and_nivel_info(db, id_unidad_academica, id_nivel)
        
        if not unidad_sigla:
            return [], {}, f"Error: Unidad Académica con id {id_unidad_academica} no encontrada"
        if not nivel_nombre:
            return [], {}, f"Error: Nivel con id {id_nivel} no encontrado"
            
        # Resolver periodo
        periodo_nombre = resolve_periodo_by_id_or_literal(db, periodo_input or default_periodo, default_periodo)
        
        # Ejecutar SP
        rows_list, columns = execute_sp_consulta_matricula(db, unidad_sigla, periodo_nombre, nivel_nombre)
        
        # Log detallado de las filas obtenidas del SP
        print("\n=== DEBUG: FILAS OBTENIDAS DEL SP ===")
        if rows_list:
            for i, row in enumerate(rows_list[:5]):
                print(f"Fila {i+1}: {row}")
        else:
            print("No se obtuvieron filas del SP.")
        
        # FILTRAR SOLO REGISTROS CON ESTATUS ACTIVO
        estatus_cands = ['Id_Estatus', 'IdEstatus', 'Estatus', 'Id_Status', 'Status', 'Estado']
        
        def is_active(row_dict):
            """Verificar si un registro tiene estatus activo."""
            # Primero mostrar todas las columnas de la fila para debug
            if not hasattr(is_active, 'debug_shown'):
                print(f"DEBUG: Columnas disponibles en fila SP: {list(row_dict.keys())}")
                is_active.debug_shown = True
                
            for cand in estatus_cands:
                if cand in row_dict:
                    val = row_dict[cand]
                    print(f"DEBUG: Encontrado campo {cand} con valor: {val} (tipo: {type(val)})")
                    if isinstance(val, (int, float)) and int(val) == 1:
                        return True
                    elif isinstance(val, str) and ('activ' in val.lower() or val == '1'):
                        return True
            
            # Si no encontramos campo de estatus, asumir activo por defecto
            print("DEBUG: No se encontró campo de estatus, asumiendo activo")
            return True
        
        active_rows = [row for row in rows_list if is_active(row)]
        
        print(f"\n=== FILTRO DE ESTATUS (rows_list) ===")
        print(f"Total de filas del SP: {len(rows_list)}")
        print(f"Filas con estatus ACTIVO: {len(active_rows)}")
        
        # Construir mapa de datos agregados (solo con filas activas)
        datos_map = build_datos_map_from_sp_rows(db, active_rows)
        
        debug_msg = f"SP ejecutado correctamente, {len(rows_list)} filas totales, {len(active_rows)} activas. Unidad: {unidad_sigla}, Periodo: {periodo_nombre}, Nivel: {nivel_nombre}"
        
        return active_rows, datos_map, debug_msg
        
    except Exception as e:
        error_msg = f"Error al ejecutar SP de matrícula: {str(e)}"
        print(error_msg)
        return [], {}, error_msg


def build_datos_map_from_sp_rows(db: Session, rows_list: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Construir mapa de datos {tipo_grupo_sexo: total} a partir de filas del SP.
    SOLO INCLUYE REGISTROS CON ESTATUS ACTIVO (Id_Estatus = 1 o Estatus = 'Activo')
    
    Args:
        db: Sesión de base de datos
        rows_list: Lista de filas del SP como diccionarios
        
    Returns:
        Dict[str, int]: Mapa con claves como "1_2_M" y valores como totales
    """
    # FILTRAR SOLO REGISTROS CON ESTATUS ACTIVO
    estatus_cands = ['Id_Estatus', 'IdEstatus', 'Estatus', 'Id_Status', 'Status']
    
    def is_active(row_dict):
        """Verificar si un registro tiene estatus activo."""
        for cand in estatus_cands:
            if cand in row_dict:
                val = row_dict[cand]
                # Si es numérico, verificar que sea 1
                if isinstance(val, (int, float)):
                    if int(val) == 1:
                        return True
                # Si es string, verificar que contenga 'activo'
                elif isinstance(val, str):
                    if 'activ' in val.lower():
                        return True
        # Si no hay columna de estatus, asumir activo (por defecto)
        return True
    
    # Filtrar filas activas
    active_rows = [row for row in rows_list if is_active(row)]
    
    print(f"\n=== FILTRO DE ESTATUS ===")
    print(f"Total de filas del SP: {len(rows_list)}")
    print(f"Filas con estatus ACTIVO: {len(active_rows)}")
    print(f"Filas filtradas (inactivas): {len(rows_list) - len(active_rows)}")
    
    # Preparar mapeos desde las tablas de catálogo para resolver nombres a IDs
    tipos_db = db.query(Tipo_Ingreso).all()
    tipos_by_name = {str(t.Tipo_de_Ingreso).strip().lower(): t for t in tipos_db}

    grupos_db = db.query(Grupo_Edad).all()
    grupos_by_name = {str(g.Grupo_Edad).strip().lower(): g for g in grupos_db}

    sexos_db = db.query(Sexo).all()
    sexos_by_name = {str(getattr(s, 'Sexo', '')).strip().lower(): s for s in sexos_db}

    def get_first(rowd, candidates):
        """Obtener el primer valor no None de una lista de candidatos de columnas."""
        for c in candidates:
            if c in rowd and rowd[c] is not None:
                return rowd[c]
        return None

    def normalize_sexo(val):
        """Normalizar valor de sexo a 'M' o 'F'."""
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
    
    # Candidatos posibles de columnas en el row_dict
    tipo_id_cands = ['Id_Tipo_Ingreso', 'Id_TipoIngreso', 'IdTipoIngreso', 'Tipo_Id']
    tipo_name_cands = ['Tipo_de_Ingreso', 'TipoIngreso', 'Tipo_Ingreso', 'Tipo']

    grupo_id_cands = ['Id_Grupo_Edad', 'Id_GrupoEdad', 'IdGrupoEdad']
    grupo_name_cands = ['Grupo_Edad', 'GrupoEdad', 'Grupo']

    sexo_id_cands = ['Id_Sexo', 'IdSexo']
    sexo_name_cands = ['Sexo', 'Nombre_Sexo', 'Genero']

    matricula_cands = ['Matricula', 'Total', 'Cantidad', 'Numero', 'Valor']

    # Usar solo las filas activas
    for rd in active_rows:
        try:
            # Resolver tipo_id
            tipo_id = get_first(rd, tipo_id_cands)
            if tipo_id is None:
                tipo_name = get_first(rd, tipo_name_cands)
                if tipo_name:
                    tipo_obj = tipos_by_name.get(str(tipo_name).strip().lower())
                    tipo_id = tipo_obj.Id_Tipo_Ingreso if tipo_obj else None

            # Resolver grupo_id
            grupo_id = get_first(rd, grupo_id_cands)
            if grupo_id is None:
                grupo_name = get_first(rd, grupo_name_cands)
                if grupo_name:
                    grupo_obj = grupos_by_name.get(str(grupo_name).strip().lower())
                    grupo_id = grupo_obj.Id_Grupo_Edad if grupo_obj else None

            # Resolver sexo
            sexo_val = get_first(rd, sexo_id_cands) or get_first(rd, sexo_name_cands)
            sexo_norm = normalize_sexo(sexo_val)

            # Obtener valor de matrícula
            matricula_val = get_first(rd, matricula_cands)
            try:
                matricula_val = int(matricula_val) if matricula_val is not None else 0
            except Exception:
                try:
                    matricula_val = int(float(matricula_val)) if matricula_val is not None else 0
                except Exception:
                    matricula_val = 0

            if tipo_id is None or grupo_id is None or sexo_norm is None:
                # no podemos mapear esta fila a una celda; saltarla
                continue

            key = f"{int(tipo_id)}_{int(grupo_id)}_{sexo_norm}"
            # Si hay múltiples filas para la misma clave, sumamos
            datos_map[key] = datos_map.get(key, 0) + matricula_val
            
        except Exception as e:
            print(f"Error procesando fila del SP: {e}")
            continue

    return datos_map