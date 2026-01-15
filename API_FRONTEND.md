# 📱 RealGo API - Documentación para Frontend

## 🔗 URLs Base

```
Producción: https://pybackendtrip.onrender.com
Documentación: https://pybackendtrip.onrender.com/docs
```

---

## 🔐 Autenticación

### Cómo funciona
1. El frontend **autentica al usuario con Neon Auth**
2. Neon Auth devuelve un **JWT token**
3. El frontend envía ese token en **cada petición** al backend

### Header de Autorización
```
Authorization: Bearer <JWT_TOKEN>
```

### Ejemplo en JavaScript/React Native:
```javascript
const API_URL = 'https://pybackendtrip.onrender.com';

async function apiCall(endpoint, options = {}) {
  const token = await getAuthToken(); // Obtener de Neon Auth
  
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...options.headers,
    },
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Error en la petición');
  }
  
  return response.json();
}
```

---

## 📋 Endpoints Disponibles

### 🏥 Health (Público)
| Método | Endpoint | Auth | Descripción |
|--------|----------|:----:|-------------|
| `GET` | `/health` | ❌ | Estado del servicio |

**Response:**
```json
{
  "status": "ok",
  "service": "realgo-mvp-plus",
  "version": "0.4.0"
}
```

---

### 👤 Usuario / Auth
| Método | Endpoint | Auth | Descripción |
|--------|----------|:----:|-------------|
| `POST` | `/me/sync` | ✅ | Crear/actualizar usuario |
| `GET` | `/me` | ✅ | Obtener mi perfil |

#### POST /me/sync
**Cuándo usar:** Después del login con Neon Auth, para registrar al usuario en nuestra BD.

**Request:**
```json
{
  "role": "passenger",  // o "driver"
  "full_name": "Juan Pérez",
  "phone_e164": "+51999888777"
}
```

**Response:**
```json
{
  "id": "uuid-del-usuario",
  "email": "juan@email.com",
  "full_name": "Juan Pérez",
  "phone_e164": "+51999888777",
  "role": "passenger",
  "is_active": true
}
```

---

### 🗺️ Rutas (Público)
| Método | Endpoint | Auth | Descripción |
|--------|----------|:----:|-------------|
| `GET` | `/routes` | ❌ | Lista de rutas activas |
| `GET` | `/routes/{id}` | ❌ | Detalle de ruta con paradas |

#### GET /routes
**Response:**
```json
[
  {
    "id": "22222222-2222-2222-2222-222222222222",
    "name": "Hoja Redonda → Chincha Alta",
    "origin_name": "Hoja Redonda",
    "destination_name": "Chincha Alta",
    "base_price_cents": 600,
    "currency": "PEN"
  }
]
```

#### GET /routes/{route_id}
**Response:**
```json
{
  "route": {
    "id": "22222222-...",
    "name": "Hoja Redonda → Chincha Alta",
    "origin_name": "Hoja Redonda",
    "destination_name": "Chincha Alta",
    "base_price_cents": 600,
    "currency": "PEN"
  },
  "stops": [
    {"id": "44444444-...", "name": "Hoja Redonda (Inicio)", "stop_order": 1},
    {"id": "55555555-...", "name": "Paradero Intermedio", "stop_order": 2},
    {"id": "66666666-...", "name": "Chincha Alta (Llegada)", "stop_order": 3}
  ]
}
```

---

### 🎫 Viajes (Pasajero)
| Método | Endpoint | Auth | Descripción |
|--------|----------|:----:|-------------|
| `POST` | `/trips` | ✅ | Solicitar viaje |
| `GET` | `/trips/{id}` | ✅ | Ver estado de viaje |
| `GET` | `/my/trips` | ✅ | Mis viajes |
| `POST` | `/trips/{id}/cancel` | ✅ | Cancelar viaje |

#### POST /trips
**Request:**
```json
{
  "route_id": "22222222-2222-2222-2222-222222222222",
  "pickup_stop_id": "44444444-4444-4444-4444-444444444444",  // opcional
  "dropoff_stop_id": "66666666-6666-6666-6666-666666666666", // opcional
  "pickup_note": "Estoy frente a la farmacia",  // opcional
  "seats_requested": 2,  // default: 1
  "payment_method": "yape"  // cash | yape | plin
}
```

**Response (201):**
```json
{
  "id": "trip-uuid",
  "route_id": "22222222-...",
  "shift_id": "shift-uuid",
  "passenger_id": "my-user-id",
  "driver_id": null,
  "pickup_stop_id": "44444444-...",
  "dropoff_stop_id": "66666666-...",
  "pickup_note": "Estoy frente a la farmacia",
  "seats_requested": 2,
  "status": "requested",
  "payment_method": "yape",
  "price_cents": 1200,
  "currency": "PEN",
  "created_at": "2024-01-15T03:00:00Z"
}
```

**Error (409):**
```json
{
  "detail": "No hay unidades disponibles en esta ruta"
}
```

#### Estados de Trip (status)
| Estado | Descripción |
|--------|-------------|
| `requested` | Pasajero solicitó, esperando conductor |
| `accepted` | Conductor aceptó |
| `rejected` | Conductor rechazó |
| `onboard` | Pasajero abordó el vehículo |
| `completed` | Viaje terminado |
| `cancelled` | Cancelado |

---

### 💬 Mensajes
| Método | Endpoint | Auth | Descripción |
|--------|----------|:----:|-------------|
| `GET` | `/trips/{id}/messages` | ✅ | Ver mensajes |
| `POST` | `/trips/{id}/messages` | ✅ | Enviar mensaje |

#### POST /trips/{trip_id}/messages
**Request:**
```json
{
  "message": "Ya estoy llegando a la parada"
}
```

#### GET /trips/{trip_id}/messages?since=2024-01-15T03:00:00Z
**Response:**
```json
[
  {
    "id": "msg-uuid",
    "trip_id": "trip-uuid",
    "sender_id": "user-uuid",
    "message": "Ya estoy llegando",
    "is_read": false,
    "created_at": "2024-01-15T03:05:00Z"
  }
]
```

---

### 🚗 Conductor - Vehículos
| Método | Endpoint | Auth | Rol | Descripción |
|--------|----------|:----:|:---:|-------------|
| `POST` | `/driver/vehicles` | ✅ | driver | Registrar vehículo |
| `GET` | `/driver/vehicles` | ✅ | driver | Mis vehículos |

#### POST /driver/vehicles
**Request:**
```json
{
  "plate": "ABC-123",
  "brand": "Toyota",
  "model": "Hiace",
  "color": "Blanco",
  "year": 2020,
  "total_seats": 10
}
```

---

### 🚗 Conductor - Turnos (Shifts)
| Método | Endpoint | Auth | Rol | Descripción |
|--------|----------|:----:|:---:|-------------|
| `POST` | `/driver/shifts` | ✅ | driver | Abrir turno |
| `GET` | `/driver/shifts/current` | ✅ | driver | Mi turno activo |
| `POST` | `/driver/shifts/{id}/close` | ✅ | driver | Cerrar turno |

#### POST /driver/shifts
**Request:**
```json
{
  "route_id": "22222222-2222-2222-2222-222222222222",
  "vehicle_id": "bbbbbbbb-...",  // opcional
  "total_seats": 4
}
```

**Response:**
```json
{
  "id": "shift-uuid",
  "driver_id": "my-user-id",
  "route_id": "22222222-...",
  "vehicle_id": null,
  "status": "open",
  "total_seats": 4,
  "available_seats": 4,
  "starts_at": "2024-01-15T03:00:00Z",
  "created_at": "2024-01-15T03:00:00Z"
}
```

---

### 🚗 Conductor - Gestión de Pedidos
| Método | Endpoint | Auth | Rol | Descripción |
|--------|----------|:----:|:---:|-------------|
| `GET` | `/driver/requests` | ✅ | driver | Ver pedidos pendientes |
| `POST` | `/driver/trips/{id}/accept` | ✅ | driver | Aceptar pedido |
| `POST` | `/driver/trips/{id}/reject` | ✅ | driver | Rechazar pedido |
| `POST` | `/driver/trips/{id}/onboard` | ✅ | driver | Pasajero abordó |
| `POST` | `/driver/trips/{id}/complete` | ✅ | driver | Viaje completado |

#### GET /driver/requests?since=2024-01-15T03:00:00Z
**Response:**
```json
[
  {
    "id": "trip-uuid",
    "route_id": "22222222-...",
    "passenger_id": "passenger-uuid",
    "pickup_stop_id": "44444444-...",
    "pickup_note": "Frente a la farmacia",
    "seats_requested": 2,
    "status": "requested",
    "payment_method": "yape",
    "price_cents": 1200,
    "passenger_name": "Juan Pérez",
    "passenger_phone": "+51999888777",
    "created_at": "2024-01-15T03:00:00Z"
  }
]
```

---

## 📱 Flujos de Implementación

### Flujo Pasajero

```
1. Login con Neon Auth → Obtener JWT
2. POST /me/sync { role: "passenger" } → Registrar en BD
3. GET /routes → Mostrar rutas disponibles
4. POST /trips → Solicitar viaje
5. Polling: GET /trips/{id} cada 5 segundos → Ver cambios de estado
6. Si status == "accepted" → Mostrar info del conductor
7. POST /trips/{id}/messages → Chat con conductor
```

### Flujo Conductor

```
1. Login con Neon Auth → Obtener JWT
2. POST /me/sync { role: "driver" } → Registrar como conductor
3. POST /driver/vehicles → Registrar vehículo (una vez)
4. POST /driver/shifts → Abrir turno en ruta
5. Polling: GET /driver/requests cada 3 segundos → Ver pedidos
6. POST /driver/trips/{id}/accept → Aceptar pasajero
7. POST /driver/trips/{id}/onboard → Marcar que abordó
8. POST /driver/trips/{id}/complete → Terminar viaje
9. POST /driver/shifts/{id}/close → Cerrar turno
```

---

## ⚠️ Códigos de Error Comunes

| Código | Significado |
|--------|-------------|
| `400` | Bad Request - Datos inválidos |
| `401` | Unauthorized - Token inválido o expirado |
| `403` | Forbidden - No tienes permiso (rol incorrecto) |
| `404` | Not Found - Recurso no existe |
| `409` | Conflict - No hay unidades disponibles |
| `500` | Server Error - Error interno |

---

## 🔄 Polling (Notificaciones MVP)

Ya que no hay websockets, usar polling:

```javascript
// Pasajero: verificar estado del viaje
useEffect(() => {
  const interval = setInterval(async () => {
    const trip = await apiCall(`/trips/${tripId}`);
    setTripStatus(trip.status);
    
    if (['completed', 'cancelled', 'rejected'].includes(trip.status)) {
      clearInterval(interval);
    }
  }, 5000); // cada 5 segundos
  
  return () => clearInterval(interval);
}, [tripId]);

// Conductor: verificar nuevos pedidos
useEffect(() => {
  let lastCheck = new Date().toISOString();
  
  const interval = setInterval(async () => {
    const requests = await apiCall(`/driver/requests?since=${lastCheck}`);
    if (requests.length > 0) {
      // Notificar nuevos pedidos
      setNewRequests(prev => [...prev, ...requests]);
    }
    lastCheck = new Date().toISOString();
  }, 3000); // cada 3 segundos
  
  return () => clearInterval(interval);
}, []);
```

---

## 📦 Ejemplo Completo: Crear Viaje

```javascript
async function createTrip(routeId, pickupNote, seats, paymentMethod) {
  try {
    const trip = await apiCall('/trips', {
      method: 'POST',
      body: JSON.stringify({
        route_id: routeId,
        pickup_note: pickupNote,
        seats_requested: seats,
        payment_method: paymentMethod
      })
    });
    
    console.log('Viaje creado:', trip.id);
    console.log('Estado:', trip.status); // "requested"
    console.log('Precio:', trip.price_cents / 100, trip.currency); // "12 PEN"
    
    return trip;
  } catch (error) {
    if (error.message.includes('No hay unidades')) {
      // Mostrar mensaje: "No hay colectivos disponibles ahora"
    }
    throw error;
  }
}
```

---

## 🔑 Variables de Entorno Frontend

```env
# API Backend
EXPO_PUBLIC_API_URL=https://pybackendtrip.onrender.com

# Neon Auth
EXPO_PUBLIC_NEON_AUTH_URL=https://ep-silent-glitter-ahbjd2ux.neonauth.c-3.us-east-1.aws.neon.tech/neondb/auth
```

---

**¿Preguntas? ¡El Swagger está disponible en `/docs` para probar!**
