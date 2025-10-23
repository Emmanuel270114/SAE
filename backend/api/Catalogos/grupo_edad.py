from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.core.templates import templates

from backend.database.models.CatGrupoEdad import CatGrupoEdad




router = APIRouter()

@router.get("/grupo_edad", response_class=HTMLResponse)
async def domicilios_view(request: Request, db: Session = Depends(get_db)):

    # Obtener datos del usuario logueado desde las cookies
    id_unidad_academica = int(request.cookies.get("id_unidad_academica", 1))
    id_rol = int(request.cookies.get("id_rol", 2))
    nombre_usuario = request.cookies.get("nombre_usuario", "")
    apellidoP_usuario = request.cookies.get("apellidoP_usuario", "")
    apellidoM_usuario = request.cookies.get("apellidoM_usuario", "")
    
    # Verificar si es super admin
    es_super_admin = (nombre_usuario.strip().lower() == 'admin' and
                     apellidoP_usuario.strip().lower() == 'admin' and
                     apellidoM_usuario.strip().lower() == 'admin')
    
    #todos_dom = db.query(CatDomicilios).all()
    #for dom in todos_dom:
        #a = db.query(CatUnidadAcademica).filter_by(Id_Unidad_Academica=dom.Id_Unidad_Academica).first()
        #unidada = a.__dict__['Sigla']
        #print(unidada)
        #a = db.query(CatUnidadAcademica).filter_by(Id_Unidad_Academica=dom.Id_Unidad_Academica).first()
        #unidada = a.__dict__['Sigla']
        #print(unidada)
    
    #cif es_super_admin:
    todos_gde = db.query(CatGrupoEdad).all()
    
    for grup in todos_gde:
        print(grup.__dict__)
    """
    
    
    domicilios = [
        {
    
            "ua": d.Id_Unidad_Academica,
            "municipio": d.Id_Entidad_Municipio,
            "calle": d.Calle,
            "numero": d.Numero,
            "colonia": d.Colonia,
            "cp": d.CP

            

        }
        for d in todos_gde
    ]
    for dom in domicilios:
        print(dom)
    """
    return templates.TemplateResponse(
        "catalogos/grupo_edad.html", 
        {
            "request": request,
            "es_super_admin": es_super_admin,
            "grupo_edad": 1
        }
    )