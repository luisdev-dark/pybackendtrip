import os
from dotenv import load_dotenv

print("🔍 Verificando archivo .env...")

# Cargar variables de entorno
load_dotenv()

database_url = os.getenv("DATABASE_URL")

if database_url:
    print(f"✅ DATABASE_URL encontrada: {database_url[:50]}...")
else:
    print("❌ DATABASE_URL NO encontrada")
    print("\nPor favor, verifica que el archivo .env tenga EXACTAMENTE esta línea:")
    print("DATABASE_URL=postgresql://neondb_owner:npg_OqKmI6jA4HsL@ep-silent-glitter-ahbjd2ux-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")
