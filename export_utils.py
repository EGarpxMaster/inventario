import urllib.parse
from fpdf import FPDF
import io

def generate_whatsapp_share_url(shopping_list_df, phone_number=""):
    """
    Genera un enlace ejecutable para enviar la lista de compras por WhatsApp
    con formato de emojis y Markdown de WhatsApp.
    """
    if shopping_list_df is None or shopping_list_df.empty:
        text = "🛒 *LISTA DE COMPRAS - DESPENSA*\n\n ¡Todo está completo en casa! No hay productos pendientes por comprar."
    else:
        text = "🛒 *LISTA DE COMPRAS - DESPENSA*\n"
        text += "-----------------------------------\n\n"

        # Agrupar por categoría
        categories = shopping_list_df["categoria"].unique()
        for cat in categories:
            cat_df = shopping_list_df[shopping_list_df["categoria"] == cat]
            text += f"📌 *{cat.upper()}*\n"
            for _, row in cat_df.iterrows():
                concepto = row.get("concepto", "")
                faltante = row.get("cantidad_a_comprar", 1)
                uma = row.get("unidad_medida", "PZA")
                estatus = row.get("estatus", "PENDIENTE")
                notas = row.get("notas", "")

                icon = "🔴" if estatus == "PENDIENTE" else "🟡" if estatus == "COMPRADO" else "⚪"
                notes_str = f" _({notas})_" if notas else ""
                
                text += f"{icon} *{concepto}*: {faltante} {uma}{notes_str}\n"
            text += "\n"

        text += "-----------------------------------\n"
        text += " Generado con Inventario Inteligente (Gemini + Supabase)"

    encoded_text = urllib.parse.quote(text)
    if phone_number:
        clean_phone = ''.join(filter(str.isdigit, str(phone_number)))
        return f"https://api.whatsapp.com/send?phone={clean_phone}&text={encoded_text}"
    else:
        return f"https://api.whatsapp.com/send?text={encoded_text}"


class ShoppingListPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(30, 41, 59) # Slate color
        self.cell(0, 10, 'LISTA DE COMPRAS - INVENTARIO DE DESPENSA', 0, 1, 'C')
        self.set_font('Helvetica', 'I', 10)
        self.set_text_color(100, 116, 139)
        self.cell(0, 5, 'Generado automáticamente por el Sistema de Inventario Inteligente', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')


def generate_shopping_list_pdf(shopping_list_df):
    """
    Genera un archivo PDF binario en memoria con la Lista de Compras elegante.
    """
    pdf = ShoppingListPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    if shopping_list_df is None or shopping_list_df.empty:
        pdf.set_font('Helvetica', '', 12)
        pdf.cell(0, 10, '¡Excelente! No hay productos pendientes por comprar en este momento.', 0, 1, 'L')
    else:
        categories = shopping_list_df["categoria"].unique()
        for cat in categories:
            cat_df = shopping_list_df[shopping_list_df["categoria"] == cat]
            
            # Título de Categoría
            pdf.set_font('Helvetica', 'B', 12)
            pdf.set_fill_color(241, 245, 249) # Light grey background
            pdf.set_text_color(15, 23, 42)
            pdf.cell(0, 8, f'  {cat.upper()}', 0, 1, 'L', fill=True)
            pdf.ln(2)

            # Encabezado de Tabla
            pdf.set_font('Helvetica', 'B', 10)
            pdf.set_text_color(71, 85, 105)
            pdf.cell(10, 7, '[ ]', 1, 0, 'C')
            pdf.cell(75, 7, 'Producto', 1, 0, 'L')
            pdf.cell(35, 7, 'A Comprar', 1, 0, 'C')
            pdf.cell(35, 7, 'Estatus', 1, 0, 'C')
            pdf.cell(35, 7, 'Notas', 1, 1, 'L')

            # Filas de Productos
            pdf.set_font('Helvetica', '', 10)
            pdf.set_text_color(30, 41, 59)

            for _, row in cat_df.iterrows():
                concepto = str(row.get("concepto", ""))[:35]
                faltante = f"{row.get('cantidad_a_comprar', 1)} {row.get('unidad_medida', 'PZA')}"
                estatus = str(row.get("estatus", "PENDIENTE"))
                notas = str(row.get("notas", ""))[:20]

                pdf.cell(10, 7, '', 1, 0, 'C') # Checkbox box
                pdf.cell(75, 7, concepto, 1, 0, 'L')
                pdf.cell(35, 7, faltante, 1, 0, 'C')
                pdf.cell(35, 7, estatus, 1, 0, 'C')
                pdf.cell(35, 7, notas, 1, 1, 'L')

            pdf.ln(4)

    # Retornar los bytes del PDF en memoria
    return pdf.output()
