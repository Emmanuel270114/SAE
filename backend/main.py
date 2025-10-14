#backend.main.py
from backend.api import registro
from backend.api import login
from backend.api import index
from backend.api import usuarios
from backend.api import mod_principal
from backend.api import unidad_academica
from backend.api import programas
from backend.api import matricula_sp
from backend.api import recuperacion
from backend.api.catalogos import domicilios
from backend.core.templates import static

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI()
app.mount("/static", static)
app.include_router(registro.router, prefix="/registro")
app.include_router(login.router , prefix="/login")
app.include_router(index.router , prefix="/index")
app.include_router(usuarios.router , prefix="/usuarios")
app.include_router(mod_principal.router , prefix="/mod_principal")
app.include_router(unidad_academica.router , prefix="/unidad-academica")
app.include_router(programas.router , prefix="/programas")
app.include_router(matricula_sp.router , prefix="/matricula")
app.include_router(domicilios.router)
app.include_router(recuperacion.router)

@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/index")