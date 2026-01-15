"""
RealGo MVP - API REST para gestión de rutas y viajes de transporte.

Este módulo contiene la API completa construida con FastAPI y asyncpg.
"""

import os
import uuid
from contextlib import asynccontextmanager
from typing import List, Optional

import asyncpg
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está configurada")


# ============================================
# Gestión del ciclo de vida de la aplicación
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestiona el ciclo de vida de la aplicación (startup/shutdown)."""
    global pool
    # Startup
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    yield
    # Shutdown
    if pool:
        await pool.close()


app = FastAPI(
    title="RealGo MVP",
    description="API REST para gestión de rutas y viajes de transporte",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pool: asyncpg.Pool | None = None


# ============================================
# Dependencias
# ============================================
async def get_conn() -> asyncpg.Connection:
    """Obtiene una conexión del pool."""
    if pool is None:
        raise RuntimeError("DB pool no inicializado")
    async with pool.acquire() as conn:
        yield conn


# ============================================
# Modelos Pydantic
# ============================================
class RouteSummary(BaseModel):
    """Resumen de una ruta."""
    id: uuid.UUID
    name: str
    origin_name: str
    destination_name: str
    base_price_cents: int
    currency: str


class RouteStopOut(BaseModel):
    """Detalle de una parada de ruta."""
    id: uuid.UUID
    name: str
    stop_order: int


class RouteDetail(BaseModel):
    """Detalle completo de una ruta con sus paradas."""
    route: RouteSummary
    stops: List[RouteStopOut]


class TripCreate(BaseModel):
    """Payload para crear un nuevo viaje."""
    route_id: uuid.UUID = Field(..., description="ID de la ruta")
    pickup_stop_id: Optional[uuid.UUID] = Field(
        None, description="Paradero de subida (puede ser null)"
    )
    dropoff_stop_id: Optional[uuid.UUID] = Field(
        None, description="Paradero de bajada (puede ser null)"
    )
    payment_method: str = Field(..., description="cash | yape | plin")


class TripOut(BaseModel):
    """Respuesta de un viaje."""
    id: uuid.UUID
    route_id: uuid.UUID
    passenger_id: uuid.UUID
    pickup_stop_id: Optional[uuid.UUID]
    dropoff_stop_id: Optional[uuid.UUID]
    status: str
    payment_method: str
    price_cents: int
    currency: str
    created_at: str


class HealthResponse(BaseModel):
    """Respuesta del health check."""
    status: str
    service: str
    version: str


# ============================================
# Constantes
# ============================================
HARDCODED_PASSENGER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
VALID_PAYMENT_METHODS = {"cash", "yape", "plin"}


# ============================================
# Endpoints
# ============================================
@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
async def root():
    """Endpoint raíz - compatible con healthchecks."""
    return {"message": "RealGo MVP API", "docs": "/docs"}


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health() -> HealthResponse:
    """Verifica que el servicio esté funcionando."""
    return HealthResponse(status="ok", service="realgo-mvp", version="0.2.0")


@app.get("/routes", response_model=List[RouteSummary], tags=["Routes"])
async def list_routes(conn: asyncpg.Connection = Depends(get_conn)) -> List[RouteSummary]:
    """Lista todas las rutas activas."""
    rows = await conn.fetch(
        """
        SELECT
          id,
          name,
          origin_name,
          destination_name,
          base_price_cents,
          currency
        FROM app.routes
        WHERE is_active = TRUE
        ORDER BY name;
        """
    )
    return [
        RouteSummary(
            id=row["id"],
            name=row["name"],
            origin_name=row["origin_name"],
            destination_name=row["destination_name"],
            base_price_cents=row["base_price_cents"],
            currency=row["currency"],
        )
        for row in rows
    ]


@app.get("/routes/{route_id}", response_model=RouteDetail, tags=["Routes"])
async def get_route_detail(
    route_id: uuid.UUID,
    conn: asyncpg.Connection = Depends(get_conn),
) -> RouteDetail:
    """Obtiene el detalle de una ruta con sus paradas."""
    route_row = await conn.fetchrow(
        """
        SELECT
          id,
          name,
          origin_name,
          destination_name,
          base_price_cents,
          currency
        FROM app.routes
        WHERE id = $1 AND is_active = TRUE;
        """,
        route_id,
    )
    if not route_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")

    stops_rows = await conn.fetch(
        """
        SELECT id, name, stop_order
        FROM app.route_stops
        WHERE route_id = $1
        ORDER BY stop_order;
        """,
        route_id,
    )

    return RouteDetail(
        route=RouteSummary(
            id=route_row["id"],
            name=route_row["name"],
            origin_name=route_row["origin_name"],
            destination_name=route_row["destination_name"],
            base_price_cents=route_row["base_price_cents"],
            currency=route_row["currency"],
        ),
        stops=[
            RouteStopOut(
                id=row["id"],
                name=row["name"],
                stop_order=row["stop_order"],
            )
            for row in stops_rows
        ],
    )


@app.post("/trips", response_model=TripOut, status_code=status.HTTP_201_CREATED, tags=["Trips"])
async def create_trip(
    payload: TripCreate,
    conn: asyncpg.Connection = Depends(get_conn),
) -> TripOut:
    """Crea un nuevo viaje."""
    # Validar método de pago
    if payload.payment_method not in VALID_PAYMENT_METHODS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"payment_method inválido. Usa uno de: {', '.join(VALID_PAYMENT_METHODS)}",
        )

    # Validar que los stops sean diferentes
    if (
        payload.pickup_stop_id
        and payload.dropoff_stop_id
        and payload.pickup_stop_id == payload.dropoff_stop_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="pickup_stop_id y dropoff_stop_id deben ser diferentes",
        )

    # Verificar que la ruta existe
    route_row = await conn.fetchrow(
        "SELECT id, base_price_cents, currency FROM app.routes WHERE id = $1 AND is_active = TRUE;",
        payload.route_id,
    )
    if not route_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")

    # Validar que los stops pertenecen a la ruta
    for stop_id in [payload.pickup_stop_id, payload.dropoff_stop_id]:
        if stop_id:
            owns = await conn.fetchval(
                "SELECT 1 FROM app.route_stops WHERE id = $1 AND route_id = $2;",
                stop_id,
                payload.route_id,
            )
            if not owns:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="stop_id no pertenece a la ruta",
                )

    trip_id = uuid.uuid4()

    row = await conn.fetchrow(
        """
        INSERT INTO app.trips (
          id, route_id, passenger_id,
          pickup_stop_id, dropoff_stop_id,
          status, payment_method,
          price_cents, currency
        )
        VALUES ($1, $2, $3, $4, $5, 'requested', $6, $7, $8)
        RETURNING
          id, route_id, passenger_id,
          pickup_stop_id, dropoff_stop_id,
          status, payment_method,
          price_cents, currency, created_at;
        """,
        trip_id,
        payload.route_id,
        HARDCODED_PASSENGER_ID,
        payload.pickup_stop_id,
        payload.dropoff_stop_id,
        payload.payment_method,
        route_row["base_price_cents"],
        route_row["currency"],
    )

    return TripOut(
        id=row["id"],
        route_id=row["route_id"],
        passenger_id=row["passenger_id"],
        pickup_stop_id=row["pickup_stop_id"],
        dropoff_stop_id=row["dropoff_stop_id"],
        status=row["status"],
        payment_method=row["payment_method"],
        price_cents=row["price_cents"],
        currency=row["currency"],
        created_at=row["created_at"].isoformat(),
    )


@app.get("/trips/{trip_id}", response_model=TripOut, tags=["Trips"])
async def get_trip(
    trip_id: uuid.UUID,
    conn: asyncpg.Connection = Depends(get_conn),
) -> TripOut:
    """Obtiene el detalle de un viaje."""
    row = await conn.fetchrow(
        """
        SELECT
          id, route_id, passenger_id,
          pickup_stop_id, dropoff_stop_id,
          status, payment_method,
          price_cents, currency, created_at
        FROM app.trips
        WHERE id = $1;
        """,
        trip_id,
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    return TripOut(
        id=row["id"],
        route_id=row["route_id"],
        passenger_id=row["passenger_id"],
        pickup_stop_id=row["pickup_stop_id"],
        dropoff_stop_id=row["dropoff_stop_id"],
        status=row["status"],
        payment_method=row["payment_method"],
        price_cents=row["price_cents"],
        currency=row["currency"],
        created_at=row["created_at"].isoformat(),
    )


# Para ejecución directa (desarrollo local)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
