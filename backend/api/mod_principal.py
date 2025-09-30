from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from backend.core.templates import templates

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def mod_principal_view(request: Request):
    nombre_usuario = request.cookies.get("nombre_usuario", "")
    apellidoP_usuario = request.cookies.get("apellidoP_usuario", "")
    apellidoM_usuario = request.cookies.get("apellidoM_usuario", "")
    nombre_completo = " ".join(filter(None, [nombre_usuario, apellidoP_usuario, apellidoM_usuario]))
    return templates.TemplateResponse("Mod_Principal.html", {"request": request, "nombre_usuario": nombre_completo})
