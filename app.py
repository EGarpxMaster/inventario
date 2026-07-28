import streamlit as st
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime

# Configuración inicial de la página
st.set_page_config(
    page_title="Inventario de Despensa & Hogar",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Importar módulos locales
from db_client import DatabaseClient, get_config_var
from gemini_processor import process_dictation_with_gemini
from export_utils import generate_whatsapp_share_url, generate_shopping_list_pdf

# CSS Personalizado para Estilo Premium
st.markdown("""
    <style>
    /* Estilos generales */
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
    }
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.0rem;
        color: #94a3b8;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #38bdf8;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .status-badge-ok {
        background-color: #064e3b;
        color: #34d399;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 600;
    }
    .status-badge-pending {
        background-color: #7f1d1d;
        color: #fca5a5;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 600;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .whatsapp-btn {
        background-color: #25D366 !important;
        color: white !important;
        font-weight: 700 !important;
        padding: 0.6rem 1.2rem !important;
        border-radius: 10px !important;
        text-decoration: none !important;
        display: inline-block !important;
        text-align: center !important;
        box-shadow: 0 4px 12px rgba(37, 211, 102, 0.3) !important;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# 1. Autenticación con PIN de Seguridad
# ----------------------------------------------------
def check_pin_auth():
    target_pin = str(get_config_var("APP_PIN", "2016"))
    
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.markdown("<div style='text-align: center; margin-top: 50px;'>", unsafe_allow_html=True)
        st.markdown("<h1>🛒 Control de Acceso a Inventario</h1>", unsafe_allow_html=True)
        st.markdown("<p style='color: #94a3b8;'>Por favor ingresa tu PIN de seguridad para acceder a la despensa</p>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1.2, 1])
        with col2:
            input_pin = st.text_input("PIN de Acceso", type="password", placeholder="Ingresa tu PIN")
            if st.button("Ingresar al Inventario", use_container_width=True, type="primary"):
                if input_pin == target_pin:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("❌ PIN incorrecto. Inténtalo nuevamente.")
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

check_pin_auth()

# ----------------------------------------------------
# 2. Inicializar Cliente DB y Estado de Sesión
# ----------------------------------------------------
@st.cache_resource
def init_db():
    return DatabaseClient()

db = init_db()

if "preview_data" not in st.session_state:
    st.session_state.preview_data = None

# Sidebar Navigation & Modos
with st.sidebar:
    st.image("https://img.icons8.com/isometric/96/shopping-cart.png", width=64)
    st.markdown("### Inventario Inteligente")
    
    db_mode = "☁️ Supabase Cloud" if db.use_supabase else "💾 SQLite Local"
    st.caption(f"**Modo Base de Datos:** {db_mode}")
    
    gemini_key = get_config_var("GEMINI_API_KEY")
    key_status = " Conectada" if gemini_key and gemini_key != "tu_gemini_api_key_aqui" else "⚠️ Sin API Key"
    st.caption(f"**Gemini IA:** {key_status}")

    st.markdown("---")
    menu = st.radio(
        "Navegación",
        ["🏠 Inventario General", "🎙️ Dictado Inteligente (IA)", "🛒 Lista de Compras & WhatsApp", "⚙️ Gestión de Productos"],
        index=0
    )
    
    st.markdown("---")
    if st.button("🔒 Cerrar Sesión", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# Cargar inventario completo
df_items = db.get_all_items()

# ----------------------------------------------------
# TAB 1: INVENTARIO GENERAL
# ----------------------------------------------------
if menu == "🏠 Inventario General":
    st.markdown("<div class='main-title'>Inventario General de Despensa</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Monitorea el stock en tiempo real de alimentos, higiene, limpieza y desechables.</div>", unsafe_allow_html=True)

    if df_items.empty:
        st.warning("El inventario está vacío. Ve a la pestaña 'Gestión de Productos' para agregar productos.")
    else:
        # Tarjetas de Métricas
        total_prod = len(df_items)
        hay_casa = len(df_items[df_items["estatus"] == "HAY EN CASA"])
        comprados = len(df_items[df_items["estatus"] == "COMPRADO"])
        pendientes = len(df_items[df_items["estatus"] == "PENDIENTE"])

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f"<div class='metric-card'><div class='metric-value'>{total_prod}</div><div class='metric-label'>Total Productos</div></div>", unsafe_allow_html=True)
        with m2:
            st.markdown(f"<div class='metric-card'><div class='metric-value' style='color:#34d399;'>{hay_casa}</div><div class='metric-label'>Hay en Casa</div></div>", unsafe_allow_html=True)
        with m3:
            st.markdown(f"<div class='metric-card'><div class='metric-value' style='color:#fbbf24;'>{comprados}</div><div class='metric-label'>Comprados en Carrito</div></div>", unsafe_allow_html=True)
        with m4:
            st.markdown(f"<div class='metric-card'><div class='metric-value' style='color:#f87171;'>{pendientes}</div><div class='metric-label'>Pendientes por Comprar</div></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Filtros de búsqueda
        col_f1, col_f2, col_f3 = st.columns([1.5, 1, 1])
        with col_f1:
            search_query = st.text_input("🔍 Buscar producto por nombre:", placeholder="ej. Cloro, Pollo, Atún")
        with col_f2:
            cats = ["Todas"] + list(df_items["categoria"].unique())
            selected_cat = st.selectbox("Filtrar por Categoría:", cats)
        with col_f3:
            statuses = ["Todos", "HAY EN CASA", "PENDIENTE", "COMPRADO", "NO HAY EN EL SUPER"]
            selected_status = st.selectbox("Filtrar por Estatus:", statuses)

        # Aplicar filtros
        filtered_df = df_items.copy()
        if search_query:
            filtered_df = filtered_df[filtered_df["concepto"].str.contains(search_query, case=False, na=False)]
        if selected_cat != "Todas":
            filtered_df = filtered_df[filtered_df["categoria"] == selected_cat]
        if selected_status != "Todos":
            filtered_df = filtered_df[filtered_df["estatus"] == selected_status]

        st.markdown(f"**Mostrando {len(filtered_df)} de {len(df_items)} productos:**")

        # Configuración del Data Editor para edición interactiva directa
        column_config = {
            "id": None, # Ocultar ID
            "concepto": st.column_config.TextColumn("Producto", required=True, width="medium"),
            "categoria": st.column_config.SelectboxColumn("Categoría", options=list(df_items["categoria"].unique()), required=True),
            "stock_ideal": st.column_config.NumberColumn("Ideal en Casa", min_value=0.0, step=0.5, format="%.1f"),
            "stock_actual": st.column_config.NumberColumn("Stock Real", min_value=0.0, step=0.5, format="%.1f"),
            "unidad_medida": st.column_config.SelectboxColumn("Unidad (UMA)", options=["PZA", "KILO", "PAQUETE", "LITRO", "LATA", "BOTE", "CAJA"]),
            "estatus": st.column_config.SelectboxColumn("Estatus", options=["HAY EN CASA", "PENDIENTE", "COMPRADO", "NO HAY EN EL SUPER"]),
            "notas": st.column_config.TextColumn("Notas / Comentarios", width="large"),
            "updated_at": st.column_config.DatetimeColumn("Última Actualización", format="DD/MM/YYYY HH:mm", disabled=True)
        }

        edited_df = st.data_editor(
            filtered_df,
            column_config=column_config,
            use_container_width=True,
            num_rows="dynamic",
            key="inventory_editor"
        )

        col_save, _ = st.columns([1, 3])
        with col_save:
            if st.button(" Guardar Cambios en Inventario", type="primary", use_container_width=True):
                # Sincronizar cambios detectados
                with st.spinner("Guardando cambios..."):
                    for idx, row in edited_df.iterrows():
                        item_id = str(row["id"])
                        updates = {
                            "concepto": row["concepto"],
                            "categoria": row["categoria"],
                            "stock_ideal": row["stock_ideal"],
                            "stock_actual": row["stock_actual"],
                            "unidad_medida": row["unidad_medida"],
                            "estatus": row["estatus"],
                            "notas": row["notas"]
                        }
                        db.update_item(item_id, updates)
                st.success(" ¡Inventario actualizado con éxito!")
                st.rerun()

# ----------------------------------------------------
# TAB 2: DICTADO INTELIGENTE (GEMINI IA)
# ----------------------------------------------------
elif menu == "🎙️ Dictado Inteligente (IA)":
    st.markdown("<div class='main-title'>Dictado Asistido por Gemini IA</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Dicta por voz o escribe en texto los cambios en tu despensa. La IA procesará tu intención y generará una lista previa de verificación antes de guardarla.</div>", unsafe_allow_html=True)

    col_dict1, col_dict2 = st.columns([1.2, 1])

    with col_dict1:
        st.subheader("1. Entrada de Voz o Texto")
        
        # Opción 1: Grabador de Voz Streamlit (si la librería está disponible)
        audio_bytes = None
        try:
            from audio_recorder_streamlit import audio_recorder
            st.write("🎙️ **Graba tu voz (haz clic en el micrófono):**")
            audio_bytes = audio_recorder(text="", recording_color="#ef4444", neutral_color="#3b82f6", icon_name="microphone", icon_size="2x")
        except Exception:
            st.info("💡 Sugerencia: Puedes escribir o subir un archivo de audio directamente abajo.")

        # Opción 2: Subir archivo de audio
        uploaded_audio = st.file_uploader("O sube un archivo de audio (.mp3, .wav, .m4a):", type=["mp3", "wav", "m4a", "ogg"])
        
        # Opción 3: Entrada de texto manual
        st.write("📝 **O escribe tu dictado en lenguaje natural:**")
        dictado_texto = st.text_area(
            "Dictado por texto:",
            placeholder="Ejemplo: Compré 2 kilos de pollo y 3 latas de atún, y ya se nos acabó el cloro y el jabón de cuerpo.",
            height=100
        )

        st.caption("Ejemplos rápidos para probar:")
        col_ex1, col_ex2 = st.columns(2)
        with col_ex1:
            if st.button("Ejemplo 1: Compras del Súper"):
                dictado_texto = "Compré 3 latas de atún, 1 kilo de pollo y 2 paquetes de salmas."
        with col_ex2:
            if st.button("Ejemplo 2: Insumos Agotados"):
                dictado_texto = "Se acabó el cloro, la pasta de dientes y nos falta café."

        if st.button("🤖 Procesar Dictado con Gemini", type="primary", use_container_width=True):
            with st.spinner("Procesando con Gemini API..."):
                current_catalog = df_items.to_dict(orient="records") if not df_items.empty else []
                
                if audio_bytes:
                    res = process_dictation_with_gemini(audio_bytes, current_catalog, is_audio=True, mime_type="audio/wav")
                elif uploaded_audio:
                    audio_data = uploaded_audio.read()
                    res = process_dictation_with_gemini(audio_data, current_catalog, is_audio=True, mime_type=uploaded_audio.type)
                elif dictado_texto:
                    res = process_dictation_with_gemini(dictado_texto, current_catalog, is_audio=False)
                else:
                    st.warning("Por favor graba audio, sube un archivo o escribe un texto para procesar.")
                    res = None

                if res:
                    if res["success"]:
                        st.session_state.preview_data = res
                        st.success(" Dictado interpretado exitosamente por Gemini.")
                    else:
                        st.error(res.get("error", "Error desconocido al procesar dictado."))

    with col_dict2:
        st.subheader("2. Lista Previa de Verificación (Preview)")
        st.info("Revisa los cambios que la IA ha identificado antes de aplicarlos a la base de datos.")

        if st.session_state.preview_data and st.session_state.preview_data.get("cambios"):
            res_data = st.session_state.preview_data
            st.markdown(f"**Explicación de la IA:** {res_data.get('explicacion', '')}")
            
            cambios_list = res_data.get("cambios", [])
            df_preview = pd.DataFrame(cambios_list)
            
            # Formatear la tabla de verificación
            df_preview["confirmar"] = True
            
            # Reordenar columnas para visualización clara
            cols_order = ["confirmar", "concepto", "categoria", "accion", "stock_actual", "estatus", "notas"]
            existing_cols = [c for c in cols_order if c in df_preview.columns]
            df_preview = df_preview[existing_cols]

            edited_preview = st.data_editor(
                df_preview,
                column_config={
                    "confirmar": st.column_config.CheckboxColumn(" Confirmar", default=True),
                    "concepto": st.column_config.TextColumn("Producto"),
                    "categoria": st.column_config.TextColumn("Categoría"),
                    "accion": st.column_config.TextColumn("Acción"),
                    "stock_actual": st.column_config.NumberColumn("Nuevo Stock", format="%.1f"),
                    "estatus": st.column_config.SelectboxColumn("Estatus", options=["HAY EN CASA", "PENDIENTE", "COMPRADO", "NO HAY EN EL SUPER"]),
                    "notas": st.column_config.TextColumn("Notas")
                },
                use_container_width=True,
                key="preview_editor"
            )

            if st.button(" Confirmar y Aplicar Cambios al Inventario", type="primary", use_container_width=True):
                with st.spinner("Aplicando actualizaciones..."):
                    count_applied = 0
                    for idx, row in edited_preview.iterrows():
                        if row.get("confirmar", True):
                            item_id = str(row.get("id", ""))
                            concepto = row.get("concepto", "")
                            
                            # Buscar si existe en el inventario por ID o nombre
                            matched_item = None
                            if item_id and not df_items.empty and "id" in df_items.columns:
                                match = df_items[df_items["id"].astype(str) == item_id]
                                if not match.empty:
                                    matched_item = match.iloc[0]

                            if matched_item is None and not df_items.empty:
                                match_name = df_items[df_items["concepto"].str.lower() == concepto.lower()]
                                if not match_name.empty:
                                    matched_item = match_name.iloc[0]

                            updates = {
                                "stock_actual": float(row.get("stock_actual", 0.0)),
                                "estatus": row.get("estatus", "PENDIENTE"),
                                "notas": row.get("notas", "")
                            }

                            if matched_item is not None:
                                db.update_item(str(matched_item["id"]), updates)
                            else:
                                # Agregar nuevo producto
                                new_product = {
                                    "concepto": concepto,
                                    "categoria": row.get("categoria", "General"),
                                    "stock_ideal": float(row.get("stock_actual", 1.0)) or 1.0,
                                    "stock_actual": float(row.get("stock_actual", 0.0)),
                                    "unidad_medida": "PZA",
                                    "estatus": row.get("estatus", "PENDIENTE"),
                                    "notas": row.get("notas", "")
                                }
                                db.add_item(new_product)
                            count_applied += 1

                st.session_state.preview_data = None
                st.success(f" Se aplicaron {count_applied} cambios al inventario.")
                st.rerun()
        else:
            st.caption("Aún no hay cambios pendientes de verificación. Graba o escribe un dictado en la sección izquierda.")

# ----------------------------------------------------
# TAB 3: LISTA DE COMPRAS & WHATSAPP
# ----------------------------------------------------
elif menu == "🛒 Lista de Compras & WhatsApp":
    st.markdown("<div class='main-title'>Lista de Compras Faltantes</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Visualiza rápidamente qué productos necesitas comprar en el supermercado y compártelos por WhatsApp o PDF.</div>", unsafe_allow_html=True)

    if df_items.empty:
        st.info("No hay datos en el inventario.")
    else:
        # Filtrar ítems a comprar (Pendientes, Comprados en carrito o con stock actual menor al ideal)
        df_items["cantidad_a_comprar"] = np.maximum(df_items["stock_ideal"] - df_items["stock_actual"], 0)
        
        shopping_df = df_items[
            (df_items["estatus"].isin(["PENDIENTE", "COMPRADO", "NO HAY EN EL SUPER"])) | 
            (df_items["cantidad_a_comprar"] > 0)
        ].copy()

        if shopping_df.empty:
            st.success(" 🎉 ¡Felicidades! Todo tu inventario está completo y hay suficiente stock en casa.")
        else:
            # Botones de Acción (WhatsApp & PDF)
            col_wa, col_pdf, _ = st.columns([1.2, 1.2, 1])

            with col_wa:
                wa_url = generate_whatsapp_share_url(shopping_df)
                st.markdown(f"""
                    <a href="{wa_url}" target="_blank" class="whatsapp-btn">
                        📲 Compartir Lista por WhatsApp
                    </a>
                """, unsafe_allow_html=True)

            with col_pdf:
                try:
                    pdf_bytes = generate_shopping_list_pdf(shopping_df)
                    st.download_button(
                        label="📄 Descargar Lista en PDF",
                        data=bytes(pdf_bytes),
                        file_name=f"Lista_de_Compras_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Error generando PDF: {e}")

            st.markdown("<br>", unsafe_allow_html=True)

            # Mostrar lista por categorías
            categories = shopping_df["categoria"].unique()
            for cat in categories:
                st.subheader(f"📌 {cat}")
                cat_items = shopping_df[shopping_df["categoria"] == cat]

                for idx, row in cat_items.iterrows():
                    item_id = str(row["id"])
                    concepto = row["concepto"]
                    comprar = row["cantidad_a_comprar"]
                    uma = row["unidad_medida"]
                    estatus = row["estatus"]
                    notas = row["notas"]

                    c1, c2, c3, c4 = st.columns([2, 1, 1.5, 2])
                    with c1:
                        st.markdown(f"**{concepto}**")
                        if notas:
                            st.caption(f"📝 {notas}")
                    with c2:
                        st.markdown(f"`Faltan: {comprar} {uma}`")
                    with c3:
                        # Marcar rápidamente como Comprado en el super
                        is_bought = estatus == "COMPRADO"
                        if st.checkbox("En Carrito", value=is_bought, key=f"shop_check_{item_id}"):
                            if estatus != "COMPRADO":
                                db.update_item(item_id, {"estatus": "COMPRADO"})
                                st.rerun()
                        else:
                            if estatus == "COMPRADO":
                                db.update_item(item_id, {"estatus": "PENDIENTE"})
                                st.rerun()
                    with c4:
                        if st.button("Marcar en Casa", key=f"home_btn_{item_id}"):
                            db.update_item(item_id, {
                                "estatus": "HAY EN CASA",
                                "stock_actual": float(row["stock_ideal"])
                            })
                            st.rerun()
                st.markdown("---")

# ----------------------------------------------------
# TAB 4: GESTIÓN DE PRODUCTOS
# ----------------------------------------------------
elif menu == "⚙️ Gestión de Productos":
    st.markdown("<div class='main-title'>Gestión y Configuración de Productos</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Agrega manualmente nuevos insumos, elimina productos obsoletos o reinicia la semilla inicial de Excel.</div>", unsafe_allow_html=True)

    tab_add, tab_del, tab_seed = st.tabs(["➕ Agregar Producto", "🗑️ Eliminar Producto", "🌱 Cargar Semilla de Excel"])

    with tab_add:
        with st.form("add_product_form"):
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                new_concepto = st.text_input("Nombre del Producto *", placeholder="ej. Papel aluminio")
                new_categoria = st.text_input("Categoría *", placeholder="ej. Desechables, Alimentos, Higiene, Limpieza")
                new_uma = st.selectbox("Unidad de Medida (UMA)", ["PZA", "KILO", "PAQUETE", "LITRO", "LATA", "BOTE", "CAJA"])
            with col_a2:
                new_ideal = st.number_input("Stock Ideal Objetivo", min_value=0.1, value=1.0, step=0.5)
                new_actual = st.number_input("Stock Actual Real", min_value=0.0, value=0.0, step=0.5)
                new_estatus = st.selectbox("Estatus Inicial", ["PENDIENTE", "HAY EN CASA", "COMPRADO", "NO HAY EN EL SUPER"])

            new_notas = st.text_input("Notas u Observaciones", placeholder="ej. Comprar solo marca específica")
            
            submitted = st.form_submit_button(" Guardar Producto Nuevo", type="primary")
            if submitted:
                if not new_concepto or not new_categoria:
                    st.error("El nombre del producto y la categoría son obligatorios.")
                else:
                    new_item = {
                        "concepto": new_concepto,
                        "categoria": new_categoria,
                        "stock_ideal": new_ideal,
                        "stock_actual": new_actual,
                        "unidad_medida": new_uma,
                        "estatus": new_estatus,
                        "notas": new_notas
                    }
                    db.add_item(new_item)
                    st.success(f" Producto '{new_concepto}' agregado exitosamente.")
                    st.rerun()

    with tab_del:
        if not df_items.empty:
            item_to_delete = st.selectbox("Selecciona el producto a eliminar:", df_items["concepto"].unique())
            if st.button("❌ Confirmar Eliminación", type="primary"):
                matched = df_items[df_items["concepto"] == item_to_delete]
                if not matched.empty:
                    item_id = str(matched.iloc[0]["id"])
                    db.delete_item(item_id)
                    st.success(f"Producto '{item_to_delete}' eliminado.")
                    st.rerun()
        else:
            st.info("No hay productos para eliminar.")

    with tab_seed:
        st.warning("⚠️ Cargar la semilla inicial sobrescribirá o restaurará los 46 productos por defecto del archivo 'Despensa EMMA_LUPITA.xlsx'.")
        if st.button("🌱 Restaurar Semilla de Excel Inicial"):
            from import_excel import export_to_json
            items = export_to_json()
            for item in items:
                db.add_item(item)
            st.success(f" Restaurados {len(items)} productos desde el Excel.")
            st.rerun()
