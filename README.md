# RealGo MVP - Backend FastAPI

## 🚀 Descripción
API REST para gestión de rutas y viajes de transporte. Backend construido con FastAPI y asyncpg conectado a NeonDB (PostgreSQL).

## 🛠️ Stack Tecnológico
- **Framework**: FastAPI 0.128+
- **Driver DB**: asyncpg (directo, sin ORM)
- **Base de datos**: PostgreSQL (NeonDB)
- **Validación**: Pydantic
- **Servidor**: Uvicorn

## 📁 Estructura del Proyecto
```
├── main.py                  # API completa (endpoints + schemas)
├── sql/
│   ├── schema.sql           # Esquema SQL de la base de datos
│   └── seed.sql             # Datos de prueba
├── .env                     # Variables de entorno (DATABASE_URL)
├── pyproject.toml           # Dependencias Python
├── test_db_connection.py    # Script para probar conexión a BD
├── check_and_seed.py        # Script para verificar y cargar datos
└── README.md               # Este archivo
```

## 🔧 Instalación

### Prerrequisitos
- Python 3.11+
- pip o uv

### Pasos de instalación

1. **Clonar el repositorio**
```bash
git clone <repo-url>
cd FastAPI-Confirma
```

2. **Instalar dependencias**
```bash
pip install -r requirements.txt
# o usando uv
uv sync
```

3. **Configurar variables de entorno**
Crear archivo `.env` con:
```
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
```

4. **Verificar conexión a la base de datos**
```bash
python test_db_connection.py
```

5. **Verificar datos de prueba**
```bash
python check_and_seed.py
```

## 🚀 Ejecutar el servidor

```bash
uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

El servidor estará disponible en: `http://localhost:5000`

## 📚 Documentación de la API

Una vez iniciado el servidor, puedes acceder a:

- **Swagger UI**: `http://localhost:5000/docs`
- **ReDoc**: `http://localhost:5000/redoc`

## 🔌 Endpoints API

### Health Check
- `GET /health` - Verifica que el servicio esté funcionando

### Rutas
- `GET /routes` - Lista todas las rutas activas
- `GET /routes/{route_id}` - Detalle de ruta con paradas

### Viajes
- `POST /trips` - Crear un nuevo viaje (status 201)
- `GET /trips/{trip_id}` - Obtener detalle de un viaje

## 📊 Base de Datos (schema `app`)

### Tablas
- **users**: Usuarios (passenger, driver, admin)
- **routes**: Rutas con origen/destino y precio base
- **route_stops**: Paradas de cada ruta
- **trips**: Viajes solicitados con timestamps

### Tipos de Enum
- `app.user_role`: passenger, driver, admin
- `app.trip_status`: requested, confirmed, started, finished, cancelled
- `app.payment_method`: cash, yape, plin

## 🧪 Datos de Prueba

El proyecto incluye datos de prueba en `sql/seed.sql`:

- **Usuario hardcoded**: `11111111-1111-1111-1111-111111111111`
- **Rutas disponibles**:
  - Hoja Redonda → Chincha Alta
  - Chincha Alta → Hoja Redonda
- **Paradas**: 6 paradas distribuidas en las rutas

## ✅ Validaciones en POST /trips

- `payment_method` debe ser: cash, yape, o plin
- `pickup_stop_id` y `dropoff_stop_id` deben ser diferentes
- Los stops deben pertenecer a la ruta especificada
- La ruta debe existir y estar activa

## 📝 Ejemplos de Uso

### Obtener todas las rutas
```bash
curl http://localhost:5000/routes
```

### Obtener detalle de una ruta
```bash
curl http://localhost:5000/routes/22222222-2222-2222-2222-222222222222
```

### Crear un viaje
```bash
curl -X POST http://localhost:5000/trips \
  -H "Content-Type: application/json" \
  -d '{
    "route_id": "22222222-2222-2222-2222-222222222222",
    "pickup_stop_id": "33333333-3333-3333-3333-333333333331",
    "dropoff_stop_id": "33333333-3333-3333-3333-333333333332",
    "payment_method": "cash"
  }'
```

### Obtener detalle de un viaje
```bash
curl http://localhost:5000/trips/{trip_id}
```

## 🔒 Variables de Entorno

- `DATABASE_URL` - URL de conexión a PostgreSQL (requerido)

## 🐛 Troubleshooting

### Error: "DATABASE_URL no está configurada"
Verifica que el archivo `.env` existe y tiene la URL correcta.

### Error de conexión a la base de datos
Ejecuta `python test_db_connection.py` para diagnosticar el problema.

### El servidor no inicia
Asegúrate de que todas las dependencias estén instaladas:
```bash
pip install -r requirements.txt
```

## 📄 Licencia
Este proyecto es parte de RealGo MVP.

## 👥 Autores
- RealGo Team
