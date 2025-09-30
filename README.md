# SAE - Sistema de Administración Escolar

Sistema web desarrollado con FastAPI y Jinja2 para la gestión de usuarios académicos.

## Características
- Gestión de usuarios por roles
- Recuperación de contraseñas vía email
- Filtrado de programas por unidad académica
- Panel de administración

## Instalación
1. Clonar repositorio
2. Crear entorno virtual: `python -m venv venv`
3. Activar entorno: `venv\Scripts\activate`
4. Instalar dependencias: `pip install -r requirements.txt`
5. Configurar variables de entorno (.env)
6. Ejecutar: `python -m uvicorn backend.main:app --reload`

## Variables de entorno requeridas
Ver `.env.example` para la configuración completa.
