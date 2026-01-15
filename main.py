"""
RealGo MVP+ - API REST para Sistema de Colectivos

API completa con:
- Autenticación JWT via Neon Auth
- Gestión de rutas y paradas
- Turnos de conductor (driver_shifts)
- Pedidos de pasajeros (trips)
- Sistema de mensajes
"""

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

import asyncpg
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from auth import get_current_user, get_current_user_optional, CurrentUser

# Cargar variables de entorno
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está configurada")


# ============================================
# Ciclo de vida de la aplicación
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    yield
    if pool:
        await pool.close()


app = FastAPI(
    title="RealGo MVP+",
    description="API para Sistema de Colectivos - Conductor y Pasajero",
    version="0.4.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pool: asyncpg.Pool | None = None


async def get_conn() -> asyncpg.Connection:
    if pool is None:
        raise RuntimeError("DB pool no inicializado")
    async with pool.acquire() as conn:
        yield conn


# ============================================
# Modelos Pydantic
# ============================================

# --- Health ---
class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


# --- User ---
class UserOut(BaseModel):
    id: uuid.UUID
    email: Optional[str]
    full_name: Optional[str]
    phone_e164: Optional[str]
    role: str
    is_active: bool


class UserSyncRequest(BaseModel):
    role: str = Field(..., description="passenger | driver")
    full_name: Optional[str] = None
    phone_e164: Optional[str] = None


# --- Routes ---
class RouteSummary(BaseModel):
    id: uuid.UUID
    name: str
    origin_name: str
    destination_name: str
    base_price_cents: int
    currency: str


class RouteStopOut(BaseModel):
    id: uuid.UUID
    name: str
    stop_order: int


class RouteDetail(BaseModel):
    route: RouteSummary
    stops: List[RouteStopOut]


# --- Vehicles ---
class VehicleCreate(BaseModel):
    plate: str
    brand: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None
    year: Optional[int] = None
    total_seats: int = Field(4, ge=1, le=20)


class VehicleOut(BaseModel):
    id: uuid.UUID
    plate: str
    brand: Optional[str]
    model: Optional[str]
    color: Optional[str]
    year: Optional[int]
    total_seats: int
    is_active: bool


# --- Driver Shifts ---
class ShiftCreate(BaseModel):
    route_id: uuid.UUID
    vehicle_id: Optional[uuid.UUID] = None
    total_seats: int = Field(4, ge=1, le=20)


class ShiftOut(BaseModel):
    id: uuid.UUID
    driver_id: uuid.UUID
    route_id: uuid.UUID
    vehicle_id: Optional[uuid.UUID]
    status: str
    total_seats: int
    available_seats: int
    starts_at: Optional[str]
    created_at: str


# --- Trips ---
class TripCreate(BaseModel):
    route_id: uuid.UUID
    pickup_stop_id: Optional[uuid.UUID] = None
    dropoff_stop_id: Optional[uuid.UUID] = None
    pickup_note: Optional[str] = Field(None, max_length=200)
    seats_requested: int = Field(1, ge=1, le=10)
    payment_method: str = "cash"


class TripOut(BaseModel):
    id: uuid.UUID
    route_id: uuid.UUID
    shift_id: Optional[uuid.UUID]
    passenger_id: uuid.UUID
    driver_id: Optional[uuid.UUID]
    pickup_stop_id: Optional[uuid.UUID]
    dropoff_stop_id: Optional[uuid.UUID]
    pickup_note: Optional[str]
    seats_requested: int
    status: str
    payment_method: str
    price_cents: int
    currency: str
    created_at: str


class TripWithPassenger(TripOut):
    passenger_name: Optional[str]
    passenger_phone: Optional[str]


# --- Messages ---
class MessageCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)


class MessageOut(BaseModel):
    id: uuid.UUID
    trip_id: uuid.UUID
    sender_id: uuid.UUID
    message: str
    is_read: bool
    created_at: str


# ============================================
# Helpers
# ============================================
VALID_PAYMENT_METHODS = {"cash", "yape", "plin"}
VALID_ROLES = {"passenger", "driver"}


async def verify_driver_role(user_id: uuid.UUID, conn: asyncpg.Connection) -> dict:
    """Verifica que el usuario sea conductor activo."""
    row = await conn.fetchrow(
        "SELECT id, role, is_active FROM app.users WHERE id = $1",
        user_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if row["role"] != "driver":
        raise HTTPException(status_code=403, detail="Solo conductores pueden acceder")
    if not row["is_active"]:
        raise HTTPException(status_code=403, detail="Usuario inactivo")
    return dict(row)


async def verify_passenger_role(user_id: uuid.UUID, conn: asyncpg.Connection) -> dict:
    """Verifica que el usuario sea pasajero activo."""
    row = await conn.fetchrow(
        "SELECT id, role, is_active FROM app.users WHERE id = $1",
        user_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no registrado. Usa POST /me/sync")
    if row["role"] != "passenger":
        raise HTTPException(status_code=403, detail="Solo pasajeros pueden crear viajes")
    if not row["is_active"]:
        raise HTTPException(status_code=403, detail="Usuario inactivo")
    return dict(row)


# ============================================
# ENDPOINTS: Health & Root
# ============================================
@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
async def root():
    return {"message": "RealGo MVP+ API", "docs": "/docs"}


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health():
    return HealthResponse(status="ok", service="realgo-mvp-plus", version="0.4.0")


# ============================================
# ENDPOINTS: Auth / User
# ============================================
@app.post("/me/sync", response_model=UserOut, tags=["Auth"])
async def sync_user(
    payload: UserSyncRequest,
    current_user: CurrentUser = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
):
    """Sincroniza usuario autenticado con la BD. Crea o actualiza."""
    if payload.role not in VALID_ROLES:
        raise HTTPException(400, f"Rol inválido. Usa: {', '.join(VALID_ROLES)}")
    
    user_id = uuid.UUID(current_user.user_id)
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
        user_id, current_user.email, payload.full_name or current_user.name,
        payload.phone_e164, payload.role,
    )
    
    # Si es driver, crear registro en drivers si no existe
    if payload.role == "driver":
        await conn.execute(
            """
            INSERT INTO app.drivers (user_id) VALUES ($1)
            ON CONFLICT (user_id) DO NOTHING
            """,
            user_id
        )
    
    return UserOut(**dict(row))


@app.get("/me", response_model=UserOut, tags=["Auth"])
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
):
    """Obtiene perfil del usuario autenticado."""
    user_id = uuid.UUID(current_user.user_id)
    row = await conn.fetchrow(
        "SELECT id, email, full_name, phone_e164, role, is_active FROM app.users WHERE id = $1",
        user_id
    )
    if not row:
        raise HTTPException(404, "Usuario no encontrado. Usa POST /me/sync")
    return UserOut(**dict(row))


# ============================================
# ENDPOINTS: Routes (Público)
# ============================================
@app.get("/routes", response_model=List[RouteSummary], tags=["Routes"])
async def list_routes(conn: asyncpg.Connection = Depends(get_conn)):
    """Lista rutas activas."""
    rows = await conn.fetch(
        """SELECT id, name, origin_name, destination_name, base_price_cents, currency
           FROM app.routes WHERE is_active = TRUE ORDER BY name"""
    )
    return [RouteSummary(**dict(r)) for r in rows]


@app.get("/routes/{route_id}", response_model=RouteDetail, tags=["Routes"])
async def get_route(route_id: uuid.UUID, conn: asyncpg.Connection = Depends(get_conn)):
    """Detalle de ruta con paradas."""
    route = await conn.fetchrow(
        """SELECT id, name, origin_name, destination_name, base_price_cents, currency
           FROM app.routes WHERE id = $1 AND is_active = TRUE""",
        route_id
    )
    if not route:
        raise HTTPException(404, "Ruta no encontrada")
    
    stops = await conn.fetch(
        "SELECT id, name, stop_order FROM app.route_stops WHERE route_id = $1 ORDER BY stop_order",
        route_id
    )
    return RouteDetail(
        route=RouteSummary(**dict(route)),
        stops=[RouteStopOut(**dict(s)) for s in stops]
    )


# ============================================
# ENDPOINTS: Driver - Vehicles
# ============================================
@app.post("/driver/vehicles", response_model=VehicleOut, status_code=201, tags=["Driver"])
async def create_vehicle(
    payload: VehicleCreate,
    current_user: CurrentUser = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
):
    """Registra un vehículo (solo conductores)."""
    user_id = uuid.UUID(current_user.user_id)
    await verify_driver_role(user_id, conn)
    
    row = await conn.fetchrow(
        """
        INSERT INTO app.vehicles (owner_id, plate, brand, model, color, year, total_seats)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id, plate, brand, model, color, year, total_seats, is_active
        """,
        user_id, payload.plate.upper(), payload.brand, payload.model,
        payload.color, payload.year, payload.total_seats
    )
    return VehicleOut(**dict(row))


@app.get("/driver/vehicles", response_model=List[VehicleOut], tags=["Driver"])
async def list_my_vehicles(
    current_user: CurrentUser = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
):
    """Lista vehículos del conductor."""
    user_id = uuid.UUID(current_user.user_id)
    await verify_driver_role(user_id, conn)
    
    rows = await conn.fetch(
        "SELECT id, plate, brand, model, color, year, total_seats, is_active FROM app.vehicles WHERE owner_id = $1",
        user_id
    )
    return [VehicleOut(**dict(r)) for r in rows]


# ============================================
# ENDPOINTS: Driver - Shifts
# ============================================
@app.post("/driver/shifts", response_model=ShiftOut, status_code=201, tags=["Driver"])
async def create_shift(
    payload: ShiftCreate,
    current_user: CurrentUser = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
):
    """Abre un turno/viaje activo (solo conductores)."""
    user_id = uuid.UUID(current_user.user_id)
    await verify_driver_role(user_id, conn)
    
    # Verificar que no tenga otro shift abierto
    existing = await conn.fetchval(
        "SELECT id FROM app.driver_shifts WHERE driver_id = $1 AND status = 'open'",
        user_id
    )
    if existing:
        raise HTTPException(400, "Ya tienes un turno abierto. Ciérralo primero.")
    
    # Verificar ruta
    route = await conn.fetchrow(
        "SELECT id, base_price_cents FROM app.routes WHERE id = $1 AND is_active = TRUE",
        payload.route_id
    )
    if not route:
        raise HTTPException(404, "Ruta no encontrada")
    
    row = await conn.fetchrow(
        """
        INSERT INTO app.driver_shifts (driver_id, vehicle_id, route_id, total_seats, available_seats, starts_at)
        VALUES ($1, $2, $3, $4, $4, now())
        RETURNING id, driver_id, route_id, vehicle_id, status, total_seats, available_seats, starts_at, created_at
        """,
        user_id, payload.vehicle_id, payload.route_id, payload.total_seats
    )
    return ShiftOut(
        **{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in dict(row).items()}
    )


@app.get("/driver/shifts/current", response_model=Optional[ShiftOut], tags=["Driver"])
async def get_current_shift(
    current_user: CurrentUser = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
):
    """Obtiene el turno activo del conductor."""
    user_id = uuid.UUID(current_user.user_id)
    await verify_driver_role(user_id, conn)
    
    row = await conn.fetchrow(
        """SELECT id, driver_id, route_id, vehicle_id, status, total_seats, available_seats, starts_at, created_at
           FROM app.driver_shifts WHERE driver_id = $1 AND status = 'open'""",
        user_id
    )
    if not row:
        return None
    return ShiftOut(**{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in dict(row).items()})


@app.post("/driver/shifts/{shift_id}/close", response_model=ShiftOut, tags=["Driver"])
async def close_shift(
    shift_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
):
    """Cierra un turno."""
    user_id = uuid.UUID(current_user.user_id)
    await verify_driver_role(user_id, conn)
    
    row = await conn.fetchrow(
        """UPDATE app.driver_shifts SET status = 'closed', ends_at = now()
           WHERE id = $1 AND driver_id = $2 AND status = 'open'
           RETURNING id, driver_id, route_id, vehicle_id, status, total_seats, available_seats, starts_at, created_at""",
        shift_id, user_id
    )
    if not row:
        raise HTTPException(404, "Turno no encontrado o ya cerrado")
    return ShiftOut(**{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in dict(row).items()})


# ============================================
# ENDPOINTS: Driver - Trip Requests
# ============================================
@app.get("/driver/requests", response_model=List[TripWithPassenger], tags=["Driver"])
async def get_trip_requests(
    current_user: CurrentUser = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
    since: Optional[datetime] = Query(None, description="Filtrar desde timestamp"),
):
    """Lista pedidos pendientes para el turno activo del conductor."""
    user_id = uuid.UUID(current_user.user_id)
    await verify_driver_role(user_id, conn)
    
    # Buscar shift activo
    shift = await conn.fetchrow(
        "SELECT id, route_id FROM app.driver_shifts WHERE driver_id = $1 AND status = 'open'",
        user_id
    )
    if not shift:
        return []
    
    query = """
        SELECT t.id, t.route_id, t.shift_id, t.passenger_id, t.driver_id,
               t.pickup_stop_id, t.dropoff_stop_id, t.pickup_note, t.seats_requested,
               t.status, t.payment_method, t.price_cents, t.currency, t.created_at,
               u.full_name as passenger_name, u.phone_e164 as passenger_phone
        FROM app.trips t
        JOIN app.users u ON u.id = t.passenger_id
        WHERE t.route_id = $1 AND t.status = 'requested'
    """
    params = [shift["route_id"]]
    
    if since:
        query += " AND t.created_at > $2"
        params.append(since)
    
    query += " ORDER BY t.created_at ASC"
    
    rows = await conn.fetch(query, *params)
    return [
        TripWithPassenger(**{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in dict(r).items()})
        for r in rows
    ]


@app.post("/driver/trips/{trip_id}/accept", response_model=TripOut, tags=["Driver"])
async def accept_trip(
    trip_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
):
    """Acepta un pedido de viaje."""
    user_id = uuid.UUID(current_user.user_id)
    await verify_driver_role(user_id, conn)
    
    # Verificar shift activo
    shift = await conn.fetchrow(
        "SELECT id, route_id, available_seats FROM app.driver_shifts WHERE driver_id = $1 AND status = 'open'",
        user_id
    )
    if not shift:
        raise HTTPException(400, "No tienes un turno activo")
    
    # Obtener trip
    trip = await conn.fetchrow(
        "SELECT id, route_id, seats_requested, status FROM app.trips WHERE id = $1",
        trip_id
    )
    if not trip:
        raise HTTPException(404, "Viaje no encontrado")
    if trip["status"] != "requested":
        raise HTTPException(400, f"Viaje no está en estado 'requested', está en '{trip['status']}'")
    if trip["route_id"] != shift["route_id"]:
        raise HTTPException(400, "Este viaje no es de tu ruta")
    if shift["available_seats"] < trip["seats_requested"]:
        raise HTTPException(400, f"No hay suficientes asientos ({shift['available_seats']} disponibles)")
    
    # Actualizar trip y shift
    async with conn.transaction():
        row = await conn.fetchrow(
            """UPDATE app.trips SET status = 'accepted', driver_id = $1, shift_id = $2
               WHERE id = $3
               RETURNING id, route_id, shift_id, passenger_id, driver_id, pickup_stop_id, dropoff_stop_id,
                         pickup_note, seats_requested, status, payment_method, price_cents, currency, created_at""",
            user_id, shift["id"], trip_id
        )
        await conn.execute(
            "UPDATE app.driver_shifts SET available_seats = available_seats - $1 WHERE id = $2",
            trip["seats_requested"], shift["id"]
        )
    
    return TripOut(**{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in dict(row).items()})


@app.post("/driver/trips/{trip_id}/reject", response_model=TripOut, tags=["Driver"])
async def reject_trip(
    trip_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
):
    """Rechaza un pedido de viaje."""
    user_id = uuid.UUID(current_user.user_id)
    await verify_driver_role(user_id, conn)
    
    row = await conn.fetchrow(
        """UPDATE app.trips SET status = 'rejected'
           WHERE id = $1 AND status = 'requested'
           RETURNING id, route_id, shift_id, passenger_id, driver_id, pickup_stop_id, dropoff_stop_id,
                     pickup_note, seats_requested, status, payment_method, price_cents, currency, created_at""",
        trip_id
    )
    if not row:
        raise HTTPException(404, "Viaje no encontrado o ya procesado")
    return TripOut(**{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in dict(row).items()})


@app.post("/driver/trips/{trip_id}/onboard", response_model=TripOut, tags=["Driver"])
async def onboard_passenger(
    trip_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
):
    """Marca que el pasajero abordó."""
    user_id = uuid.UUID(current_user.user_id)
    await verify_driver_role(user_id, conn)
    
    row = await conn.fetchrow(
        """UPDATE app.trips SET status = 'onboard'
           WHERE id = $1 AND driver_id = $2 AND status = 'accepted'
           RETURNING id, route_id, shift_id, passenger_id, driver_id, pickup_stop_id, dropoff_stop_id,
                     pickup_note, seats_requested, status, payment_method, price_cents, currency, created_at""",
        trip_id, user_id
    )
    if not row:
        raise HTTPException(404, "Viaje no encontrado o no eres el conductor")
    return TripOut(**{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in dict(row).items()})


@app.post("/driver/trips/{trip_id}/complete", response_model=TripOut, tags=["Driver"])
async def complete_trip(
    trip_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
):
    """Marca viaje como completado."""
    user_id = uuid.UUID(current_user.user_id)
    await verify_driver_role(user_id, conn)
    
    row = await conn.fetchrow(
        """UPDATE app.trips SET status = 'completed'
           WHERE id = $1 AND driver_id = $2 AND status IN ('accepted', 'onboard')
           RETURNING id, route_id, shift_id, passenger_id, driver_id, pickup_stop_id, dropoff_stop_id,
                     pickup_note, seats_requested, status, payment_method, price_cents, currency, created_at""",
        trip_id, user_id
    )
    if not row:
        raise HTTPException(404, "Viaje no encontrado o no puedes completarlo")
    return TripOut(**{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in dict(row).items()})


# ============================================
# ENDPOINTS: Passenger - Trips
# ============================================
@app.post("/trips", response_model=TripOut, status_code=201, tags=["Trips"])
async def create_trip(
    payload: TripCreate,
    current_user: CurrentUser = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
):
    """Crea un nuevo pedido de viaje (solo pasajeros)."""
    user_id = uuid.UUID(current_user.user_id)
    await verify_passenger_role(user_id, conn)
    
    if payload.payment_method not in VALID_PAYMENT_METHODS:
        raise HTTPException(400, f"Método de pago inválido. Usa: {', '.join(VALID_PAYMENT_METHODS)}")
    
    if payload.pickup_stop_id and payload.dropoff_stop_id and payload.pickup_stop_id == payload.dropoff_stop_id:
        raise HTTPException(400, "Pickup y dropoff deben ser diferentes")
    
    # Verificar ruta
    route = await conn.fetchrow(
        "SELECT id, base_price_cents, currency FROM app.routes WHERE id = $1 AND is_active = TRUE",
        payload.route_id
    )
    if not route:
        raise HTTPException(404, "Ruta no encontrada")
    
    # Buscar shift abierto con asientos disponibles
    shift = await conn.fetchrow(
        """SELECT id, driver_id, available_seats FROM app.driver_shifts
           WHERE route_id = $1 AND status = 'open' AND available_seats >= $2
           ORDER BY created_at ASC LIMIT 1""",
        payload.route_id, payload.seats_requested
    )
    
    if not shift:
        raise HTTPException(409, "No hay unidades disponibles en esta ruta")
    
    # Validar stops
    for stop_id in [payload.pickup_stop_id, payload.dropoff_stop_id]:
        if stop_id:
            exists = await conn.fetchval(
                "SELECT 1 FROM app.route_stops WHERE id = $1 AND route_id = $2",
                stop_id, payload.route_id
            )
            if not exists:
                raise HTTPException(400, "Stop no pertenece a la ruta")
    
    # Calcular precio
    price = route["base_price_cents"] * payload.seats_requested
    
    row = await conn.fetchrow(
        """INSERT INTO app.trips (route_id, shift_id, passenger_id, pickup_stop_id, dropoff_stop_id,
                                   pickup_note, seats_requested, payment_method, price_cents, currency)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
           RETURNING id, route_id, shift_id, passenger_id, driver_id, pickup_stop_id, dropoff_stop_id,
                     pickup_note, seats_requested, status, payment_method, price_cents, currency, created_at""",
        payload.route_id, shift["id"], user_id, payload.pickup_stop_id, payload.dropoff_stop_id,
        payload.pickup_note, payload.seats_requested, payload.payment_method, price, route["currency"]
    )
    
    return TripOut(**{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in dict(row).items()})


@app.get("/trips/{trip_id}", response_model=TripOut, tags=["Trips"])
async def get_trip(
    trip_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
):
    """Obtiene detalle de un viaje."""
    user_id = uuid.UUID(current_user.user_id)
    
    row = await conn.fetchrow(
        """SELECT id, route_id, shift_id, passenger_id, driver_id, pickup_stop_id, dropoff_stop_id,
                  pickup_note, seats_requested, status, payment_method, price_cents, currency, created_at
           FROM app.trips WHERE id = $1""",
        trip_id
    )
    if not row:
        raise HTTPException(404, "Viaje no encontrado")
    
    # Verificar acceso
    if row["passenger_id"] != user_id and row["driver_id"] != user_id:
        user_row = await conn.fetchrow("SELECT role FROM app.users WHERE id = $1", user_id)
        if not user_row or user_row["role"] != "admin":
            raise HTTPException(403, "No tienes acceso a este viaje")
    
    return TripOut(**{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in dict(row).items()})


@app.get("/my/trips", response_model=List[TripOut], tags=["Trips"])
async def get_my_trips(
    current_user: CurrentUser = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
    status: Optional[str] = Query(None),
):
    """Lista viajes del usuario (como pasajero o conductor)."""
    user_id = uuid.UUID(current_user.user_id)
    
    query = """
        SELECT id, route_id, shift_id, passenger_id, driver_id, pickup_stop_id, dropoff_stop_id,
               pickup_note, seats_requested, status, payment_method, price_cents, currency, created_at
        FROM app.trips WHERE passenger_id = $1 OR driver_id = $1
    """
    params = [user_id]
    
    if status:
        query += " AND status = $2::app.trip_status"
        params.append(status)
    
    query += " ORDER BY created_at DESC LIMIT 50"
    
    rows = await conn.fetch(query, *params)
    return [
        TripOut(**{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in dict(r).items()})
        for r in rows
    ]


@app.post("/trips/{trip_id}/cancel", response_model=TripOut, tags=["Trips"])
async def cancel_trip(
    trip_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
):
    """Cancela un viaje (solo el pasajero, si está en requested/accepted)."""
    user_id = uuid.UUID(current_user.user_id)
    
    trip = await conn.fetchrow(
        "SELECT id, passenger_id, shift_id, seats_requested, status FROM app.trips WHERE id = $1",
        trip_id
    )
    if not trip:
        raise HTTPException(404, "Viaje no encontrado")
    if trip["passenger_id"] != user_id:
        raise HTTPException(403, "Solo el pasajero puede cancelar")
    if trip["status"] not in ("requested", "accepted"):
        raise HTTPException(400, f"No se puede cancelar un viaje en estado '{trip['status']}'")
    
    async with conn.transaction():
        row = await conn.fetchrow(
            """UPDATE app.trips SET status = 'cancelled'
               WHERE id = $1
               RETURNING id, route_id, shift_id, passenger_id, driver_id, pickup_stop_id, dropoff_stop_id,
                         pickup_note, seats_requested, status, payment_method, price_cents, currency, created_at""",
            trip_id
        )
        # Devolver asientos al shift si estaba aceptado
        if trip["status"] == "accepted" and trip["shift_id"]:
            await conn.execute(
                "UPDATE app.driver_shifts SET available_seats = available_seats + $1 WHERE id = $2",
                trip["seats_requested"], trip["shift_id"]
            )
    
    return TripOut(**{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in dict(row).items()})


# ============================================
# ENDPOINTS: Messages
# ============================================
@app.get("/trips/{trip_id}/messages", response_model=List[MessageOut], tags=["Messages"])
async def get_trip_messages(
    trip_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
    since: Optional[datetime] = Query(None),
):
    """Lista mensajes de un viaje."""
    user_id = uuid.UUID(current_user.user_id)
    
    # Verificar acceso
    trip = await conn.fetchrow(
        "SELECT passenger_id, driver_id FROM app.trips WHERE id = $1",
        trip_id
    )
    if not trip:
        raise HTTPException(404, "Viaje no encontrado")
    if trip["passenger_id"] != user_id and trip["driver_id"] != user_id:
        raise HTTPException(403, "No tienes acceso a este viaje")
    
    query = "SELECT id, trip_id, sender_id, message, is_read, created_at FROM app.messages WHERE trip_id = $1"
    params = [trip_id]
    
    if since:
        query += " AND created_at > $2"
        params.append(since)
    
    query += " ORDER BY created_at ASC"
    
    rows = await conn.fetch(query, *params)
    return [
        MessageOut(**{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in dict(r).items()})
        for r in rows
    ]


@app.post("/trips/{trip_id}/messages", response_model=MessageOut, status_code=201, tags=["Messages"])
async def send_message(
    trip_id: uuid.UUID,
    payload: MessageCreate,
    current_user: CurrentUser = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
):
    """Envía un mensaje en un viaje."""
    user_id = uuid.UUID(current_user.user_id)
    
    # Verificar acceso
    trip = await conn.fetchrow(
        "SELECT passenger_id, driver_id FROM app.trips WHERE id = $1",
        trip_id
    )
    if not trip:
        raise HTTPException(404, "Viaje no encontrado")
    if trip["passenger_id"] != user_id and trip["driver_id"] != user_id:
        raise HTTPException(403, "No tienes acceso a este viaje")
    
    row = await conn.fetchrow(
        """INSERT INTO app.messages (trip_id, sender_id, message)
           VALUES ($1, $2, $3)
           RETURNING id, trip_id, sender_id, message, is_read, created_at""",
        trip_id, user_id, payload.message
    )
    return MessageOut(**{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in dict(row).items()})


# ============================================
# Run
# ============================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
