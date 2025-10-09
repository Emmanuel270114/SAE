from backend.database.models.Bitacora import Bitacora
from datetime import datetime
from sqlalchemy.orm import Session

def registrar_bitacora(
    db: Session,
    id_usuario: int,
    id_modulo: int,
    id_periodo: int,
    accion: str,
    host: str,
    fecha: datetime = None
):
    bitacora = Bitacora(
        Id_Usuario=id_usuario,
        Id_Modulo=id_modulo,
        Id_Periodo=id_periodo,
        Acciones=accion,
        Host=host,
        Fecha=fecha or datetime.now()
    )
    db.add(bitacora)
    db.commit()
    db.refresh(bitacora)
    return bitacora

def log_accion(db: Session, id_usuario: int, accion: str, host: str):
    """Función simplificada para registrar acciones de seguridad"""
    try:
        registrar_bitacora(
            db=db,
            id_usuario=id_usuario,
            id_modulo=1,  # Módulo de seguridad/autenticación
            id_periodo=1,  # Periodo por defecto
            accion=accion,
            host=host  # Host de donde se realizó la acción
        )
    except Exception as e:
        print(f"Error registrando en bitácora: {e}")
        # No lanzar excepción para no interrumpir el flujo principal