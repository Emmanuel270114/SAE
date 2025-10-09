from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

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
import json
from backend.database.models.CatGrupoEdad import CatGrupoEdad as Grupo_Edad
from backend.database.models.CatTipoIngreso import TipoIngreso as Tipo_Ingreso
from backend.database.models.CatSexo import CatSexo as Sexo

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def matricula_list_view(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = 200,
):
    """
    Vista básica de solo lectura que lista registros de la tabla Matricula
    filtrados por la Unidad Académica del usuario logueado.
    """
    # Obtener datos del usuario logueado desde las cookies
    id_unidad_academica = int(request.cookies.get("id_unidad_academica", 0))
    nombre_usuario = request.cookies.get("nombre_usuario", "")
    apellidoP_usuario = request.cookies.get("apellidoP_usuario", "")
    apellidoM_usuario = request.cookies.get("apellidoM_usuario", "")
    nombre_completo = " ".join(filter(None, [nombre_usuario, apellidoP_usuario, apellidoM_usuario]))

    # Realizar joins para obtener nombres/descripciones en lugar de IDs
    items = (
        db.query(
            Periodo.Periodo.label("Periodo"),
            Unidad_Academica.Nombre.label("Unidad_Academica"),
            Programas.Nombre_Programa.label("Programa"),
            Rama.Nombre_Rama.label("Rama"),
            Nivel.Nivel.label("Nivel"),
            Modalidad.Modalidad.label("Modalidad"),
            Turno.Turno.label("Turno"),
            Semestre.Semestre.label("Semestre"),
            Grupo_Edad.Grupo_Edad.label("Grupo_Edad"),
            Tipo_Ingreso.Tipo_de_Ingreso.label("Tipo_Ingreso"),
            Sexo.Sexo.label("Sexo"),
            Matricula.Matricula
        )
        .join(Periodo, Matricula.Id_Periodo == Periodo.Id_Periodo)
        .join(Unidad_Academica, Matricula.Id_Unidad_Academica == Unidad_Academica.Id_Unidad_Academica)
        .join(Programas, Matricula.Id_Programa == Programas.Id_Programa)
        .join(Rama, Matricula.Id_Rama == Rama.Id_Rama)
        .join(Nivel, Matricula.Id_Nivel == Nivel.Id_Nivel)
        .join(Modalidad, Matricula.Id_Modalidad == Modalidad.Id_Modalidad)
        .join(Turno, Matricula.Id_Turno == Turno.Id_Turno)
        .join(Semestre, Matricula.Id_Semestre == Semestre.Id_Semestre)
        .join(Grupo_Edad, Matricula.Id_Grupo_Edad == Grupo_Edad.Id_Grupo_Edad)
        .join(Tipo_Ingreso, Matricula.Id_Tipo_Ingreso == Tipo_Ingreso.Id_Tipo_Ingreso)
        .filter(Matricula.Id_Unidad_Academica == id_unidad_academica)
        .order_by(Periodo.Periodo.desc())
        .limit(limit)
        .all()
    )
    print(f"DEBUG: Número de elementos obtenidos: {len(items)}")

    return templates.TemplateResponse(
        "matricula.html",
        {
            "request": request,
            "items": items,
            "nombre_usuario": nombre_completo,
            "limit": limit,
        },
    )


@router.put("/update_matricula/{id}", response_class=HTMLResponse)
async def update_matricula(
    id: int,
    nueva_matricula: int,
    db: Session = Depends(get_db)
):
    """
    Actualiza el valor de matrícula para un registro específico.
    """
    try:
        db.query(Matricula).filter(Matricula.Id == id).update({"Matricula": nueva_matricula})
        db.commit()
        return {"mensaje": "Matrícula actualizada correctamente."}
    except Exception as e:
        db.rollback()
        return {"error": f"Error al actualizar matrícula: {str(e)}"}


@router.post("/guardar_captura")
async def guardar_captura_matricula(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Endpoint para guardar los datos de captura de matrícula.
    """
    try:
        # Obtener datos del JSON enviado desde el frontend
        data = await request.json()
        
        # Obtener datos del usuario logueado desde las cookies
        id_unidad_academica = int(request.cookies.get("id_unidad_academica", 0))
        id_usuario = int(request.cookies.get("id_usuario", 0))
        id_nivel = int(request.cookies.get("id_nivel", 0))
        id_rol = int(request.cookies.get("id_rol", 0))
        nombre_rol = request.cookies.get("nombre_rol", "")
        nombre_usuario = request.cookies.get("nombre_usuario", "")
        
        # Validar que el usuario tenga permisos y el rol correcto
        if not id_unidad_academica or not id_usuario:
            return {"error": "Usuario no autenticado correctamente"}
        
        if nombre_rol.lower() != 'capturista':
            return {"error": "Acceso denegado: Solo los usuarios con rol 'Capturista' pueden realizar esta acción"}
        
        # Crear registros para cada combinación de turno, género y tipo
        registros_creados = 0
        
        # Procesar los datos por grupo de edad
        datos_por_grupo = data.get('datos_por_grupo', {})
        
        turnos = ['matutino', 'vespertino', 'mixto']
        tipos = [
            ('nuevo_hombres', 1, 1),  # nuevo ingreso, hombres, tipo_ingreso=1
            ('nuevo_mujeres', 2, 1),  # nuevo ingreso, mujeres, tipo_ingreso=1
            ('rep_hombres', 1, 2),    # repetidores, hombres, tipo_ingreso=2
            ('rep_mujeres', 2, 2)     # repetidoras, mujeres, tipo_ingreso=2
        ]
        
        # Procesar cada grupo de edad
        for grupo_edad_id, datos_grupo in datos_por_grupo.items():
            id_grupo_edad = int(grupo_edad_id)
            
            for turno_idx, turno_nombre in enumerate(['mat', 'vesp', 'mixto']):
                for tipo_key, id_sexo, id_tipo_ingreso in tipos:
                    campo = f"{tipo_key}_{turno_nombre}"
                    cantidad = int(datos_grupo.get(campo, 0))
                    
                    if cantidad > 0:
                        # Buscar IDs correspondientes
                        turno_id = turno_idx + 1  # Asumiendo que los IDs son 1, 2, 3
                        
                        nueva_matricula = Matricula(
                            Id_Periodo=int(data.get('periodo')),
                            Id_Unidad_Academica=id_unidad_academica,  # Usar la UA del usuario logueado
                            Id_Programa=int(data.get('programa')),
                            Id_Rama=1,  # Se puede obtener del programa o definir por defecto
                            Id_Nivel=id_nivel,  # Usar el nivel del usuario logueado
                            Id_Modalidad=int(data.get('modalidad', 1)),
                            Id_Turno=turno_id,
                            Id_Semestre=int(data.get('semestre')),
                            Id_Grupo_Edad=id_grupo_edad,  # Usar el grupo de edad específico
                            Id_Sexo=id_sexo,
                            Id_Tipo_Ingreso=id_tipo_ingreso,
                            Matricula=cantidad
                        )
                        db.add(nueva_matricula)
                        registros_creados += 1
            
            # Procesar grupos si hay datos
            for turno_idx, turno_nombre in enumerate(['mat', 'vesp', 'mixto']):
                campo_grupos = f"grupos_{turno_nombre}"
                cantidad_grupos = int(datos_grupo.get(campo_grupos, 0))
                
                if cantidad_grupos > 0:
                    # Crear registro para grupos (si se necesita una tabla separada)
                    # Por ahora solo lo registramos como un tipo especial
                    pass
        

        
        db.commit()
        return {"mensaje": f"Matrícula guardada correctamente. {registros_creados} registros creados."}
    except Exception as e:
        db.rollback()
        return {"error": f"Error al guardar matrícula: {str(e)}"}


@router.get("/captura_matricula", response_class=HTMLResponse)
async def captura_matricula_view(request: Request, db: Session = Depends(get_db)):
    """
    Endpoint para servir la página de captura de matrícula.
    Solo accesible para usuarios con rol 'Capturista'.
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

    return templates.TemplateResponse("captura_matricula.html", {
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


@router.post("/obtener_datos_existentes")
async def obtener_datos_existentes(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Endpoint para obtener datos existentes de matrícula para un conjunto específico de filtros.
    """
    try:
        data = await request.json()
        
        # Obtener datos del usuario logueado
        id_unidad_academica = int(request.cookies.get("id_unidad_academica", 0))
        id_nivel = int(request.cookies.get("id_nivel", 0))
        nombre_rol = request.cookies.get("nombre_rol", "")
        
        # Validar permisos
        if nombre_rol.lower() != 'capturista':
            return {"error": "Acceso denegado"}
        
        # Obtener filtros del request
        periodo = data.get('periodo')
        programa = data.get('programa')
        modalidad = data.get('modalidad')
        semestre = data.get('semestre')
        
        if not all([periodo, programa, modalidad, semestre]):
            return {"error": "Faltan parámetros requeridos"}
        
        # Buscar datos existentes
        matriculas_existentes = db.query(Matricula).filter(
            Matricula.Id_Periodo == periodo,
            Matricula.Id_Unidad_Academica == id_unidad_academica,
            Matricula.Id_Programa == programa,
            Matricula.Id_Nivel == id_nivel,
            Matricula.Id_Modalidad == modalidad,
            Matricula.Id_Semestre == semestre
        ).all()
        
        # Organizar datos por grupo de edad
        datos_existentes = {}
        for matricula in matriculas_existentes:
            grupo_edad_id = str(matricula.Id_Grupo_Edad)
            if grupo_edad_id not in datos_existentes:
                datos_existentes[grupo_edad_id] = {}
            
            # Crear clave para identificar el campo en el formulario
            turno = ['mat', 'vesp', 'mixto'][matricula.Id_Turno - 1]  # Convertir ID a nombre
            
            if matricula.Id_Tipo_Ingreso == 1:  # Nuevo ingreso
                if matricula.Id_Sexo == 1:  # Hombres
                    campo = f"nuevo_hombres_{turno}"
                else:  # Mujeres
                    campo = f"nuevo_mujeres_{turno}"
            else:  # Repetidores
                if matricula.Id_Sexo == 1:  # Hombres
                    campo = f"rep_hombres_{turno}"
                else:  # Mujeres
                    campo = f"rep_mujeres_{turno}"
            
            datos_existentes[grupo_edad_id][campo] = matricula.Matricula
        
        return {"datos": datos_existentes}
        
    except Exception as e:
        return {"error": f"Error al obtener datos existentes: {str(e)}"}


@router.get("/semestres_map")
async def semestres_map(
    db: Session = Depends(get_db)
):
    """
    Devuelve un mapeo simple Id_Semestre -> Semestre (texto) en JSON.
    """
    try:
        semestres = db.query(Semestre).all()
        sem_map = {s.Id_Semestre: s.Semestre for s in semestres}
        return sem_map
    except Exception as e:
        return {"error": str(e)}
