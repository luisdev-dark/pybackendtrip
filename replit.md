# RealGo MVP - Backend FastAPI

## Overview
API REST para gestión de rutas y viajes. Backend construido con FastAPI, SQLAlchemy async y PostgreSQL.

## Stack Tecnológico
- **Framework**: FastAPI
- **ORM**: SQLAlchemy 2.x (async)
- **Base de datos**: PostgreSQL (Replit)
- **Driver**: asyncpg
- **Validación**: Pydantic

## Estructura del Proyecto
```
├── app/
│   ├── main.py              # Punto de entrada FastAPI
│   ├── core/
│   │   ├── config.py        # Configuración (env vars)
│   │   └── db.py            # Conexión a DB async
│   ├── models/
│   │   ├── base.py          # Base del ORM
│   │   ├── user.py          # Modelo User
│   │   ├── route.py         # Modelo Route + RouteStop
│   │   └── trip.py          # Modelo Trip
│   ├── schemas/
│   │   ├── user.py          # Pydantic schemas
│   │   ├── route.py
│   │   └── trip.py
│   └── api/
│       ├── deps.py          # Dependencias (get_db)
│       └── routes/
│           ├── health.py    # /health
│           ├── routes.py    # /routes
│           └── trips.py     # /trips
├── sql/
│   ├── schema.sql           # Esquema SQL
│   └── seed.sql             # Datos de prueba
├── main.py                  # Entry point para uvicorn
└── pyproject.toml           # Dependencias Python
```

## Endpoints API
- `GET /health` - Health check
- `GET /routes` - Lista todas las rutas activas
- `GET /routes/{route_id}` - Detalle de ruta con paradas
- `POST /trips` - Crear un nuevo viaje
- `GET /trips/{trip_id}` - Obtener detalle de un viaje

## Modelos de Base de Datos
- **users**: Usuarios (passenger, driver, admin)
- **routes**: Rutas con origen/destino
- **route_stops**: Paradas de cada ruta
- **trips**: Viajes solicitados

## Variables de Entorno
- `DATABASE_URL` - URL de conexión a PostgreSQL (automático en Replit)

## Ejecutar
El servidor corre en puerto 5000:
```bash
uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

## Datos de Prueba
- Usuario de prueba: `11111111-1111-1111-1111-111111111111`
- Ruta Lima Centro - Miraflores: `22222222-2222-2222-2222-222222222222`
- 4 paradas en la ruta
