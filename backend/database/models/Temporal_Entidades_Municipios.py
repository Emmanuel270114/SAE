from ..db_base import Base
from sqlalchemy import Integer, String, DateTime,func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

class temporal_Entidades_Municipios(Base):
    __tablename__ = 'temporal_entidades_municipios'

    IdEntidadMunicipio: Mapped[str] = mapped_column(String(50), primary_key=True, autoincrement=True)
    IdEntidad: Mapped[str] = mapped_column(String(50), nullable=False)
    NombreEntidad: Mapped[str] = mapped_column(String(100), nullable=False)
    AbreviaturaEntidad: Mapped[str] = mapped_column(String(10), nullable=False)
    IdMunicipio: Mapped[str] = mapped_column(String(50), nullable=False)
    NombreMunicipio: Mapped[str] = mapped_column(String(100), nullable=False)
    IdLocalidad: Mapped[str] = mapped_column(String(50), nullable=True)
    NombreLocalidad: Mapped[str] = mapped_column(String(200), nullable=True)
    IdPais: Mapped[int] = mapped_column(Integer, nullable=False)