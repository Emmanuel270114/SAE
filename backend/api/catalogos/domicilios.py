from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from backend.core.templates import templates


router = APIRouter()

@router.get("/domicilios", response_class=HTMLResponse)
async def domicilios_view(request: Request):
    return templates.TemplateResponse("catalogos/domicilios.html", {"request": request})
