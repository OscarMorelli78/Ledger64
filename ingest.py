"""Bounded document ingestion; ambiguous documents fail closed."""
import csv, io, zipfile, hashlib, base64, binascii, json
from datetime import datetime,date
from decimal import Decimal
from engine import FIELDS, InputError, MAX_BYTES, audit, parse
from flexible import convert, invoice_text, monthly

def xlsx(raw):
    from openpyxl import load_workbook
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            infos=z.infolist()
            if len(infos)>200 or sum(i.file_size for i in infos)>20_000_000: raise InputError('Excel excede límites de descompresión')
            if any('vbaProject' in i.filename or 'externalLinks/' in i.filename for i in infos): raise InputError('Macros o vínculos externos no admitidos')
        w=load_workbook(io.BytesIO(raw),read_only=True,data_only=False,keep_links=False)
        try:
            if len(w.sheetnames)!=1: raise InputError('Se requiere una sola hoja de compras')
            s=w.active
            if (s.max_row or 0)>10001 or (s.max_column or 0)>40: raise InputError('Dimensiones Excel excedidas')
            rows=[]
            for i,row in enumerate(s.iter_rows(),1):
                if i>10001 or len(row)>40: raise InputError('Dimensiones o columnas incorrectas')
                vals=[]
                for c in row:
                    if c.data_type in ('f','e') or isinstance(c.value,bool): raise InputError('Fórmulas, errores y booleanos no admitidos')
                    v=c.value
                    if isinstance(v,datetime):
                        if v.time()!=datetime.min.time(): raise InputError('Fecha con hora no admitida')
                        v=v.date()
                    if isinstance(v,date): v=v.isoformat()
                    if isinstance(v,float): v=format(Decimal(str(v)),'f')
                    vals.append(v)
                rows.append(vals)
            return convert(rows)
        finally:w.close()
    except InputError:raise
    except Exception as e:raise InputError('Excel inválido o no compatible') from e

def pdf(raw):
    from pypdf import PdfReader
    try:
        r=PdfReader(io.BytesIO(raw),strict=True)
        if r.is_encrypted or len(r.pages)>30:raise InputError('PDF cifrado o superior a 30 páginas')
        lines=[]
        for p in r.pages:
            content=p.get_contents()
            if content and len(content.get_data())>2_000_000:raise InputError('Página PDF demasiado compleja')
            text=p.extract_text() or ''
            if not text.strip():raise InputError('PDF escaneado: requiere transcripción verificada')
            lines.extend(x.strip() for x in text.splitlines() if x.strip())
        # Only a documented pipe-delimited purchase export; never infer arbitrary invoice tables.
        header='|'.join(FIELDS)
        if not lines or lines[0]!=header:return invoice_text('\n'.join(lines))
        out=io.StringIO(newline=''); w=csv.writer(out);w.writerow(FIELDS)
        for line in lines[1:]:
            if line==header:continue
            parts=line.split('|')
            if len(parts)!=len(FIELDS):raise InputError('Fila PDF ambigua')
            w.writerow(parts)
        return out.getvalue().encode('utf-8')
    except InputError:raise
    except Exception as e:raise InputError('PDF inválido o no compatible') from e

def normalize(raw):
    if not raw or len(raw)>MAX_BYTES:raise InputError('Archivo vacío o superior a 2 MB')
    fmt='xlsx' if raw.startswith(b'PK\x03\x04') else 'pdf' if raw.startswith(b'%PDF-') else 'csv'
    normalized={'xlsx':xlsx,'pdf':pdf,'csv':lambda x:x}[fmt](raw)
    parse(normalized)
    return fmt,normalized

def finish(normalized,source_hash,fmt,synthetic=False,connection=None):
    changes=[]
    if connection is not None and not synthetic:
        from decisions import apply
        normalized,changes=apply(normalized,connection)
    result=audit(normalized,synthetic)
    result['approved_mappings']=changes
    result.update(schema_version=3,source_format=fmt,normalized_sha256=result['input_sha256'],input_sha256=source_hash)
    result['monthly_costs']=monthly(normalized)
    from independent import verify
    result['verification']=verify(normalized,result)
    return result

def audit_document(raw,synthetic=False,connection=None):
    fmt,normalized=normalize(raw)
    return finish(normalized,hashlib.sha256(raw).hexdigest(),fmt,synthetic,connection)

MAX_BATCH_BODY=12_000_000

def audit_batch(payload,connection=None):
    if not isinstance(payload,dict) or not isinstance(payload.get('files'),list) or not 2<=len(payload['files'])<=20:raise InputError('Selecciona entre 2 y 20 archivos')
    out=io.StringIO(newline='');w=csv.writer(out);w.writerow(FIELDS);manifest=[];total=0;row_count=0
    for obj in payload['files']:
        if not isinstance(obj,dict) or not isinstance(obj.get('name'),str) or not isinstance(obj.get('data'),str):raise InputError('Archivo de lote inválido')
        name=obj['name'].strip()
        if not name or len(name)>200 or '/' in name or '\\' in name:raise InputError('Nombre de archivo inválido')
        try:raw=base64.b64decode(obj['data'],validate=True)
        except (ValueError,binascii.Error) as e:raise InputError('Base64 inválido') from e
        total+=len(raw)
        if total>8_000_000:raise InputError('Lote superior a 8 MB')
        try:fmt,normalized=normalize(raw)
        except InputError as e:raise InputError(f'{name}: {e}') from e
        start=row_count+2
        r=csv.reader(io.StringIO(normalized.decode('utf-8-sig'),newline=''));next(r)
        for line in r:
            if not line:continue
            w.writerow(line);row_count+=1
            if row_count>10000:raise InputError('Lote superior a 10.000 líneas')
        manifest.append({'name':name,'format':fmt,'sha256':hashlib.sha256(raw).hexdigest(),'first_normalized_row':start,'last_normalized_row':row_count+1})
    normalized=out.getvalue().encode();source_hash=hashlib.sha256(json.dumps(manifest,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    result=finish(normalized,source_hash,'batch',False,connection);result['source_documents']=manifest
    return result
