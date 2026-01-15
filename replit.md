# RealGo MVP - Backend FastAPI

## Overview
API REST para gestión de rutas y viajes. Backend construido con FastAPI y asyncpg directo a PostgreSQL.

## Stack Tecnológico
- **Framework**: FastAPI
- **Driver DB**: asyncpg (directo, sin ORM)
- **Base de datos**: PostgreSQL (Replit)
- **Validación**: Pydantic

## Estructura del Proyecto
```
├── main.py                  # API completa (endpoints + schemas)
├── sql/
│   ├── schema.sql           # Esquema SQL
│   └── seed.sql             # Datos de prueba
└── pyproject.toml           # Dependencias Python
```

## Endpoints API
- `GET /health` - Health check
- `GET /routes` - Lista todas las rutas activas
- `GET /routes/{route_id}` - Detalle de ruta con paradas
- `POST /trips` - Crear un nuevo viaje (status 201)
- `GET /trips/{trip_id}` - Obtener detalle de un viaje

## Base de Datos (schema app)
- **users**: Usuarios (passenger, driver, admin)
- **routes**: Rutas con origen/destino y precio base
- **route_stops**: Paradas de cada ruta
- **trips**: Viajes solicitados con timestamps

## Variables de Entorno
- `DATABASE_URL` - URL de conexión a PostgreSQL (automático en Replit)

## Ejecutar
El servidor corre en puerto 5000:
```bash
uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

## Datos de Prueba
- Usuario hardcoded: `11111111-1111-1111-1111-111111111111`
- Ruta Lima Centro - Miraflores: `22222222-2222-2222-2222-222222222222`
- 4 paradas en la ruta (Plaza San Martin → Parque Kennedy)

## Validaciones en POST /trips
- `payment_method` debe ser: cash, yape, o plin
- `pickup_stop_id` y `dropoff_stop_id` deben ser diferentes
- Los stops deben pertenecer a la ruta especificada
- La ruta debe existir y estar activa
