import zipfile
import xml.etree.ElementTree as ET
import json
import os
from datetime import datetime

def parse_excel(file_path):
    """Extrae las filas y columnas estructuradas de Despensa EMMA_LUPITA.xlsx usando la stdlib."""
    if not os.path.exists(file_path):
        print(f"Error: No se encontró el archivo {file_path}")
        return []

    with zipfile.ZipFile(file_path) as z:
        strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            tree = ET.fromstring(z.read('xl/sharedStrings.xml'))
            for elem in tree.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si'):
                t = ''.join([e.text or '' for e in elem.iter() if e.tag.endswith('t')])
                strings.append(t)
        
        sheet_tree = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
        rows = sheet_tree.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheetData/{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row')
        
        raw_data = []
        for row in rows:
            row_vals = []
            for cell in row.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c'):
                cell_type = cell.attrib.get('t')
                val_elem = cell.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
                val = val_elem.text if val_elem is not None else ''
                if cell_type == 's' and val.isdigit():
                    val = strings[int(val)]
                row_vals.append(val)
            if any(row_vals):
                raw_data.append(row_vals)

    # Filtrar encabezados y procesar filas
    # Filas 0 y 1 son título y fecha. Fila 2 son encabezados:
    # ['Categoría', 'Concepto', 'Unidad ideal', 'UMA', 'Unidad real', 'UMA', 'Por comprar', 'UMA', 'ESTATUS', 'NOTAS']
    items = []
    current_category = "General"

    for idx, row in enumerate(raw_data):
        if idx < 3:
            continue # Omitir encabezados

        cat = row[0].strip() if len(row) > 0 and row[0] else ""
        if cat:
            current_category = cat.split('\n')[0].strip()

        concepto = row[1].strip() if len(row) > 1 else ""
        if not concepto or concepto.lower() == 'concepto':
            continue

        def safe_float(val, default=0.0):
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        stock_ideal = safe_float(row[2] if len(row) > 2 else 1.0, 1.0)
        uma = row[3].strip() if len(row) > 3 and row[3] else "PZA"
        stock_actual = safe_float(row[4] if len(row) > 4 else 0.0, 0.0)
        estatus = row[8].strip() if len(row) > 8 and row[8] else "PENDIENTE"
        notas = row[9].strip() if len(row) > 9 and row[9] else ""

        items.append({
            "categoria": current_category,
            "concepto": concepto,
            "stock_ideal": stock_ideal,
            "stock_actual": stock_actual,
            "unidad_medida": uma,
            "estatus": estatus,
            "notas": notas,
            "updated_at": datetime.now().isoformat()
        })

    return items

def export_to_json(excel_path="Despensa EMMA_LUPITA.xlsx", json_path="initial_seed.json"):
    items = parse_excel(excel_path)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f" Éxito: Se extrajeron {len(items)} productos y se guardaron en {json_path}")
    return items

if __name__ == "__main__":
    export_to_json()
