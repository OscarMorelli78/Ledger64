"""Optional OCR: draft transcription only, never used as audited amounts."""
import io,math,shutil,subprocess,time,hashlib
from engine import MAX_BYTES,InputError

def transcribe(raw,language='eng'):
    if language not in ('eng','spa','spa+eng'):raise InputError('Idioma OCR no admitido')
    if not raw.startswith(b'%PDF-') or len(raw)>MAX_BYTES:raise InputError('OCR requiere un PDF de hasta 2 MB')
    binary=shutil.which('tesseract')
    if not binary:raise InputError('OCR no disponible: instala Tesseract y los modelos de idioma requeridos')
    try:import pypdfium2 as pdfium
    except ImportError as e:raise InputError('OCR no disponible: falta pypdfium2') from e
    start=time.monotonic();pages=[]
    try:
        doc=pdfium.PdfDocument(raw)
        try:
            if not 1<=len(doc)<=5:raise InputError('OCR admite hasta cinco páginas')
            for i in range(len(doc)):
                page=doc[i]
                try:
                    w,h=page.get_size();scale=min(2.5,math.sqrt(6_000_000/(w*h)))
                    if min(w,h)<=0 or scale<.5:raise InputError('Dimensiones PDF no admitidas')
                    bitmap=page.render(scale=scale)
                    try:
                        img=bitmap.to_pil().convert('RGB');buf=io.BytesIO();img.save(buf,format='PNG');img.close()
                    finally:bitmap.close()
                finally:page.close()
                timeout=max(1,30-(time.monotonic()-start))
                p=subprocess.run([binary,'stdin','stdout','-l',language,'--psm','6'],input=buf.getvalue(),capture_output=True,timeout=timeout,check=False)
                if p.returncode:raise InputError('OCR no pudo reconocer la página')
                text=p.stdout.decode('utf-8',errors='replace')
                if len(text)>100_000:raise InputError('Transcripción demasiado larga')
                pages.append({'page':i+1,'text':text})
                if time.monotonic()-start>30:raise InputError('OCR superó el límite de tiempo')
        finally:doc.close()
    except InputError:raise
    except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as e:raise InputError('OCR inválido o no disponible dentro de los límites') from e
    except Exception as e:raise InputError('PDF no compatible con OCR') from e
    return {'status':'BORRADOR_NO_VERIFICADO','source_sha256':hashlib.sha256(raw).hexdigest(),'language':language,'pages':pages,'warning':'Revisa la transcripción contra el original. No se incorpora a los cálculos de auditoría.'}
