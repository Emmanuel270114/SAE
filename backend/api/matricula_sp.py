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
        "grupos_edad": grupos_edad
    })


@router.post("/obtener_datos_existentes_sp")
async def obtener_datos_existentes_sp(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Endpoint para obtener datos existentes de matrícula usando el SP.
    Usa las cookies del usuario para obtener UA, Nivel y Periodo automáticamente.
    """
    try:
        data = await request.json()
        
        # Obtener parámetros del JSON
        periodo = data.get('periodo')
        programa = data.get('programa')
        modalidad = data.get('modalidad')
        semestre = data.get('semestre')
        
        # Obtener datos del usuario desde cookies para usar en el SP
        id_unidad_academica = int(request.cookies.get("id_unidad_academica", 0))
        id_nivel = int(request.cookies.get("id_nivel", 0))
        
        # Obtener Sigla de la UA y Nivel para el SP
        unidad_sigla = db.execute(text("SELECT Sigla FROM Cat_Unidad_Academica WHERE Id_Unidad_Academica = :id"), {'id': id_unidad_academica}).scalar()
        nivel_nombre = db.execute(text("SELECT Nivel FROM Cat_Nivel WHERE Id_Nivel = :id"), {'id': id_nivel}).scalar()
        periodo_nombre = db.execute(text("SELECT Periodo FROM Cat_Periodo WHERE Id_Periodo = :id"), {'id': periodo}).scalar()
        
        if not unidad_sigla or not nivel_nombre or not periodo_nombre:
            return {"error": "No se pudieron obtener los datos del usuario"}
        
        # Ejecutar el SP para obtener datos existentes
        sql = text("EXEC SP_Consulta_Matricula_Unidad_Academica :unidad, :periodo, :nivel")
        result = db.execute(sql, {'unidad': unidad_sigla, 'periodo': periodo_nombre, 'nivel': nivel_nombre})
        rows = [dict(r) for r in result.fetchall()]
        
        # Filtrar los resultados por los filtros específicos del usuario
        datos_filtrados = {}
        
        for row in rows:
            # Verificar si la fila coincide con los filtros
            if programa:
                programa_nombre = db.execute(text("SELECT Nombre_Programa FROM Cat_Programas WHERE Id_Programa = :id"), {'id': programa}).scalar()
                if row.get('Nombre_Programa') != programa_nombre:
                    continue
            
            if modalidad:
                modalidad_nombre = db.execute(text("SELECT Modalidad FROM Cat_Modalidad WHERE Id_Modalidad = :id"), {'id': modalidad}).scalar()
                if row.get('Modalidad') != modalidad_nombre:
                    continue
                    
            if semestre:
                semestre_nombre = db.execute(text("SELECT Semestre FROM Cat_Semestre WHERE Id_Semestre = :id"), {'id': semestre}).scalar()
                if row.get('Semestre') != semestre_nombre:
                    continue
            
            # Obtener Id_Grupo_Edad
            id_grupo_edad = db.execute(text("SELECT Id_Grupo_Edad FROM Cat_Grupo_Edad WHERE Grupo_Edad = :g"), {'g': row.get('Grupo_Edad')}).scalar()
            
            if id_grupo_edad not in datos_filtrados:
                datos_filtrados[id_grupo_edad] = {}
            
            # Mapear los datos al formato esperado por el frontend
            tipo_ingreso = row.get('Tipo_de_Ingreso', '')
            sexo = row.get('Sexo', '')
            turno = row.get('Turno', '')
            matricula = row.get('Matricula', 0)
            
            # Determinar el campo según tipo/sexo/turno
            campo = ""
            if 'nuevo' in tipo_ingreso.lower():
                if 'hom' in sexo.lower():
                    if 'matutino' in turno.lower():
                        campo = 'nuevo_hombres_mat'
                    elif 'vespertino' in turno.lower():
                        campo = 'nuevo_hombres_vesp'
                    else:
                        campo = 'nuevo_hombres_mixto'
                else:  # mujeres
                    if 'matutino' in turno.lower():
                        campo = 'nuevo_mujeres_mat'
                    elif 'vespertino' in turno.lower():
                        campo = 'nuevo_mujeres_vesp'
                    else:
                        campo = 'nuevo_mujeres_mixto'
            else:  # repetidores
                if 'hom' in sexo.lower():
                    if 'matutino' in turno.lower():
                        campo = 'rep_hombres_mat'
                    elif 'vespertino' in turno.lower():
                        campo = 'rep_hombres_vesp'
                    else:
                        campo = 'rep_hombres_mixto'
                else:  # mujeres
                    if 'matutino' in turno.lower():
                        campo = 'rep_mujeres_mat'
                    elif 'vespertino' in turno.lower():
                        campo = 'rep_mujeres_vesp'
                    else:
                        campo = 'rep_mujeres_mixto'
            
            if campo:
                datos_filtrados[id_grupo_edad][campo] = matricula
        
        return {"datos": datos_filtrados}
        
    except Exception as e:
        return {"error": f"Error al obtener datos existentes: {str(e)}"}


@router.get('/semestres_map')
async def semestres_map_sp(db: Session = Depends(get_db)):
    """Endpoint para obtener el mapeo de semestres (Id -> Nombre)"""
    try:
        semestres = db.query(Semestre).all()
        semestres_map = {s.Id_Semestre: s.Semestre for s in semestres}
        return semestres_map
    except Exception as e:
        return {"error": str(e)}

