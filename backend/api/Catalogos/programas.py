from sqlalchemy import text
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.core.templates import templates

router = APIRouter()

@router.get("/programas", response_class=HTMLResponse)
def programas_view(
    request: Request,
    UUsuario: str = "paco",
    HHost: str = "Test",
    PPeriodo: str = "2025-2026/1",
    db: Session = Depends(get_db)
):
    
    SSigla = str(request.cookies.get("sigla_unidad_academica", ""))
    Rol = str(request.cookies.get("nombre_rol",""))
    
    data = []
    try:
        connection = db.connection()
        cursor = connection.connection.cursor()

        cursor.execute("""
            EXEC dbo.SP_Consulta_Catalogo_Programas 
                @UUnidad_Academica = ?, 
                @UUsuario = ?, 
                @HHost = ?, 
                @PPeriodo = ?
        """, (SSigla, UUsuario, HHost, PPeriodo))

        # 🔁 Si el primer resultset está vacío (por otro EXEC), saltamos al siguiente
        while cursor.description is None and cursor.nextset():
            pass

        if cursor.description:
            columns = [col[0] for col in cursor.description]
            data = [dict(zip(columns, row)) for row in cursor.fetchall()]
        else:
            print("⚠️ El SP no devolvió resultados visibles")

        cursor.close()
    except Exception as e:
        print("Error al ejecutar SP_Consulta_Catalogo_Programas:", e)

    return templates.TemplateResponse(
        "catalogos/programas.html",
        {
            "request": request, 
            "programas": data,
            "rol": Rol
            }
    )
