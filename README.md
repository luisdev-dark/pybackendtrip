# 🚗 RealGo MVP - Backend API

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.128+-green?style=for-the-badge&logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-NeonDB-336791?style=for-the-badge&logo=postgresql)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

**API REST para gestión de rutas y viajes de transporte**

[📖 Documentación](#-documentación-de-la-api) • [🚀 Deploy](#-despliegue-en-la-nube) • [🛠️ Desarrollo](#️-desarrollo-local)

</div>

---

## 📋 Descripción

RealGo MVP es un backend construido con **FastAPI** y **asyncpg** que proporciona una API REST para gestionar rutas de transporte y viajes de pasajeros. Está diseñado para conectar pasajeros con rutas de transporte público o privado.

### ✨ Características

- ⚡ **Alto rendimiento** - FastAPI + asyncpg (conexiones asíncronas)
- 🔐 **Validación robusta** - Pydantic para validación de datos
- 📊 **Auto-documentación** - Swagger UI y ReDoc integrados
- 🐘 **PostgreSQL** - Base de datos en NeonDB (serverless)
- 🐳 **Docker Ready** - Listo para contenedores
- ☁️ **Cloud Ready** - Configurado para Railway, Render y más

---

## 🛠️ Stack Tecnológico

| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| Python | 3.11+ | Runtime |
| FastAPI | 0.128+ | Framework Web |
| asyncpg | 0.31+ | Driver PostgreSQL (async) |
| Pydantic | 2.0+ | Validación de datos |
| Uvicorn | 0.40+ | Servidor ASGI |
| PostgreSQL | 15+ | Base de datos (NeonDB) |

---

## 📁 Estructura del Proyecto

```
realgo-mvp/
├── main.py                 # API completa (endpoints + schemas)
├── sql/
│   ├── schema.sql          # Esquema SQL de la base de datos
│   └── seed.sql            # Datos de prueba
├── Dockerfile              # Configuración Docker
├── Procfile                # Para Railway/Render/Heroku
├── render.yaml             # Blueprint para Render.com
├── railway.json            # Configuración Railway
├── requirements.txt        # Dependencias Python
├── pyproject.toml          # Metadatos del proyecto
├── .env.example            # Template de variables de entorno
├── check_and_seed.py       # Script para verificar/cargar datos
├── test_db_connection.py   # Script para probar conexión
└── README.md               # Este archivo
```

---

## 🔌 Endpoints API

### Health Check
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/health` | Verifica estado del servicio |

### Rutas
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/routes` | Lista todas las rutas activas |
| `GET` | `/routes/{route_id}` | Detalle de ruta con paradas |

### Viajes
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/trips` | Crear un nuevo viaje |
| `GET` | `/trips/{trip_id}` | Obtener detalle de un viaje |

---

## 🛠️ Desarrollo Local

### Prerrequisitos
- Python 3.11+
- pip o uv
- PostgreSQL (o cuenta en [NeonDB](https://neon.tech))

### Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/realgo-mvp.git
cd realgo-mvp

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o en Windows:
.\venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tu DATABASE_URL

# 5. Verificar conexión a BD
python test_db_connection.py

# 6. Cargar datos de prueba (si es necesario)
python check_and_seed.py

# 7. Ejecutar servidor
uvicorn main:app --reload --port 8000
```

El servidor estará disponible en: `http://localhost:8000`

---

## 📖 Documentación de la API

Una vez iniciado el servidor, accede a:

| Interfaz | URL |
|----------|-----|
| **Swagger UI** | `http://localhost:8000/docs` |
| **ReDoc** | `http://localhost:8000/redoc` |
| **OpenAPI JSON** | `http://localhost:8000/openapi.json` |

---

## 🚀 Despliegue en la Nube

### Railway (Recomendado)

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new)

1. Conecta tu repositorio de GitHub a Railway
2. Añade la variable de entorno `DATABASE_URL`
3. Railway detectará automáticamente el `Procfile`
4. ¡Listo! Tu API estará en línea

### Render

1. Conecta tu repositorio a [Render.com](https://render.com)
2. Render detectará `render.yaml` automáticamente
3. Añade `DATABASE_URL` en el dashboard
4. Deploy automático configurado

### Docker

```bash
# Construir imagen
docker build -t realgo-mvp .

# Ejecutar contenedor
docker run -d -p 8000:8000 \
  -e DATABASE_URL="tu_database_url" \
  realgo-mvp
```

---

## 📊 Base de Datos

### Esquema (`app`)

| Tabla | Descripción |
|-------|-------------|
| `users` | Usuarios (pasajeros) |
| `routes` | Rutas con origen/destino y precio |
| `route_stops` | Paradas de cada ruta |
| `trips` | Viajes solicitados |

### Tipos Enum

- `app.trip_status`: `requested`, `started`, `finished`, `cancelled`
- `app.payment_method`: `cash`, `yape`, `plin`

### Configurar Base de Datos

```bash
# Ejecutar schema
psql $DATABASE_URL -f sql/schema.sql

# Cargar datos de prueba
psql $DATABASE_URL -f sql/seed.sql
```

---

## 🧪 Ejemplos de Uso

### Obtener todas las rutas

```bash
curl http://localhost:8000/routes
```

### Obtener detalle de una ruta

```bash
curl http://localhost:8000/routes/22222222-2222-2222-2222-222222222222
```

### Crear un viaje

```bash
curl -X POST http://localhost:8000/trips \
  -H "Content-Type: application/json" \
  -d '{
    "route_id": "22222222-2222-2222-2222-222222222222",
    "pickup_stop_id": "44444444-4444-4444-4444-444444444444",
    "dropoff_stop_id": "66666666-6666-6666-6666-666666666666",
    "payment_method": "yape"
  }'
```

---

## 🔒 Variables de Entorno

| Variable | Requerida | Descripción |
|----------|:---------:|-------------|
| `DATABASE_URL` | ✅ | URL de conexión PostgreSQL |

Ejemplo:
```
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
```

---

## ✅ Validaciones en POST /trips

- `payment_method` debe ser: `cash`, `yape`, o `plin`
- `pickup_stop_id` y `dropoff_stop_id` deben ser diferentes
- Los stops deben pertenecer a la ruta especificada
- La ruta debe existir y estar activa

---

## 🐛 Troubleshooting

| Error | Solución |
|-------|----------|
| `DATABASE_URL no está configurada` | Verifica que `.env` existe y tiene la URL |
| Error de conexión a BD | Ejecuta `python test_db_connection.py` |
| No hay rutas en `/routes` | Ejecuta `python check_and_seed.py` |

---

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver [LICENSE](LICENSE) para más detalles.

---

## 👥 Equipo

**RealGo Team**

---

<div align="center">

Hecho con ❤️ para facilitar el transporte

</div>
