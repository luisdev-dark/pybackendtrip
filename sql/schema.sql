-- Extensión para UUID
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Esquema de la app
CREATE SCHEMA IF NOT EXISTS app;

-- Enums simples
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'trip_status') THEN
    CREATE TYPE app.trip_status AS ENUM ('requested','started','finished','cancelled');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'payment_method') THEN
    CREATE TYPE app.payment_method AS ENUM ('cash','yape','plin');
  END IF;
END$$;

-- Usuarios (solo passenger por ahora)
CREATE TABLE IF NOT EXISTS app.users (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  full_name   TEXT NOT NULL,
  phone_e164  TEXT NOT NULL UNIQUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

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

-- Paradas / anexos (incluye si quieres origen/destino)
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
  pickup_stop_id   UUID NULL REFERENCES app.route_stops(id) ON DELETE SET NULL,
  dropoff_stop_id  UUID NULL REFERENCES app.route_stops(id) ON DELETE SET NULL,
  status           app.trip_status NOT NULL DEFAULT 'requested',
  payment_method   app.payment_method NOT NULL DEFAULT 'cash',
  price_cents      INTEGER NOT NULL DEFAULT 0 CHECK (price_cents >= 0),
  currency         TEXT NOT NULL DEFAULT 'PEN',
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_trips_route ON app.trips(route_id);
CREATE INDEX IF NOT EXISTS idx_trips_passenger ON app.trips(passenger_id);
