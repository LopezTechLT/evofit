# EVOFIT by Lopez Tech

Sistema inteligente de administración y seguimiento para gimnasios.

## Características

- Registro y gestión de clientes
- Control de membresías
- Sistema de pagos
- Rutinas personalizadas
- Seguimiento físico con gráficas
- Control de ingreso con QR
- Panel administrador
- Modo entrenador

## Instalación

1. Clona el repositorio
2. Crea un entorno virtual: `python -m venv venv`
3. Activa el entorno: `venv\Scripts\activate`
4. Instala dependencias: `pip install -r requirements.txt`
5. Configura la base de datos en `.env`
6. Ejecuta: `python run.py`

## Uso

- Registra un usuario administrador
- Agrega clientes
- Gestiona membresías y pagos
- Crea rutinas
- Monitorea progreso

## Tecnologías

- Backend: Flask, SQLAlchemy, SQLite/MySQL (según `DATABASE_URL`)
- Frontend: HTML, CSS, Bootstrap, JavaScript

