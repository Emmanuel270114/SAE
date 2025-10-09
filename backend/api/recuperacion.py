from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.core.templates import templates
from backend.services.usuario_service import get_username_by_email, reset_password, change_password
from backend.services.bitacora_service import registrar_bitacora
from backend.services.usuario_service import is_super_admin

router = APIRouter(prefix="/recuperacion", tags=["recuperacion"])

@router.get("/usuario", response_class=HTMLResponse)
async def recuperar_usuario_view(request: Request):
    return templates.TemplateResponse("recuperar_usuario.html", {"request": request})

@router.post("/usuario", response_class=JSONResponse)
async def recuperar_usuario(email: str = Form(...), db: Session = Depends(get_db)):
    try:
        username = get_username_by_email(db, email)
        # Respuesta genérica si no existe
        if not username:
            return {"mensaje": "Si el correo existe, el usuario ha sido mostrado.", "usuario": None}
        return {"mensaje": "Usuario encontrado.", "usuario": username}
    finally:
        db.close()

@router.get("/password", response_class=HTMLResponse)
async def recuperar_password_view(request: Request):
    return templates.TemplateResponse("recuperar_password.html", {"request": request})

@router.post("/password", response_class=JSONResponse)
async def recuperar_password(username: str = Form(...), email: str = Form(...), request: Request = None, db: Session = Depends(get_db)):
    # Pasar el objeto request directamente a la función
    ok = reset_password(db, username, email, request)
    if ok:
        # bitácora adicional opcional para el endpoint
        try:
            # Capturar hostname de la misma forma
            import socket
            if request:
                xff = request.headers.get("x-forwarded-for") or ""
                client_ip = (xff.split(",")[0].strip() if xff else (request.client.host if request.client else ""))
                try:
                    host = socket.gethostbyaddr(client_ip)[0] if client_ip else ""
                except Exception:
                    host = client_ip
            else:
                host = "sistema"
            registrar_bitacora(db, id_usuario=0, id_modulo=1, id_periodo=9, accion=f"Reset password solicitado para usuario {username}", host=host)
        except Exception:
            pass
        return {"mensaje": "Si los datos son correctos, se envió una nueva contraseña al correo registrado."}
    return JSONResponse(status_code=400, content={"mensaje": "No se pudo completar la operación."})

@router.get("/cambiar", response_class=HTMLResponse)
async def cambiar_password_view(request: Request):
    return templates.TemplateResponse("cambiar_password.html", {"request": request})

@router.post("/cambiar", response_class=JSONResponse)
async def cambiar_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    new_password2: str = Form(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    if new_password != new_password2:
        return JSONResponse(status_code=400, content={"mensaje": "Las contraseñas nuevas no coinciden."})
    # Usuario logueado
    id_usuario = request.cookies.get("id_usuario") if request else None
    try:
        id_usuario_int = int(id_usuario) if id_usuario else 0
    except (TypeError, ValueError):
        id_usuario_int = 0
    if id_usuario_int <= 0:
        return JSONResponse(status_code=401, content={"mensaje": "Sesión no válida."})
    
    # Pasar el objeto request directamente a la función
    ok = change_password(db, id_usuario_int, current_password, new_password, request)
    if ok:
        try:
            # Capturar hostname de la misma forma
            import socket
            if request:
                xff = request.headers.get("x-forwarded-for") or ""
                client_ip = (xff.split(",")[0].strip() if xff else (request.client.host if request.client else ""))
                try:
                    host = socket.gethostbyaddr(client_ip)[0] if client_ip else ""
                except Exception:
                    host = client_ip
            else:
                host = "sistema"
            registrar_bitacora(db, id_usuario=id_usuario_int, id_modulo=1, id_periodo=9, accion="Cambio de contraseña exitoso", host=host)
        except Exception:
            pass
        return {"mensaje": "Contraseña actualizada."}
    return JSONResponse(status_code=400, content={"mensaje": "Credenciales inválidas."})
