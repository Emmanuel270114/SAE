from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from backend.core.templates import templates
from backend.database.connection import get_db
from backend.services.usuario_service import (
    get_usuarios_by_unidad,
    get_usuario_by_id,
    update_usuario,
    set_usuario_estatus,
    get_usuarios_by_unidad_con_rol,
    get_all_usuarios_con_rol,
    get_unidad_academica_nombre,
    register_usuario,
    is_super_admin,
    has_admin_permissions
)
from backend.services.roles_service import get_all_roles, get_roles_for_user_group
from backend.services.bitacora_service import registrar_bitacora
from backend.services.unidad_services import get_all_units
from backend.services.nivel_service import get_all_niveles
from backend.schemas.Usuario import UsuarioCreate, UsuarioResponse
from sqlalchemy.orm import Session
import socket
from backend.utils.request import get_request_host

router = APIRouter()


# Vista unificada: registro y lista de usuarios
@router.get("/", response_class=HTMLResponse)
async def usuarios_view(
    request: Request,
    db: Session = Depends(get_db),
):
    # Datos del usuario logueado
    id_unidad_academica = int(request.cookies.get("id_unidad_academica", 1))
    id_rol = int(request.cookies.get("id_rol", 2))
    Rol = str(request.cookies.get("nombre_rol",""))
    nombre_usuario = request.cookies.get("nombre_usuario", "")
    apellidoP_usuario = request.cookies.get("apellidoP_usuario", "")
    apellidoM_usuario = request.cookies.get("apellidoM_usuario", "")
    nombre_completo = " ".join(filter(None, [nombre_usuario, apellidoP_usuario, apellidoM_usuario]))
    
    # Verificar si es super admin
    es_super_admin = is_super_admin(nombre_usuario, apellidoP_usuario, apellidoM_usuario)
    
    # Verificar si tiene permisos administrativos
    tiene_permisos_admin = has_admin_permissions(db, id_rol)
    
    # Obtener usuarios según privilegios
    if es_super_admin:
        usuarios_con_rol = get_all_usuarios_con_rol(db)
        nombre_ua = "Todas las Unidades Académicas"
    else:
        usuarios_con_rol = get_usuarios_by_unidad_con_rol(db, id_unidad_academica)
        # Filtrar para que no aparezca el superadmin 'admin admin admin'
        usuarios_con_rol = [u for u in usuarios_con_rol if not (
            getattr(u[0], 'Nombre', '').strip().lower() == 'admin' and
            getattr(u[0], 'Paterno', '').strip().lower() == 'admin' and
            getattr(u[0], 'Materno', '').strip().lower() == 'admin'
        )]
        nombre_ua = get_unidad_academica_nombre(db, id_unidad_academica)
    
    # Filtrar roles según el grupo del rol del usuario logueado
    try:
        roles = get_roles_for_user_group(db, id_rol)
    except Exception:
        roles = get_all_roles(db)
    unidades_academicas = get_all_units(db)
    niveles = get_all_niveles(db)
    return templates.TemplateResponse(
        "usuarios.html",
        {
            "request": request,
            "usuarios_con_rol": usuarios_con_rol,
            "id_rol": id_rol,
            "nombre_ua": nombre_ua,
            "nombre_usuario": nombre_completo,
            "roles": roles,
            "unidades_academicas": unidades_academicas,
            "niveles": niveles,
            "es_super_admin": es_super_admin,
            "tiene_permisos_admin": tiene_permisos_admin,
            "rol": Rol
        },
    )


# Endpoint para registrar usuario desde la misma página
@router.post("/registrar", response_class=JSONResponse)
async def registrar_usuario_view(
    request: Request,
    db: Session = Depends(get_db),
):
    data = await request.json()
    try:
        user = UsuarioCreate(**data)
        usuario_registrado = register_usuario(db, user)
        
        # Registro en la tabla Bitacora de la DB
        # Tomar el ID del usuario logueado desde la cookie
        id_usuario_log = request.cookies.get("id_usuario")
        try:
            id_usuario_log = int(id_usuario_log) if id_usuario_log is not None else 0
        except (TypeError, ValueError):
            id_usuario_log = 0
        if id_usuario_log > 0:
            try:
                id_modulo = 1  # Puedes ajustar el ID del módulo según tu catálogo
                id_periodo = 9  # Por ahora fijo como solicitaste
                accion = f"Registró nuevo usuario con ID {usuario_registrado.Id_Usuario}"

                # Obtener el hostname del cliente (reverse DNS). Si falla, usar IP.
                host = get_request_host(request)
                # Registrar en la bitácora
                registrar_bitacora(
                    db=db,
                    id_usuario=id_usuario_log,
                    id_modulo=id_modulo,
                    id_periodo=id_periodo,
                    accion=accion,
                    host=host
                )
                print(f"✅ Bitácora registrada: Usuario {id_usuario_log} registró usuario {usuario_registrado.Id_Usuario}")
            except Exception as bitacora_error:
                print(f"❌ Error al registrar en bitácora: {bitacora_error}")
                # No fallar el registro por error en bitácora
        
        return JSONResponse(content={"Id_Usuario": usuario_registrado.Id_Usuario})
    except Exception as e:
        msg = str(e)
        if "La persona ya está registrada" in msg:
            return JSONResponse(status_code=400, content={"detail": "La persona ya está registrada"})
        if "Email ya está registrado" in msg:
            return JSONResponse(status_code=400, content={"detail": "Email ya está registrado"})
        return JSONResponse(status_code=400, content={"detail": msg})

# Endpoint para editar usuario desde la misma página
@router.post("/editar/{id_usuario}", response_class=JSONResponse)
async def editar_usuario_ajax(
    id_usuario: int,
    request: Request,
    db: Session = Depends(get_db),
):
    # Validar superadmin
    nombre_usuario = request.cookies.get("nombre_usuario", "")
    apellidoP_usuario = request.cookies.get("apellidoP_usuario", "")
    apellidoM_usuario = request.cookies.get("apellidoM_usuario", "")
    if not is_super_admin(nombre_usuario, apellidoP_usuario, apellidoM_usuario):
        return JSONResponse(content={"mensaje": "No te puedes modificar a ti mismo."}, status_code=403)
    try:
        data = await request.json()
        update_usuario(
            db,
            id_usuario,
            data.get("Nombre"),
            data.get("Paterno"),
            data.get("Materno"),
            data.get("Email"),
            data.get("Id_Rol"),
            data.get("Usuario"),
            data.get("Id_Unidad_Academica"),
            data.get("Id_Nivel")
        )
        # Registro en la tabla Bitacora de la DB
        # Tomar el ID del usuario logueado desde la cookie (no el modificado)
        id_usuario_log = request.cookies.get("id_usuario")
        try:
            id_usuario_log = int(id_usuario_log) if id_usuario_log is not None else 0
        except (TypeError, ValueError):
            id_usuario_log = 0
        if id_usuario_log > 0:
            id_modulo = 1  # Puedes ajustar el ID del módulo según tu catálogo
            id_periodo = 9  # Por ahora fijo como solicitaste
            accion = f"Modificó usuario con ID {id_usuario}"

            # Obtener el hostname del cliente (reverse DNS). Si falla, usar IP.
            xff = request.headers.get("x-forwarded-for") or ""
            client_ip = (xff.split(",")[0].strip() if xff else (request.client.host if request.client else ""))
            try:
                # Obtener el hostname a partir de la IP
                host = socket.gethostbyaddr(client_ip)[0] if client_ip else ""
            except Exception:
                host = client_ip
            # Registrar en la bitácora
            registrar_bitacora(
                db=db,
                id_usuario=id_usuario_log,
                id_modulo=id_modulo,
                id_periodo=id_periodo,
                accion=accion,
                host=host
            )
        return JSONResponse(content={"mensaje": "Usuario actualizado correctamente."})
    except Exception as e:
        return JSONResponse(content={"mensaje": str(e)}, status_code=500)

# Baja lógica de usuario (Id_Estatus = 3)
@router.post("/eliminar/{id_usuario}", response_class=JSONResponse)
async def eliminar_usuario(
    id_usuario: int,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        u = set_usuario_estatus(db, id_usuario, 3)
        if not u:
            return JSONResponse(content={"mensaje": "Usuario no encontrado"}, status_code=404)

        # Bitácora: quién elimina a quién
        id_usuario_log = request.cookies.get("id_usuario")
        try:
            id_usuario_log = int(id_usuario_log) if id_usuario_log is not None else 0
        except (TypeError, ValueError):
            id_usuario_log = 0
        if id_usuario_log > 0:
            id_modulo = 1
            id_periodo = 9
            accion = f"Eliminó (baja lógica) usuario con ID {id_usuario}"
            host = get_request_host(request)
            registrar_bitacora(db=db, id_usuario=id_usuario_log, id_modulo=id_modulo, id_periodo=id_periodo, accion=accion, host=host)

        return JSONResponse(content={"mensaje": "Usuario dado de baja correctamente."})
    except Exception as e:
        return JSONResponse(content={"mensaje": str(e)}, status_code=500)
