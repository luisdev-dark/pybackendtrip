-- ==============================================
-- RealGo MVP+ - Schema de Base de Datos
-- Sistema de Colectivos Completo
-- ==============================================

-- Extensión para UUID
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Esquema de la app
CREATE SCHEMA IF NOT EXISTS app;

-- ==============================================
-- ENUMS
-- ==============================================
DO $$
BEGIN
  -- Rol de usuario
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
    CREATE TYPE app.user_role AS ENUM ('passenger', 'driver', 'admin');
  END IF;

  -- Estado del viaje/pedido
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'trip_status') THEN
    CREATE TYPE app.trip_status AS ENUM (
      'requested',   -- Pasajero solicitó
      'accepted',    -- Conductor aceptó
      'rejected',    -- Conductor rechazó
      'onboard',     -- Pasajero a bordo
      'completed',   -- Viaje terminado
      'cancelled'    -- Cancelado
    );
  ELSE
    -- Añadir nuevos valores si no existen
    BEGIN
      ALTER TYPE app.trip_status ADD VALUE IF NOT EXISTS 'accepted';
      ALTER TYPE app.trip_status ADD VALUE IF NOT EXISTS 'rejected';
      ALTER TYPE app.trip_status ADD VALUE IF NOT EXISTS 'onboard';
      ALTER TYPE app.trip_status ADD VALUE IF NOT EXISTS 'completed';
    EXCEPTION WHEN duplicate_object THEN NULL;
    END;
  END IF;

  -- Estado del turno/shift del conductor
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'shift_status') THEN
    CREATE TYPE app.shift_status AS ENUM ('open', 'closed', 'completed');
  END IF;

  -- Método de pago
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'payment_method') THEN
    CREATE TYPE app.payment_method AS ENUM ('cash', 'yape', 'plin');
  END IF;
END$$;

-- ==============================================
-- USUARIOS
-- ==============================================
CREATE TABLE IF NOT EXISTS app.users (
  id          UUID PRIMARY KEY,
  email       TEXT UNIQUE,
  full_name   TEXT,
  phone_e164  TEXT UNIQUE,
  role        app.user_role NOT NULL DEFAULT 'passenger',
  is_active   BOOLEAN NOT NULL DEFAULT TRUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON app.users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON app.users(role);

-- ==============================================
-- VEHÍCULOS
-- ==============================================
CREATE TABLE IF NOT EXISTS app.vehicles (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id        UUID NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
  plate           TEXT NOT NULL UNIQUE,
  brand           TEXT,
  model           TEXT,
  color           TEXT,
  year            INTEGER,
  total_seats     INTEGER NOT NULL DEFAULT 4 CHECK (total_seats >= 1 AND total_seats <= 20),
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_vehicles_owner ON app.vehicles(owner_id);
CREATE INDEX IF NOT EXISTS idx_vehicles_plate ON app.vehicles(plate);

-- ==============================================
-- CONDUCTORES (info extra del driver)
-- ==============================================
CREATE TABLE IF NOT EXISTS app.drivers (
  user_id           UUID PRIMARY KEY REFERENCES app.users(id) ON DELETE CASCADE,
  license_number    TEXT,
  license_expiry    DATE,
  default_vehicle_id UUID REFERENCES app.vehicles(id) ON DELETE SET NULL,
  rating            DECIMAL(3,2) DEFAULT 5.00,
  total_trips       INTEGER DEFAULT 0,
  is_verified       BOOLEAN NOT NULL DEFAULT FALSE,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ==============================================
-- RUTAS
-- ==============================================
CREATE TABLE IF NOT EXISTS app.routes (
  id                 UUID PRIMARY KEY,
  name               TEXT NOT NULL,
  origin_name        TEXT NOT NULL,
  origin_lat         DOUBLE PRECISION NOT NULL,
  origin_lon         DOUBLE PRECISION NOT NULL,
  destination_name   TEXT NOT NULL,
  destination_lat    DOUBLE PRECISION NOT NULL,
  destination_lon    DOUBLE PRECISION NOT NULL,
  base_price_cents   INTEGER NOT NULL DEFAULT 0 CHECK (base_price_cents >= 0),
  currency           TEXT NOT NULL DEFAULT 'PEN',
  is_active          BOOLEAN NOT NULL DEFAULT TRUE,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_routes_active ON app.routes(is_active);

-- ==============================================
-- PARADAS DE RUTA
-- ==============================================
CREATE TABLE IF NOT EXISTS app.route_stops (
  id          UUID PRIMARY KEY,
  route_id    UUID NOT NULL REFERENCES app.routes(id) ON DELETE CASCADE,
  stop_order  INTEGER NOT NULL CHECK (stop_order >= 1),
  name        TEXT NOT NULL,
  lat         DOUBLE PRECISION NOT NULL,
  lon         DOUBLE PRECISION NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_route_stops_route ON app.route_stops(route_id);

-- ==============================================
-- TURNOS/SHIFTS (Viaje activo del conductor)
-- ==============================================
CREATE TABLE IF NOT EXISTS app.driver_shifts (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  driver_id         UUID NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
  vehicle_id        UUID REFERENCES app.vehicles(id) ON DELETE SET NULL,
  route_id          UUID NOT NULL REFERENCES app.routes(id) ON DELETE CASCADE,
  status            app.shift_status NOT NULL DEFAULT 'open',
  total_seats       INTEGER NOT NULL DEFAULT 4 CHECK (total_seats >= 1),
  available_seats   INTEGER NOT NULL DEFAULT 4 CHECK (available_seats >= 0),
  starts_at         TIMESTAMPTZ,
  ends_at           TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  
  CONSTRAINT available_seats_check CHECK (available_seats <= total_seats)
);

CREATE INDEX IF NOT EXISTS idx_shifts_driver ON app.driver_shifts(driver_id);
CREATE INDEX IF NOT EXISTS idx_shifts_route ON app.driver_shifts(route_id);
CREATE INDEX IF NOT EXISTS idx_shifts_status ON app.driver_shifts(status);
CREATE INDEX IF NOT EXISTS idx_shifts_open ON app.driver_shifts(route_id, status) WHERE status = 'open';

-- ==============================================
-- VIAJES/PEDIDOS (Trips)
-- ==============================================
CREATE TABLE IF NOT EXISTS app.trips (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  route_id         UUID NOT NULL REFERENCES app.routes(id) ON DELETE RESTRICT,
  shift_id         UUID REFERENCES app.driver_shifts(id) ON DELETE SET NULL,
  passenger_id     UUID NOT NULL REFERENCES app.users(id) ON DELETE RESTRICT,
  driver_id        UUID REFERENCES app.users(id) ON DELETE SET NULL,
  pickup_stop_id   UUID REFERENCES app.route_stops(id) ON DELETE SET NULL,
  dropoff_stop_id  UUID REFERENCES app.route_stops(id) ON DELETE SET NULL,
  pickup_note      TEXT,  -- "Estoy frente a la farmacia"
  seats_requested  INTEGER NOT NULL DEFAULT 1 CHECK (seats_requested >= 1 AND seats_requested <= 10),
  status           app.trip_status NOT NULL DEFAULT 'requested',
  payment_method   app.payment_method NOT NULL DEFAULT 'cash',
  price_cents      INTEGER NOT NULL DEFAULT 0 CHECK (price_cents >= 0),
  currency         TEXT NOT NULL DEFAULT 'PEN',
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_trips_route ON app.trips(route_id);
CREATE INDEX IF NOT EXISTS idx_trips_shift ON app.trips(shift_id);
CREATE INDEX IF NOT EXISTS idx_trips_passenger ON app.trips(passenger_id);
CREATE INDEX IF NOT EXISTS idx_trips_driver ON app.trips(driver_id);
CREATE INDEX IF NOT EXISTS idx_trips_status ON app.trips(status);

-- ==============================================
-- MENSAJES (Chat simple trip)
-- ==============================================
CREATE TABLE IF NOT EXISTS app.messages (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trip_id       UUID NOT NULL REFERENCES app.trips(id) ON DELETE CASCADE,
  sender_id     UUID NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
  message       TEXT NOT NULL,
  is_read       BOOLEAN NOT NULL DEFAULT FALSE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_trip ON app.messages(trip_id);
CREATE INDEX IF NOT EXISTS idx_messages_sender ON app.messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON app.messages(trip_id, created_at);

-- ==============================================
-- FUNCIONES ÚTILES
-- ==============================================

-- Función para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION app.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers para updated_at
DO $$
DECLARE
  t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY['users', 'vehicles', 'drivers', 'routes', 'driver_shifts', 'trips']
  LOOP
    EXECUTE format('
      DROP TRIGGER IF EXISTS trigger_update_%I ON app.%I;
      CREATE TRIGGER trigger_update_%I
        BEFORE UPDATE ON app.%I
        FOR EACH ROW
        EXECUTE FUNCTION app.update_updated_at();
    ', t, t, t, t);
  END LOOP;
END$$;
