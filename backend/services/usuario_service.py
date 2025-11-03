from backend.crud.Usuario import (
    create_usuario,
    read_user_by_username,
    read_user_by_email,
    read_password_by_user,
    read_password_by_email,
    update_usuario as crud_update_usuario,
    set_usuario_estatus as crud_set_usuario_estatus,
    get_usuarios_by_unidad as crud_get_usuarios_by_unidad,
    get_usuario_by_id as crud_get_usuario_by_id,
)
from backend.services.bitacora_service import registrar_bitacora
from backend.database.models.Usuario import Usuario
from backend.utils.security import hash_password, generate_random_password
from backend.utils.request import get_request_host
from backend.utils.email import send_email, EmailSendError
from backend.schemas.Usuario import UsuarioCreate, UsuarioResponse, UsuarioLogin


from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, Dict

import bcrypt

class UserAlreadyExistsError(Exception):
    """Excepción lanzada cuando un usuario ya existe."""
    pass

def get_username_by_email(db: Session, email: str) -> str | None:
    user = read_user_by_email(db, email)
    return user.Usuario if user else None

# Funciones para manejo de contraseñas
def reset_password(db: Session, username: str, email: str, request = None) -> bool:
    """Genera una contraseña temporal y la envía al correo si username & email coinciden.
    Respuesta siempre booleana sin detallar causa para no filtrar existencia.
    """
    try:
        user = read_user_by_username(db, username)
        if not user or user.Email.lower() != email.lower():
            # Responder éxito falso pero sin detalle
            return False
        nueva = generate_random_password()
        user.Password = hash_password(nueva)
        from datetime import datetime, timezone
        user.Fecha_Modificacion = datetime.now(timezone.utc)
        db.commit()
        
        # Registrar en bitácora que se generó contraseña temporal
        try:
            from backend.services.bitacora_service import registrar_bitacora
            import socket
            
            id_modulo = 1  # Módulo de seguridad
            id_periodo = 7  # Periodo por defecto
            accion = f"Nueva contraseña temporal generada para {user.Usuario}"

            # Obtener el hostname del cliente (reverse DNS). Si falla, usar IP.
            host = get_request_host(request)
            
            # Registrar en la bitácora
            registrar_bitacora(
                db=db,
                id_usuario=user.Id_Usuario,
                id_modulo=id_modulo,
                id_periodo=id_periodo,
                accion=accion,
                host=host
            )
            print(f"✅ Bitácora registrada: Nueva contraseña temporal para usuario {user.Id_Usuario} desde host {host}")
        except Exception as bitacora_error:
            print(f"❌ Error al registrar en bitácora: {bitacora_error}")
            # No fallar el registro por error en bitácora
        # Enviar correo
        cuerpo = f"""
        <p>Hola {user.Nombre or ''},</p>
        <p>Se ha generado una nueva contraseña temporal para tu cuenta.</p>
        <p><strong>{nueva}</strong></p>
        <p>Por seguridad, cámbiela después de Iniciar Sesión.</p>
        <p>-- Sistema SAE</p>
        """
        try:
            send_email(user.Email, "Recuperación de contraseña", cuerpo)
        except EmailSendError:
            # Revertir si falla envío
            db.rollback()
            return False
        return True
    except Exception:
        db.rollback()
        return False

def change_password(db: Session, user_id: int, request, new_password: str) -> bool:
    """
    Cambiar la contraseña del usuario SIN requerir la contraseña actual.
    Solo necesita el ID del usuario y la nueva contraseña.
    """
    user = db.query(Usuario).filter(Usuario.Id_Usuario == user_id).first()
    if not user:
        return False
    
    # Actualizar directamente sin validar contraseña actual
    user.Password = hash_password(new_password)
    from datetime import datetime, timezone
    user.Fecha_Modificacion = datetime.now(timezone.utc)
    db.commit()
    
    # Registrar en bitácora que cambió a contraseña personal
    try:
        from backend.services.bitacora_service import registrar_bitacora
        import socket
        
        id_modulo = 1  # Módulo de seguridad
        id_periodo = 7  # Periodo por defecto
        accion = f"Usuario cambió su contraseña"

        # Obtener el hostname del cliente (reverse DNS). Si falla, usar IP.
        host = get_request_host(request)
        
        # Registrar en la bitácora
        registrar_bitacora(
            db=db,
            id_usuario=user_id,
            id_modulo=id_modulo,
            id_periodo=id_periodo,
            accion=accion,
            host=host
        )
        print(f"✅ Bitácora registrada: Cambio de contraseña para usuario {user_id} desde host {host}")
    except Exception as bitacora_error:
        print(f"❌ Error al registrar en bitácora: {bitacora_error}")
        # No fallar el cambio de contraseña por error en bitácora
    
    return True

#Funciones read
def user_already_exists(db: Session, username: str, email: str) -> bool:
    """Verifica si el usuario ya existe por nombre de usuario o email."""
    return read_user_by_username(db, username) is not None \
        or read_user_by_email(db, email) is not None

# Validar usuario por username/email y password
def validacion_usuario(db: Session, username_email: Optional[str], password: Optional[str]) -> bool:
    try:
        if username_email is not None and password is not None:
            user = read_user_by_email(db, username_email)
            if user is None:
                user = read_user_by_username(db, username_email)
            if user is None:
                return False  
            stored_password: Optional[str] = user.Password
            if stored_password is None:
                return False
            if bcrypt.checkpw(password.encode("utf-8"), stored_password.encode("utf-8")):
                return True
            else:
                return False
        else:
            return False
    except Exception as e:
        print(f"Error en validacion_usuario: {e}")
        return False

# Validar usuario usando un objeto UsuarioLogin
def validacion_usuario_2(db: Session, userlogin: Optional[UsuarioLogin]) -> bool:
    """ Validar usuario usando un objeto UsuarioLogin """
    try:
        if userlogin is not None:
            user = read_user_by_email(db, userlogin.Usuario)
            if user is None:
                user = read_user_by_username(db, userlogin.Email)
            if user is None:
                return False
            stored_password: Optional[str] = user.Password
            if stored_password is None:
                return False
            if bcrypt.checkpw(userlogin.Password.encode("utf-8"), stored_password.encode("utf-8")):
                return True
            else:
                return False
        else:
            return False
    except Exception as e:        
        print(f"Error en validacion_usuario: {e}")
        return False
            
#Funciones create
# Registrar un nuevo usuario
def register_usuario(db: Session, user_dict: UsuarioCreate) -> UsuarioResponse:
    try:

        # 1) Validar nombre completo (Nombre, Paterno, Materno) para evitar duplicidad de persona (solo activos)
        persona_existente = (
            db.query(Usuario)
            .filter(
                Usuario.Nombre == user_dict.Nombre,
                Usuario.Paterno == user_dict.Paterno,
                Usuario.Materno == user_dict.Materno,
                Usuario.Id_Estatus != 3
            )
            .first()
        )
        if persona_existente:
            raise ValueError("La persona ya está registrada")

        # 2) Validar usuario único (campo Usuario)
        usuario_existente = db.query(Usuario).filter(Usuario.Usuario == user_dict.Usuario).first()
        if usuario_existente:
            if usuario_existente.Id_Estatus != 3:
                raise ValueError("El nombre de usuario ya está registrado y activo.")
            # Si el usuario existe pero está dado de baja (estatus 3), permitir registro

        # 3) Validar email (usuario se deriva del email)
        if read_user_by_email(db, user_dict.Email):
            raise ValueError("Email ya está registrado")

        user_dict.Password = hash_password(user_dict.Password)
        user = create_usuario(db, user_dict)
        return UsuarioResponse.model_validate(user)

    except IntegrityError as e:
        # Respaldo por condiciones de carrera: mapear todo a email (política solicitada)
        msg = str(e.orig).lower()
        if ("email" in msg) or ("correo" in msg) or ("usuario" in msg):
            raise ValueError("Email ya está registrado")
        raise
    except Exception as e:
        print(f"Error en usuario_services: {e}")
        raise
    finally:
        db.close()

# Obtener todos los usuarios de una Unidad Académica
def get_usuarios_by_unidad(db: Session, id_unidad_academica: int):
    return crud_get_usuarios_by_unidad(db, id_unidad_academica)

# Obtener un usuario por su ID
def get_usuario_by_id(db: Session, id_usuario: int):
    return crud_get_usuario_by_id(db, id_usuario)

# Actualizar un usuario
def update_usuario(
    db: Session,
    id_usuario: int,
    Nombre: str,
    Paterno: str,
    Materno: str,
    Email: str,
    Id_Rol: int,
    Usuario: Optional[str] = None,
    Id_Unidad_Academica: Optional[int] = None,
    Id_Nivel: Optional[int] = None,
):
    return crud_update_usuario(
        db,
        id_usuario,
        Nombre,
        Paterno,
        Materno,
        Email,
        Id_Rol,
        UsuarioStr=Usuario,
        Id_Unidad_Academica=Id_Unidad_Academica,
        Id_Nivel=Id_Nivel,
    )

# Cambiar estatus de un usuario (baja lógica)
def set_usuario_estatus(db: Session, id_usuario: int, id_estatus: int):
    return crud_set_usuario_estatus(db, id_usuario, id_estatus)

# Obtener todos los roles
def get_all_roles(db: Session):
    from backend.database.models.CatRoles import CatRoles
    return db.query(CatRoles).all()

# Obtener usuarios por unidad académica junto con el nombre del rol
def get_usuarios_by_unidad_con_rol(db: Session, id_unidad_academica: int):
    from backend.database.models.Usuario import Usuario
    from backend.database.models.CatRoles import CatRoles
    from backend.database.models.CatUnidadAcademica import CatUnidadAcademica
    return (
        db.query(Usuario, CatRoles.Rol.label("NombreRol"), CatUnidadAcademica.Sigla.label("SiglaUA"))
        .join(CatRoles, Usuario.Id_Rol == CatRoles.Id_Rol)
        .join(CatUnidadAcademica, Usuario.Id_Unidad_Academica == CatUnidadAcademica.Id_Unidad_Academica)
        .filter(
            Usuario.Id_Unidad_Academica == id_unidad_academica,
            Usuario.Id_Estatus != 3
        )
        .all()
    )

# Obtener el nombre de la Unidad Académica por su id
def get_unidad_academica_nombre(db: Session, id_unidad_academica: int) -> str:
    from backend.crud.CatUnidadAcademica import read_unidad_by_id
    ua = read_unidad_by_id(db, id_unidad_academica)
    return ua.Nombre if ua else "-"

# Verificar si un usuario es super admin (nombre completo "admin admin admin")
def is_super_admin(nombre: str, paterno: str, materno: str) -> bool:
    return (nombre.lower() == "admin" and 
            paterno.lower() == "admin" and 
            materno.lower() == "admin")

# Función para determinar si un rol tiene permisos administrativos
def has_admin_permissions(db: Session, id_rol: int) -> bool:
    """
    Determina si un rol tiene permisos administrativos basándose en el nombre del rol.
    Roles con permisos: Titular, Jefe/a de División, Jefe/a de Departamento, CEGET
    """
    from backend.database.models.CatRoles import CatRoles
    
    try:
        rol = db.query(CatRoles).filter(CatRoles.Id_Rol == id_rol).first()
        if not rol:
            return False
        
        # Roles con permisos administrativos (normalizar a minúsculas para comparación)
        rol_nombre = rol.Rol.lower()
        roles_admin = [
            'administrador',
            'titular', 
            'jefe/a de división',
            'jefe/a de departamento',
            'ceget'
        ]
        
        return any(admin_role in rol_nombre for admin_role in roles_admin)
    except Exception:
        return False

# Obtener TODOS los usuarios con rol (para super admin)
def get_all_usuarios_con_rol(db: Session):
    from backend.database.models.Usuario import Usuario
    from backend.database.models.CatRoles import CatRoles
    from backend.database.models.CatUnidadAcademica import CatUnidadAcademica
    return (
        db.query(Usuario, CatRoles.Rol.label("NombreRol"), CatUnidadAcademica.Sigla.label("SiglaUA"))
        .join(CatRoles, Usuario.Id_Rol == CatRoles.Id_Rol)
        .join(CatUnidadAcademica, Usuario.Id_Unidad_Academica == CatUnidadAcademica.Id_Unidad_Academica)
        .filter(Usuario.Id_Estatus != 3)
        .all()
    )

# Detectar si el usuario tiene contraseña temporal (basado en bitácora)
def has_temporary_password(db: Session, user_id: int) -> bool:
    """
    Detecta si el usuario tiene una contraseña temporal activa.
    Verifica si hay un reset reciente sin cambio posterior a contraseña personal.
    """
    try:
        from backend.database.models.Bitacora import Bitacora
        from datetime import datetime, timedelta
        
        # Buscar en las últimas 48 horas
        hace_48h = datetime.now() - timedelta(hours=48)
        
        # Buscar último evento de reset de contraseña temporal
        ultimo_reset = db.query(Bitacora).filter(
            Bitacora.Id_Usuario == user_id,
            Bitacora.Acciones.contains('Nueva contraseña temporal generada'),
            Bitacora.Fecha >= hace_48h
        ).order_by(Bitacora.Fecha.desc()).first()
        
        print(f"DEBUG: Usuario {user_id} - Último reset encontrado: {ultimo_reset is not None}")
        if not ultimo_reset:
            return False
        
        # Verificar si después del reset hubo un cambio de contraseña
        # Buscamos cualquiera de estos mensajes:
        # - "Usuario cambió de contraseña temporal a personal" (mensaje antiguo)
        # - "Usuario cambió su contraseña" (mensaje nuevo)
        # - "Cambio de contraseña exitoso" (mensaje del endpoint)
        from sqlalchemy import or_
        cambio_personal = db.query(Bitacora).filter(
            Bitacora.Id_Usuario == user_id,
            Bitacora.Fecha > ultimo_reset.Fecha,
            or_(
                Bitacora.Acciones.contains('Usuario cambió de contraseña temporal a personal'),
                Bitacora.Acciones.contains('Usuario cambió su contraseña'),
                Bitacora.Acciones.contains('Cambio de contraseña exitoso')
            )
        ).first()
        
        print(f"DEBUG: Usuario {user_id} - Cambio personal después de reset: {cambio_personal is not None}")
        if cambio_personal:
            print(f"DEBUG: Usuario {user_id} - Acción encontrada: {cambio_personal.Acciones}")
        
        # Si no hay cambio personal después del reset, aún tiene contraseña temporal
        result = cambio_personal is None
        print(f"DEBUG: Usuario {user_id} - Resultado final: {result}")
        return result
        
    except Exception as e:
        # Si hay error (ej: tabla bitácora no existe), asumir que no tiene contraseña temporal
        print(f"Error detectando contraseña temporal: {e}")
        return False
