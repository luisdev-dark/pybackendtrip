-- ==============================================
-- RealGo MVP+ - Migración desde MVP a MVP+
-- Ejecutar en Neon SQL Editor
-- ==============================================

-- 1. Nuevos ENUMs
DO $$
BEGIN
  -- Estado del turno/shift del conductor
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'shift_status') THEN
    CREATE TYPE app.shift_status AS ENUM ('open', 'closed', 'completed');
  END IF;

  -- Añadir nuevos valores a trip_status
  BEGIN
    ALTER TYPE app.trip_status ADD VALUE IF NOT EXISTS 'accepted';
  EXCEPTION WHEN duplicate_object THEN NULL;
  END;
  BEGIN
    ALTER TYPE app.trip_status ADD VALUE IF NOT EXISTS 'rejected';
  EXCEPTION WHEN duplicate_object THEN NULL;
  END;
  BEGIN
    ALTER TYPE app.trip_status ADD VALUE IF NOT EXISTS 'onboard';
  EXCEPTION WHEN duplicate_object THEN NULL;
  END;
  BEGIN
    ALTER TYPE app.trip_status ADD VALUE IF NOT EXISTS 'completed';
  EXCEPTION WHEN duplicate_object THEN NULL;
  END;
END$$;

-- 2. Tabla VEHICLES
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

-- 3. Tabla DRIVERS
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

-- 4. Tabla DRIVER_SHIFTS
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
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_shifts_driver ON app.driver_shifts(driver_id);
CREATE INDEX IF NOT EXISTS idx_shifts_route ON app.driver_shifts(route_id);
CREATE INDEX IF NOT EXISTS idx_shifts_status ON app.driver_shifts(status);

-- 5. Tabla MESSAGES
CREATE TABLE IF NOT EXISTS app.messages (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trip_id       UUID NOT NULL REFERENCES app.trips(id) ON DELETE CASCADE,
  sender_id     UUID NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
  message       TEXT NOT NULL,
  is_read       BOOLEAN NOT NULL DEFAULT FALSE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_trip ON app.messages(trip_id);

-- 6. Añadir columnas a TRIPS
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'app' AND table_name = 'trips' AND column_name = 'shift_id') THEN
    ALTER TABLE app.trips ADD COLUMN shift_id UUID REFERENCES app.driver_shifts(id) ON DELETE SET NULL;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'app' AND table_name = 'trips' AND column_name = 'pickup_note') THEN
    ALTER TABLE app.trips ADD COLUMN pickup_note TEXT;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'app' AND table_name = 'trips' AND column_name = 'seats_requested') THEN
    ALTER TABLE app.trips ADD COLUMN seats_requested INTEGER NOT NULL DEFAULT 1;
  END IF;
END$$;

-- Índices adicionales
CREATE INDEX IF NOT EXISTS idx_trips_shift ON app.trips(shift_id);

SELECT 'Migración completada exitosamente!' as resultado;
