-- Schema para RealGo MVP
CREATE SCHEMA IF NOT EXISTS app;

-- Enum types
CREATE TYPE app.user_role AS ENUM ('passenger', 'driver', 'admin');
CREATE TYPE app.trip_status AS ENUM ('requested', 'confirmed', 'started', 'finished', 'cancelled');
CREATE TYPE app.payment_method AS ENUM ('cash', 'yape', 'plin');

-- Users table
CREATE TABLE app.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role app.user_role NOT NULL DEFAULT 'passenger',
    full_name VARCHAR NOT NULL,
    phone_e164 VARCHAR NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- Routes table
CREATE TABLE app.routes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL,
    origin_name VARCHAR NOT NULL,
    origin_lat DOUBLE PRECISION NOT NULL,
    origin_lon DOUBLE PRECISION NOT NULL,
    destination_name VARCHAR NOT NULL,
    destination_lat DOUBLE PRECISION NOT NULL,
    destination_lon DOUBLE PRECISION NOT NULL,
    base_price_cents INTEGER NOT NULL DEFAULT 0,
    currency VARCHAR(3) NOT NULL DEFAULT 'PEN',
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- Route stops table
CREATE TABLE app.route_stops (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    route_id UUID NOT NULL REFERENCES app.routes(id),
    stop_order INTEGER NOT NULL,
    name VARCHAR NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- Trips table
CREATE TABLE app.trips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    route_id UUID NOT NULL REFERENCES app.routes(id),
    passenger_id UUID NOT NULL REFERENCES app.users(id),
    pickup_stop_id UUID REFERENCES app.route_stops(id),
    dropoff_stop_id UUID REFERENCES app.route_stops(id),
    status app.trip_status NOT NULL DEFAULT 'requested',
    payment_method app.payment_method NOT NULL DEFAULT 'cash',
    price_cents INTEGER NOT NULL DEFAULT 0,
    currency VARCHAR(3) NOT NULL DEFAULT 'PEN',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
