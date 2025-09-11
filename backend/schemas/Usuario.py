from pydantic import BaseModel, EmailStr

class UsuarioBase(BaseModel):
    Usuario: str
    Email: EmailStr

class UsuarioCreate(UsuarioBase):
    Id_Unidad_Academica: int
    Id_Rol: int
    Contraseña: str
    Id_Estatus: int
    Nombre: str
    Paterno: str
    Materno: str

class UsuarioResponse(UsuarioBase):
    Id_Usuario: int

    model_config = {
        "from_attributes": True
    }
