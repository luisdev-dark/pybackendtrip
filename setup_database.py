import asyncio
import os
from dotenv import load_dotenv
import asyncpg

# Cargar variables de entorno
load_dotenv()

async def execute_sql_file(conn, file_path):
    """Ejecuta un archivo SQL en la base de datos"""
    with open(file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Dividir el SQL por punto y coma para ejecutar cada statement
    statements = [s.strip() for s in sql_content.split(';

Assistant: Primero, necesito verificar si el archivo .env está configurado correctamente. El usuario mencionó que lo configuró, pero antes vimos que tenía el comando psql incluido. Ahora que lo corregí, necesito probar la conexión.

El script test_db_connection.py debería funcionar ahora.

Después de probar la conexión, si funciona, puedo ejecutar el schema.sql y seed.sql en la base de datos.

Para ejecutar SQL en NeonDB, puedo usar psql con la URL.

El comando sería: psql $DATABASE_URL -f sql/schema.sql

Pero primero, necesito probar la conexión.

El script ya lo hace, así que ejecutémoslo.<execute_command>
<command>python test_db_connection.py</command>
</execute_command>
