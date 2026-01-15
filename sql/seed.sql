-- ==============================================
-- RealGo MVP - Datos de Prueba (Seed)
-- ==============================================

-- Usuario de prueba (hardcoded para MVP)
INSERT INTO app.users (id, full_name, phone_e164)
VALUES (
  '11111111-1111-1111-1111-111111111111',
  'Usuario Demo',
  '+51999888777'
)
ON CONFLICT (id) DO NOTHING;

-- Ruta 1: Hoja Redonda -> Chincha Alta
INSERT INTO app.routes (
  id, name,
  origin_name, origin_lat, origin_lon,
  destination_name, destination_lat, destination_lon,
  base_price_cents, currency
) VALUES (
  '22222222-2222-2222-2222-222222222222',
  'Hoja Redonda → Chincha Alta',
  'Hoja Redonda',  -13.548331, -76.115268,
  'Chincha Alta',  -13.409900, -76.132300,
  600, 'PEN'
)
ON CONFLICT (id) DO NOTHING;

-- Ruta 2: Chincha Alta -> Hoja Redonda
INSERT INTO app.routes (
  id, name,
  origin_name, origin_lat, origin_lon,
  destination_name, destination_lat, destination_lon,
  base_price_cents, currency
) VALUES (
  '33333333-3333-3333-3333-333333333333',
  'Chincha Alta → Hoja Redonda',
  'Chincha Alta',  -13.409900, -76.132300,
  'Hoja Redonda',  -13.548331, -76.115268,
  600, 'PEN'
)
ON CONFLICT (id) DO NOTHING;

-- Anexos / paradas para Ruta 1
INSERT INTO app.route_stops (id, route_id, stop_order, name, lat, lon) VALUES
  ('44444444-4444-4444-4444-444444444444', '22222222-2222-2222-2222-222222222222', 1, 'Hoja Redonda (Inicio)',      -13.548331, -76.115268),
  ('55555555-5555-5555-5555-555555555555', '22222222-2222-2222-2222-222222222222', 2, 'Paradero Intermedio',        -13.479000, -76.123800),
  ('66666666-6666-6666-6666-666666666666', '22222222-2222-2222-2222-222222222222', 3, 'Chincha Alta (Llegada)',     -13.409900, -76.132300)
ON CONFLICT (id) DO NOTHING;

-- Anexos / paradas para Ruta 2 (mismo recorrido al revés)
INSERT INTO app.route_stops (id, route_id, stop_order, name, lat, lon) VALUES
  ('77777777-7777-7777-7777-777777777777', '33333333-3333-3333-3333-333333333333', 1, 'Chincha Alta (Inicio)',      -13.409900, -76.132300),
  ('88888888-8888-8888-8888-888888888888', '33333333-3333-3333-3333-333333333333', 2, 'Paradero Intermedio',        -13.479000, -76.123800),
  ('99999999-9999-9999-9999-999999999999', '33333333-3333-3333-3333-333333333333', 3, 'Hoja Redonda (Llegada)',     -13.548331, -76.115268)
ON CONFLICT (id) DO NOTHING;
