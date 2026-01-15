import asyncio
import os
from dotenv import load_dotenv
import asyncpg

# Cargar variables de entorno
load_dotenv()

async def check_and_seed():
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    try:
        print("🔌 Conectando a NeonDB...")
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Verificar usuarios
        users_count = await conn.fetchval("SELECT COUNT(*) FROM app.users")
        print(f"👤 Usuarios en BD: {users_count}")
        
        # Verificar rutas
        routes = await conn.fetch("SELECT id, name, origin_name, destination_name FROM app.routes")
        print(f"🛣️  Rutas en BD: {len(routes)}")
        for route in routes:
            print(f"   - {route['name']}: {route['origin_name']} → {route['destination_name']}")
        
        # Verificar paradas
        stops_count = await conn.fetchval("SELECT COUNT(*) FROM app.route_stops")
        print(f"📍 Paradas en BD: {stops_count}")
        
        # Verificar viajes
        trips_count = await conn.fetchval("SELECT COUNT(*) FROM app.trips")
        print(f"🚗 Viajes en BD: {trips_count}")
        
        # Si no hay datos, ejecutar seed
        if users_count == 0 or len(routes) == 0:
            print("\n⚠️  No se encontraron datos de prueba. Ejecutando seed.sql...")
            
            with open('sql/seed.sql', 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # Ejecutar cada statement
            statements = [s.strip() for s in sql_content.split(';') if s.strip()]
            for stmt in statements:
                if stmt:
                    try:
                        await conn.execute(stmt)
                    except Exception as e:
                        if "already exists" not in str(e):
                            print(f"⚠️  Advertencia: {e}")
            
            print("✅ Seed ejecutado correctamente!")
            
            # Verificar nuevamente
            users_count = await conn.fetchval("SELECT COUNT(*) FROM app.users")
            routes = await conn.fetch("SELECT id, name FROM app.routes")
            print(f"\n📊 Después del seed:")
            print(f"   👤 Usuarios: {users_count}")
            print(f"   🛣️  Rutas: {len(routes)}")
        else:
            print("\n✅ Los datos de prueba ya existen en la base de datos.")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(check_and_seed())
    if result:
        print("\n✨ Base de datos lista para usar!")
    else:
        print("\n❌ Error al verificar/configurar la base de datos")
