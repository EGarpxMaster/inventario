import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

def get_gemini_api_key():
    """Obtiene la API key de Gemini desde secretos o variables de entorno."""
    try:
        import streamlit as st
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY", "")

def process_dictation_with_gemini(input_data, current_catalog, is_audio=False, mime_type="audio/wav"):
    """
    Procesa dictado de texto o audio utilizando Gemini API.
    
    :param input_data: str (texto) o bytes (audio)
    :param current_catalog: list de dicts con el inventario actual
    :param is_audio: bool indicando si es audio
    :param mime_type: tipo mime del audio si aplica
    :return: dict con los cambios propuestos y explicación
    """
    api_key = get_gemini_api_key()
    if not api_key or api_key == "tu_gemini_api_key_aqui":
        return {
            "success": False,
            "error": "No se ha configurado una GEMINI_API_KEY válida. Por favor configúrala en el archivo .env o en .streamlit/secrets.toml.",
            "cambios": []
        }

    # Intentar usar el nuevo SDK google-genai o el clasico google-generativeai
    try:
        from google import genai
        from google.genai import types
        use_new_sdk = True
    except ImportError:
        try:
            import google.generativeai as genai_old
            use_new_sdk = False
        except ImportError:
            return {
                "success": False,
                "error": "La librería `google-genai` no está instalada.",
                "cambios": []
            }

    # Preparar resumen del catálogo actual para contexto de Gemini
    catalog_summary = []
    for item in current_catalog:
        catalog_summary.append({
            "id": str(item.get("id", "")),
            "concepto": item.get("concepto", ""),
            "categoria": item.get("categoria", ""),
            "stock_actual": item.get("stock_actual", 0.0),
            "stock_ideal": item.get("stock_ideal", 1.0),
            "unidad_medida": item.get("unidad_medida", "PZA"),
            "estatus": item.get("estatus", "PENDIENTE"),
            "notas": item.get("notas", "")
        })

    system_instruction = f"""
Eres un Asistente Inteligente de Inventario de Despensa e Insumos del Hogar.
Tu tarea es analizar el dictado (audio o texto en español) del usuario y traducirlo a modificaciones precisas sobre el catálogo de productos existente.

Catálogo actual de productos disponibles en la casa:
{json.dumps(catalog_summary, ensure_ascii=False, indent=2)}

Reglas de interpretación:
1. Si el usuario dice que compró algo (ej. "Compré 3 latas de atún"), debes cambiar el estatus a "COMPRADO" o "HAY EN CASA" y actualizar stock_actual a esa cantidad o sumarle esa cantidad.
2. Si el usuario dice que consumió, gastó o que ya no hay (ej. "Nos quedamos sin cloro" o "Gasté 1 litro de leche"), actualiza stock_actual a 0 (o réstalo) y cambia el estatus a "PENDIENTE" si es 0.
3. Si el producto ya existe en el catálogo, usa exactamente su "id" y su "concepto" existente.
4. Si el producto NO existe en el catálogo y el usuario lo menciona (ej. "Agrega servilletas de papel"), marca "accion": "ADD_PRODUCT", sugiere una categoría adecuada (Alimentos, Higiene, Limpieza, Desechables) y asígnalle id vacio "".
5. Estatus posibles permitidos: "HAY EN CASA", "PENDIENTE", "COMPRADO", "NO HAY EN EL SUPER".

Debes responder ÚNICAMENTE con un objeto JSON válido con la siguiente estructura:
{{
  "explicacion": "Breve resumen comprensible para el usuario de lo que entendiste",
  "cambios": [
    {{
      "id": "ID_DEL_PRODUCTO_O_VACIO",
      "concepto": "Nombre del producto",
      "categoria": "Categoría",
      "accion": "UPDATE_STOCK_AND_STATUS" | "ADD_PRODUCT" | "DELETE",
      "stock_actual": 2.0,
      "stock_ideal": 2.0,
      "unidad_medida": "PZA",
      "estatus": "COMPRADO",
      "notas": "Comentario opcional extraído del dictado"
    }}
  ]
}}
"""

    prompt = "Analiza el siguiente dictado e identifica las actualizaciones de inventario:"

    # Probar modelos disponibles verificados para la API key
    candidate_models = [
        'gemini-flash-latest',
        'gemini-flash-lite-latest',
        'gemini-3.1-flash-lite',
        'gemini-3-flash-preview',
        'gemini-3.5-flash-lite',
        'gemini-2.0-flash'
    ]
    raw_text = None
    last_error = None

    for model_name in candidate_models:
        try:
            if use_new_sdk:
                client = genai.Client(api_key=api_key)
                contents = [system_instruction, prompt]
                
                if is_audio:
                    contents.append(types.Part.from_bytes(data=input_data, mime_type=mime_type))
                else:
                    contents.append(f"Dictado del usuario: \"{input_data}\"")

                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1
                    )
                )
                raw_text = response.text
                if raw_text:
                    break
            else:
                genai_old.configure(api_key=api_key)
                model = genai_old.GenerativeModel(model_name)
                parts = [system_instruction, prompt]
                if is_audio:
                    parts.append({"mime_type": mime_type, "data": input_data})
                else:
                    parts.append(f"Dictado del usuario: \"{input_data}\"")

                response = model.generate_content(parts)
                raw_text = response.text
                if raw_text:
                    break
        except Exception as err:
            last_error = err
            continue

    if not raw_text:
        return {
            "success": False,
            "error": f"Error al procesar con Gemini API: {str(last_error)}",
            "cambios": []
        }

    try:
        # Limpiar markdown wrapper json si existe
        clean_json = re.sub(r'^```json\s*|\s*```$', '', raw_text.strip(), flags=re.MULTILINE)
        data = json.loads(clean_json)

        return {
            "success": True,
            "explicacion": data.get("explicacion", "Dictado procesado correctamente."),
            "cambios": data.get("cambios", [])
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Error parseando respuesta JSON de Gemini: {str(e)}",
            "cambios": []
        }
