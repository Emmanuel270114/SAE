#Este archivo contiene las funciones CRUD para el modelo Usuario.

from backend.database.models.Usuario import Usuario
from backend.schemas.Usuario import UsuarioCreate, UsuarioResponse

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from typing import Optional

############################__________________FUNCIONES CREATE____________________________############################
def create_usuario(db: Session, user_data: UsuarioCreate) -> Usuario:
    new_user = Usuario(**user_data.model_dump())
    db.add(new_user)
    try:
        db.commit()
        db.refresh(new_user)
    except IntegrityError as e:
        db.rollback()
        print("❌ Error exacto:", e.orig)
        raise
    return new_user

############################__________________FUNCIONES READ____________________________############################
def read_user_by_username(db: Session, username: str) -> Optional[Usuario]:
    stmt = select(Usuario).where(Usuario.Usuario == username, Usuario.Id_Estatus != 3)
    return db.execute(stmt).scalars().first()

def read_user_by_email(db: Session, email: str) -> Optional[Usuario]:
    stmt = select(Usuario).where(Usuario.Email == email, Usuario.Id_Estatus != 3)
    return db.execute(stmt).scalars().first()

def read_password_by_user(db: Session, username: str) -> Optional[str]:
    stmt = select(Usuario.Contrasena).where(Usuario.Usuario == username)
    result = db.execute(stmt).scalar_one_or_none()
    return result

def read_password_by_email(db: Session, email: str) -> Optional[str]:
    stmt = select(Usuario.Contrasena).where(Usuario.Email == email)
    result = db.execute(stmt).scalar_one_or_none()
    return result