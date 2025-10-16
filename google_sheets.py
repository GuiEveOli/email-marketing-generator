import re
import csv
from io import StringIO

def _norm(s):
    if s is None:
        return ''
    return re.sub(r"\s+", '', str(s).replace('\ufeff', '').strip()).upper()

expected = ['COD_PRODUTO', 'NOMEPRODUTOECOMM', 'COD_BARRAS', 'URLECOMMERCEIMG', 'PRODUCTURL']
aliases = {
    'CODPRODUTO': 'COD_PRODUTO',
    'SKU': 'COD_PRODUTO',
    'NOME': 'NOMEPRODUTOECOMM',
    'NOMEPRODUTO': 'NOMEPRODUTOECOMM',
    'NOME_PRODUTO': 'NOMEPRODUTOECOMM',
    'DESCRICAO': 'NOMEPRODUTOECOMM',
    'CODBARRAS': 'COD_BARRAS',
    'EAN': 'COD_BARRAS',
    'URLIMG': 'URLECOMMERCEIMG',
    'IMAGEM': 'URLECOMMERCEIMG',
    'URLIMAGEM': 'URLECOMMERCEIMG',
    'URL': 'PRODUCTURL',
    'LINK': 'PRODUCTURL',
    'PRODUCT_URL': 'PRODUCTURL',
    'URL_PRODUTO': 'PRODUCTURL'
}

def _map_headers(fieldnames):
    detected_norm = [_norm(h) for h in fieldnames]
    expected_norm = [_norm(x) for x in expected]
    mapping = {}
    for idx, norm_name in enumerate(detected_norm):
        real = fieldnames[idx]
        if norm_name in expected_norm:
            i = expected_norm.index(norm_name)
            mapping[expected[i]] = real
        elif norm_name in aliases:
            canonical = aliases[norm_name]
            mapping.setdefault(canonical, real)
    return mapping

def _rows_to_produtos(rows, mapping):
    produtos = []
    for row in rows:
        try:
            sku = str(row.get(mapping.get('COD_PRODUTO', ''), '')).strip()
            nome = str(row.get(mapping.get('NOMEPRODUTOECOMM', ''), '')).strip()
            ean = str(row.get(mapping.get('COD_BARRAS', ''), '')).strip()
            imagem = str(row.get(mapping.get('URLECOMMERCEIMG', ''), '')).strip()
            url = str(row.get(mapping.get('PRODUCTURL', ''), '')).strip()
            if not url or url in ('0', '-'):
                continue
            produtos.append({'sku': sku, 'nome': nome, 'ean': ean, 'imagem': imagem, 'url': url})
        except Exception:
            continue
    return produtos

def parse_csv_text(csv_text):
    for delimiter in [';', ',', '\t', '|']:
        sio = StringIO(csv_text)
        reader = csv.DictReader(sio, delimiter=delimiter)
        fieldnames = reader.fieldnames or []
        if not fieldnames:
            continue
        mapping = _map_headers(fieldnames)
        if all(col in mapping for col in expected):
            produtos = _rows_to_produtos(list(reader), mapping)
            if produtos:
                return produtos, {'delimiter': delimiter}
    return [], {}

def ler_produtos_via_sheets_csv(url):
    import requests
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    text = resp.text
    produtos, meta = parse_csv_text(text)
    return produtos, {'source': 'sheets_csv', **meta}

def ler_produtos_via_api(spreadsheet_id, worksheet_or_range=None, credentials_file=None):
    from google.oauth2.service_account import Credentials
    import gspread
    scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    creds = Credentials.from_service_account_file(credentials_file, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(spreadsheet_id)

    # Coleta valores
    values = []
    if worksheet_or_range and '!' in worksheet_or_range:
        sheet_name, rng = worksheet_or_range.split('!', 1)
        ws = sh.worksheet(sheet_name)
        values = ws.get(rng) or []
    else:
        if worksheet_or_range:
            ws = sh.worksheet(worksheet_or_range)
        else:
            ws = sh.sheet1
        values = ws.get_all_values() or []

    if not values:
        return [], {'source': 'sheets_api'}

    fieldnames = values[0]
    rows = []
    for vals in values[1:]:
        row = {fieldnames[i]: (vals[i] if i < len(vals) else '') for i in range(len(fieldnames))}
        rows.append(row)

    mapping = _map_headers(fieldnames)
    if not all(col in mapping for col in expected):
        return [], {'source': 'sheets_api', 'headers': fieldnames}

    produtos = _rows_to_produtos(rows, mapping)
    return produtos, {'source': 'sheets_api', 'worksheet': worksheet_or_range or (ws.title if 'ws' in locals() else 'sheet1')}