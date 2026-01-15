-- Datos de prueba para RealGo MVP

-- Usuario de prueba (hardcoded passenger)
INSERT INTO app.users (id, role, full_name, phone_e164, is_active)
VALUES ('11111111-1111-1111-1111-111111111111', 'passenger', 'Usuario Prueba', '+51999999999', TRUE)
ON CONFLICT (id) DO NOTHING;

-- Ruta de ejemplo: Lima Centro a Miraflores
INSERT INTO app.routes (id, name, origin_name, origin_lat, origin_lon, destination_name, destination_lat, destination_lon, base_price_cents, currency, is_active)
VALUES ('22222222-2222-2222-2222-222222222222', 'Lima Centro - Miraflores', 'Plaza San Martin', -12.0508, -77.0342, 'Parque Kennedy', -12.1191, -77.0311, 500, 'PEN', TRUE)
ON CONFLICT (id) DO NOTHING;

-- Paradas de la ruta
INSERT INTO app.route_stops (id, route_id, stop_order, name, lat, lon, is_active) VALUES
('33333333-3333-3333-3333-333333333331', '22222222-2222-2222-2222-222222222222', 1, 'Plaza San Martin', -12.0508, -77.0342, TRUE),
('33333333-3333-3333-3333-333333333332', '22222222-2222-2222-2222-222222222222', 2, 'Av. Arequipa / Javier Prado', -12.0889, -77.0356, TRUE),
('33333333-3333-3333-3333-333333333333', '22222222-2222-2222-2222-222222222222', 3, 'Ovalo Gutierrez', -12.1078, -77.0328, TRUE),
('33333333-3333-3333-3333-333333333334', '22222222-2222-2222-2222-222222222222', 4, 'Parque Kennedy', -12.1191, -77.0311, TRUE)
ON CONFLICT (id) DO NOTHING;
