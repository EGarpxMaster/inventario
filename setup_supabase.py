import os
import json
from dotenv import load_dotenv
from db_client import DatabaseClient

load_dotenv()

def verify_and_seed_supabase():
    print(" Verificando conexión a Supabase...")
    db = DatabaseClient()
    
    if not db.use_supabase:
        print("⚠️ No se pudo conectar a Supabase. Revisa SUPABASE_URL y SUPABASE_KEY en el archivo .env.")
        return False

    try:
        # Intentar consultar la tabla inventario
        res = db.client.table("inventario").select("*").limit(1).execute()
        print(" Conexión exitosa a la tabla 'inventario' en Supabase.")
        
        # Consultar total de registros
        res_all = db.client.table("inventario").select("id").execute()
        total_items = len(res_all.data)
        print(f" Cantidad de productos en Supabase actualmente: {total_items}")

        if total_items == 0:
            print("🌱 Sembrando los 46 productos iniciales desde el archivo Excel...")
            seed_path = os.path.join(os.path.dirname(__file__), "initial_seed.json")
            if os.path.exists(seed_path):
                with open(seed_path, 'r', encoding='utf-8') as f:
                    items = json.load(f)
                
                count = 0
                for item in items:
                    db.client.table("inventario").insert(item).execute()
                    count += 1
                print(f" ¡Se poblaron los {count} productos exitosamente en Supabase!")
        return True

    except Exception as e:
        err_msg = str(e)
        if "PGRST205" in err_msg or "Could not find the table" in err_msg:
            print("\n❌ La tabla 'public.inventario' aún no ha sido creada en tu base de datos de Supabase.")
            print("\n Para crear la tabla en 1 minuto:")
            print("1. Inicia sesión en https://supabase.com y abre tu proyecto (mglyddymxhxovpftimwy).")
            print("2. En el menú lateral izquierdo, haz clic en 'SQL Editor'.")
            print("3. Pega y ejecuta las siguientes instrucciones (o el contenido de schema.sql):\n")
            print("-" * 60)
            with open("schema.sql", "r", encoding="utf-8") as sf:
                print(sf.read())
            print("-" * 60)
            print("\n4. Vuelve a ejecutar este script (`python3 setup_supabase.py`) para sembrar los productos automáticamente.")
        else:
            print(f"❌ Error al consultar Supabase: {e}")
        return False

if __name__ == "__main__":
    verify_and_seed_supabase()
