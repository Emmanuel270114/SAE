from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.services.roles_service import get_all_roles, get_roles_for_user_group
from backend.services.unidad_services import get_all_units
from backend.services.usuario_service import register_usuario
from backend.services.nivel_service import get_all_niveles, get_niveles_by_unidad_academica
from backend.schemas.Usuario import UsuarioCreate, UsuarioResponse
from backend.core.templates import templates


router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def registro_view(request: Request, db: Session = Depends(get_db)):
    try:
        unidades_academicas = get_all_units(db)
        niveles = get_all_niveles(db)
        # Intentar leer el rol del usuario logueado desde cookie
        id_rol_cookie = request.cookies.get("id_rol")
        if id_rol_cookie and str(id_rol_cookie).isdigit():
            roles = get_roles_for_user_group(db, int(id_rol_cookie))
        else:
            # Fallback: mostrar todos los roles si no hay sesión
            roles = get_all_roles(db)
        return templates.TemplateResponse(
            "registro.html",
            {"request": request, "unidades_academicas": unidades_academicas, "roles": roles, "niveles": niveles},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()

@router.post("/", response_model=UsuarioResponse)
async def register_user_endpoint(user: UsuarioCreate, db: Session = Depends(get_db)):
    try:
        return register_usuario(db, user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
# Endpoint para obtener niveles por UA
@router.get("/niveles-por-ua/{id_unidad_academica}", response_class=JSONResponse)
async def niveles_por_ua(id_unidad_academica: int, db: Session = Depends(get_db)):
    try:
        niveles = get_niveles_by_unidad_academica(db, id_unidad_academica)
        return [n.model_dump() for n in niveles]
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})