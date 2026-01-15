-- ==============================================
-- RealGo MVP - Schema de Base de Datos
-- ==============================================

-- Extensión para UUID
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Esquema de la app
CREATE SCHEMA IF NOT EXISTS app;

-- Enums
DO $$
BEGIN
  -- Tipo de estado de viaje
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'trip_status') THEN
    CREATE TYPE app.trip_status AS ENUM ('requested','confirmed','started','finished','cancelled');
  END IF;

  -- Método de pago
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'payment_method') THEN
    CREATE TYPE app.payment_method AS ENUM ('cash','yape','plin');
  END IF;

  -- Rol de usuario
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
    CREATE TYPE app.user_role AS ENUM ('passenger','driver','admin');
  END IF;
END$$;

-- Usuarios
CREATE TABLE IF NOT EXISTS app.users (
  id          UUID PRIMARY KEY,  -- ID viene de Better Auth (sub claim)
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

-- Rutas A → B
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

-- Paradas / anexos de ruta
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

-- Viajes / reservas
CREATE TABLE IF NOT EXISTS app.trips (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  route_id         UUID NOT NULL REFERENCES app.routes(id) ON DELETE RESTRICT,
  passenger_id     UUID NOT NULL REFERENCES app.users(id) ON DELETE RESTRICT,
  driver_id        UUID REFERENCES app.users(id) ON DELETE SET NULL,
  pickup_stop_id   UUID REFERENCES app.route_stops(id) ON DELETE SET NULL,
  dropoff_stop_id  UUID REFERENCES app.route_stops(id) ON DELETE SET NULL,
  status           app.trip_status NOT NULL DEFAULT 'requested',
  payment_method   app.payment_method NOT NULL DEFAULT 'cash',
  price_cents      INTEGER NOT NULL DEFAULT 0 CHECK (price_cents >= 0),
  currency         TEXT NOT NULL DEFAULT 'PEN',
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_trips_route ON app.trips(route_id);
CREATE INDEX IF NOT EXISTS idx_trips_passenger ON app.trips(passenger_id);
CREATE INDEX IF NOT EXISTS idx_trips_driver ON app.trips(driver_id);
CREATE INDEX IF NOT EXISTS idx_trips_status ON app.trips(status);

-- ==============================================
-- Migración: Añadir columna role si no existe
-- ==============================================
DO $$
BEGIN
  -- Añadir role si no existe
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_schema = 'app' AND table_name = 'users' AND column_name = 'role'
  ) THEN
    ALTER TABLE app.users ADD COLUMN role app.user_role NOT NULL DEFAULT 'passenger';
  END IF;

  -- Añadir email si no existe
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_schema = 'app' AND table_name = 'users' AND column_name = 'email'
  ) THEN
    ALTER TABLE app.users ADD COLUMN email TEXT UNIQUE;
  END IF;

  -- Añadir driver_id a trips si no existe
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_schema = 'app' AND table_name = 'trips' AND column_name = 'driver_id'
  ) THEN
    ALTER TABLE app.users ADD COLUMN driver_id UUID REFERENCES app.users(id) ON DELETE SET NULL;
  END IF;
END$$;
