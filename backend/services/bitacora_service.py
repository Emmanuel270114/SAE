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