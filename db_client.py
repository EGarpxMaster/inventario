import os
import json
import sqlite3
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables del archivo .env
load_dotenv()

# Intentar importar Supabase
try:
    from supabase import create_client, Client
    HAS_SUPABASE_LIB = True
except ImportError:
    HAS_SUPABASE_LIB = False

def get_config_var(key, default=""):
    """Obtiene variables desde st.secrets, .env o variables de entorno del sistema."""
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    
    val = os.environ.get(key)
    if val:
        return val

    # Mapeos alternativos de claves
    if key == "SUPABASE_KEY":
        return os.environ.get("SUPABASE_SECRET_KEY") or os.environ.get("SUPABASE_PUBLISHABLE_KEY") or default
    return default

class DatabaseClient:
    def __init__(self):
        self.supabase_url = get_config_var("SUPABASE_URL")
        self.supabase_key = get_config_var("SUPABASE_KEY")
        self.use_supabase = False
        self.client = None
        self.db_path = os.path.join(os.path.dirname(__file__), "inventario_local.db")

        if HAS_SUPABASE_LIB and self.supabase_url and self.supabase_key and "tu-proyecto" not in self.supabase_url:
            try:
                self.client = create_client(self.supabase_url, self.supabase_key)
                self.use_supabase = True
                print(" Conectado a Supabase correctamente.")
            except Exception as e:
                print(f" Error conectando a Supabase ({e}). Usando modo local SQLite.")

        if not self.use_supabase:
            self._init_local_db()

    def _init_local_db(self):
        """Inicializa la base de datos local SQLite con initial_seed.json si no existe."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventario (
                id TEXT PRIMARY KEY,
                categoria TEXT NOT NULL,
                concepto TEXT NOT NULL,
                stock_ideal REAL DEFAULT 1.0,
                stock_actual REAL DEFAULT 0.0,
                unidad_medida TEXT DEFAULT 'PZA',
                estatus TEXT DEFAULT 'HAY EN CASA',
                notas TEXT DEFAULT '',
                updated_at TEXT
            )
        """)
        conn.commit()

        # Verificar si hay registros
        cursor.execute("SELECT COUNT(*) FROM inventario")
        count = cursor.fetchone()[0]

        if count == 0:
            seed_path = os.path.join(os.path.dirname(__file__), "initial_seed.json")
            if os.path.exists(seed_path):
                with open(seed_path, 'r', encoding='utf-8') as f:
                    items = json.load(f)
                import uuid
                for item in items:
                    cursor.execute("""
                        INSERT INTO inventario (id, categoria, concepto, stock_ideal, stock_actual, unidad_medida, estatus, notas, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(uuid.uuid4()),
                        item.get("categoria", "General"),
                        item.get("concepto", ""),
                        item.get("stock_ideal", 1.0),
                        item.get("stock_actual", 0.0),
                        item.get("unidad_medida", "PZA"),
                        item.get("estatus", "PENDIENTE"),
                        item.get("notas", ""),
                        item.get("updated_at", datetime.now().isoformat())
                    ))
                conn.commit()
                print(f" Base de datos SQLite local sembrada con {len(items)} productos iniciales.")
        conn.close()

    def get_all_items(self) -> pd.DataFrame:
        """Retorna todos los ítems como un DataFrame de Pandas."""
        if self.use_supabase:
            try:
                res = self.client.table("inventario").select("*").order("categoria").execute()
                df = pd.DataFrame(res.data)
                return df if not df.empty else pd.DataFrame()
            except Exception as e:
                print(f"Error consultando Supabase: {e}")
                return pd.DataFrame()
        else:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query("SELECT * FROM inventario ORDER BY categoria, concepto", conn)
            conn.close()
            return df

    def update_item(self, item_id: str, updates: dict) -> bool:
        """Actualiza las propiedades de un producto existente."""
        updates["updated_at"] = datetime.now().isoformat()
        if self.use_supabase:
            try:
                self.client.table("inventario").update(updates).eq("id", item_id).execute()
                return True
            except Exception as e:
                print(f"Error actualizando en Supabase: {e}")
                return False
        else:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            set_clauses = [f"{k} = ?" for k in updates.keys()]
            values = list(updates.values()) + [item_id]
            sql = f"UPDATE inventario SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(sql, values)
            conn.commit()
            conn.close()
            return True

    def add_item(self, item_data: dict) -> bool:
        """Agrega un nuevo producto al inventario."""
        item_data["updated_at"] = datetime.now().isoformat()
        if self.use_supabase:
            try:
                self.client.table("inventario").insert(item_data).execute()
                return True
            except Exception as e:
                print(f"Error insertando en Supabase: {e}")
                return False
        else:
            import uuid
            if "id" not in item_data or not item_data["id"]:
                item_data["id"] = str(uuid.uuid4())
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO inventario (id, categoria, concepto, stock_ideal, stock_actual, unidad_medida, estatus, notas, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item_data["id"],
                item_data.get("categoria", "General"),
                item_data.get("concepto", ""),
                item_data.get("stock_ideal", 1.0),
                item_data.get("stock_actual", 0.0),
                item_data.get("unidad_medida", "PZA"),
                item_data.get("estatus", "PENDIENTE"),
                item_data.get("notas", ""),
                item_data["updated_at"]
            ))
            conn.commit()
            conn.close()
            return True

    def delete_item(self, item_id: str) -> bool:
        """Elimina un producto por ID."""
        if self.use_supabase:
            try:
                self.client.table("inventario").delete().eq("id", item_id).execute()
                return True
            except Exception as e:
                print(f"Error eliminando de Supabase: {e}")
                return False
        else:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM inventario WHERE id = ?", (item_id,))
            conn.commit()
            conn.close()
            return True
