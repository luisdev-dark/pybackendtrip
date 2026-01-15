import asyncio
import os
from dotenv import load_dotenv
import asyncpg

# Cargar variables de entorno
load_dotenv()

async def test_connection():
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    if not DATABASE_URL:
        print("❌ ERROR: DATABASE_URL no está configurada en el archivo .env")
        return False
    
    try:
        print("🔌 Conectando a NeonDB...")
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Probar una consulta simple
        version = await conn.fetchval('SELECT version()')
        print(f"✅ Conexión exitosa!")
        print(f"📊 Versión de PostgreSQL: {version[:50]}...")
        
        # Verificar tablas existentes
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'app'
        """)
        
        if tables:
            print(f"📋 Tablas encontradas en schema 'app': {[t['table_name'] for t in tables]}")
        else:
            print("⚠️  No se encontraron tablas en schema 'app'. Necesitas ejecutar el schema.sql")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_connection())
    if result:
        print("\n✨ La conexión a NeonDB funciona correctamente!")
    else:
        print("\n❌ No se pudo conectar a NeonDB. Verifica tu DATABASE_URL en el archivo .env")
