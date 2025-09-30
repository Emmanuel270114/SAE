# SAE

## Configuración de entorno (.env)

Crea un archivo `.env` en la raíz (basado en `.env.example`). Nunca lo subas al repositorio.

Variables soportadas:

```env
# Base de datos
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=1433
DB_NAME=
DB_DRIVER="ODBC Driver 17 for SQL Server"

# SMTP / Correo
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=tu_correo@ejemplo.com
SMTP_PASS=app_password_o_contraseña
SMTP_FROM=No-Reply <no-reply@ejemplo.com>
SMTP_SUBJECT_PREFIX=SAE
```

Si `SMTP_FROM` está vacío se utilizará `SMTP_USER` como remitente.

## Flujo de recuperación de acceso

Rutas incorporadas:

| Acción | Ruta | Método |
|--------|------|--------|
| Recuperar usuario | `/recuperacion/usuario` | GET/POST |
| Recuperar contraseña | `/recuperacion/password` | GET/POST |
| Cambiar contraseña | `/recuperacion/cambiar` | GET/POST |

Características de seguridad:
* No se revela si un email/usuario existe (respuesta genérica en reset).
* Contraseñas siempre hasheadas (bcrypt).
* Contraseña temporal aleatoria generada al recuperar.
* Registro en bitácora de eventos (reset/cambio de contraseña).

## Envío de correo

Se usa `smtplib` con SSL. Ajusta `SMTP_HOST` y `SMTP_PORT` según tu proveedor.

Para Gmail con 2FA activa, genera un *App Password* y úsalo en `SMTP_PASS`.

## Ejecución local

1. Crear entorno virtual.
2. Instalar dependencias: `pip install -r requirements.txt`.
3. Crear `.env` desde `.env.example`.
4. Ejecutar:

```bash
python -m uvicorn backend.main:app --reload
```

## Notas futuras

* Se puede agregar token de expiración para reset de contraseña.
* Se puede integrar un servicio de correo transaccional (SendGrid, Mailgun) fácilmente sustituyendo `send_email`.
