"""
RealGo MVP - API REST para gestión de rutas y viajes de transporte.

Este módulo contiene la API completa construida con FastAPI y asyncpg.
Incluye autenticación JWT via Better Auth (JWKS).
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

from auth import get_current_user, get_current_user_optional, require_role, CurrentUser

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
    version="0.3.0",
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
    driver_id: Optional[uuid.UUID] = None
    pickup_stop_id: Optional[uuid.UUID]
    dropoff_stop_id: Optional[uuid.UUID]
    status: str
    payment_method: str
    price_cents: int
    currency: str
    created_at: str


class UserSyncRequest(BaseModel):
    """Payload para sincronizar usuario."""
    role: str = Field(..., description="passenger | driver")
    full_name: Optional[str] = Field(None, description="Nombre completo")
    phone_e164: Optional[str] = Field(None, description="Teléfono en formato E.164")


class UserOut(BaseModel):
    """Respuesta de usuario."""
    id: uuid.UUID
    email: Optional[str]
    full_name: Optional[str]
    phone_e164: Optional[str]
    role: str
    is_active: bool


class HealthResponse(BaseModel):
    """Respuesta del health check."""
    status: str
    service: str
    version: str


# ============================================
# Constantes
# ============================================
VALID_PAYMENT_METHODS = {"cash", "yape", "plin"}
VALID_ROLES = {"passenger", "driver"}


# ============================================
# Endpoints - Health & Root
# ============================================
@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
async def root():
    """Endpoint raíz - compatible con healthchecks."""
    return {"message": "RealGo MVP API", "docs": "/docs"}


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health() -> HealthResponse:
    """Verifica que el servicio esté funcionando."""
    return HealthResponse(status="ok", service="realgo-mvp", version="0.3.0")


# ============================================
# Endpoints - User Sync (Better Auth)
# ============================================
@app.post("/me/sync", response_model=UserOut, tags=["Auth"])
async def sync_user(
    payload: UserSyncRequest,
    current_user: CurrentUser = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
) -> UserOut:
    """
    Sincroniza el usuario autenticado con la base de datos.
    Crea o actualiza el usuario en Neon con el rol especificado.
    """
    if payload.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rol inválido. Usa uno de: {', '.join(VALID_ROLES)}"
        )
    
    user_id = uuid.UUID(current_user.user_id)
    email = current_user.email
    full_name = payload.full_name or current_user.name
    
    # Upsert: crear o actualizar usuario
    row = await conn.fetchrow(
        """
        INSERT INTO app.users (id, email, full_name, phone_e164, role)
        VALUES ($1, $2, $3, $4, $5::app.user_role)
        ON CONFLICT (id) DO UPDATE SET
            email = COALESCE(EXCLUDED.email, app.users.email),
            full_name = COALESCE(EXCLUDED.full_name, app.users.full_name),
            phone_e164 = COALESCE(EXCLUDED.phone_e164, app.users.phone_e164),
            role = EXCLUDED.role,
            updated_at = now()
        RETURNING id, email, full_name, phone_e164, role, is_active;
        """,
        user_id,
        email,
        full_name,
        payload.phone_e164,
        payload.role,
    )
    
    return UserOut(
        id=row["id"],
        email=row["email"],
        full_name=row["full_name"],
        phone_e164=row["phone_e164"],
        role=row["role"],
        is_active=row["is_active"],
    )


@app.get("/me", response_model=UserOut, tags=["Auth"])
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
) -> UserOut:
    """Obtiene el perfil del usuario autenticado."""
    user_id = uuid.UUID(current_user.user_id)
    
    row = await conn.fetchrow(
        """
        SELECT id, email, full_name, phone_e164, role, is_active
        FROM app.users
        WHERE id = $1;
        """,
        user_id,
    )
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado. Usa POST /me/sync primero."
        )
    
    return UserOut(
        id=row["id"],
        email=row["email"],
        full_name=row["full_name"],
        phone_e164=row["phone_e164"],
        role=row["role"],
        is_active=row["is_active"],
    )


# ============================================
# Endpoints - Routes (Públicos)
# ============================================
@app.get("/routes", response_model=List[RouteSummary], tags=["Routes"])
async def list_routes(conn: asyncpg.Connection = Depends(get_conn)) -> List[RouteSummary]:
    """Lista todas las rutas activas."""
    rows = await conn.fetch(
        """
        SELECT id, name, origin_name, destination_name, base_price_cents, currency
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
        SELECT id, name, origin_name, destination_name, base_price_cents, currency
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


# ============================================
# Endpoints - Trips (Autenticados)
# ============================================
@app.post("/trips", response_model=TripOut, status_code=status.HTTP_201_CREATED, tags=["Trips"])
async def create_trip(
    payload: TripCreate,
    current_user: CurrentUser = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
) -> TripOut:
    """
    Crea un nuevo viaje.
    Solo usuarios con rol 'passenger' pueden crear viajes.
    """
    # Obtener usuario de BD para verificar rol
    user_id = uuid.UUID(current_user.user_id)
    user_row = await conn.fetchrow(
        "SELECT id, role FROM app.users WHERE id = $1 AND is_active = TRUE;",
        user_id,
    )
    
    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario no registrado. Usa POST /me/sync primero."
        )
    
    if user_row["role"] != "passenger":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los pasajeros pueden crear viajes."
        )
    
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
          id, route_id, passenger_id, driver_id,
          pickup_stop_id, dropoff_stop_id,
          status, payment_method,
          price_cents, currency, created_at;
        """,
        trip_id,
        payload.route_id,
        user_id,  # Ahora usamos el ID real del usuario autenticado
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
        driver_id=row["driver_id"],
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
    current_user: CurrentUser = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
) -> TripOut:
    """Obtiene el detalle de un viaje."""
    user_id = uuid.UUID(current_user.user_id)
    
    row = await conn.fetchrow(
        """
        SELECT
          id, route_id, passenger_id, driver_id,
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
    
    # Verificar que el usuario es parte del viaje (pasajero o conductor)
    if row["passenger_id"] != user_id and row["driver_id"] != user_id:
        # Verificar si es admin
        user_row = await conn.fetchrow(
            "SELECT role FROM app.users WHERE id = $1;",
            user_id,
        )
        if not user_row or user_row["role"] != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes acceso a este viaje"
            )

    return TripOut(
        id=row["id"],
        route_id=row["route_id"],
        passenger_id=row["passenger_id"],
        driver_id=row["driver_id"],
        pickup_stop_id=row["pickup_stop_id"],
        dropoff_stop_id=row["dropoff_stop_id"],
        status=row["status"],
        payment_method=row["payment_method"],
        price_cents=row["price_cents"],
        currency=row["currency"],
        created_at=row["created_at"].isoformat(),
    )


@app.get("/my/trips", response_model=List[TripOut], tags=["Trips"])
async def get_my_trips(
    current_user: CurrentUser = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
) -> List[TripOut]:
    """Obtiene los viajes del usuario autenticado."""
    user_id = uuid.UUID(current_user.user_id)
    
    rows = await conn.fetch(
        """
        SELECT
          id, route_id, passenger_id, driver_id,
          pickup_stop_id, dropoff_stop_id,
          status, payment_method,
          price_cents, currency, created_at
        FROM app.trips
        WHERE passenger_id = $1 OR driver_id = $1
        ORDER BY created_at DESC
        LIMIT 50;
        """,
        user_id,
    )
    
    return [
        TripOut(
            id=row["id"],
            route_id=row["route_id"],
            passenger_id=row["passenger_id"],
            driver_id=row["driver_id"],
            pickup_stop_id=row["pickup_stop_id"],
            dropoff_stop_id=row["dropoff_stop_id"],
            status=row["status"],
            payment_method=row["payment_method"],
            price_cents=row["price_cents"],
            currency=row["currency"],
            created_at=row["created_at"].isoformat(),
        )
        for row in rows
    ]


# Para ejecución directa (desarrollo local)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
