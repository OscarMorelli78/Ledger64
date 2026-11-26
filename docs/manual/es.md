# Ledger64 — Documentación (Español)

Auditoría de facturas, comparación de costes de compra y gobernanza financiera de código abierto para pymes. Interfaz inspirada en C64 y procesamiento local sin IA externa.

**Versión candidata: utiliza solo datos sintéticos. No certifica contabilidad ni impuestos. Solo compras en EUR; sin abonos. ALE es experimental y fuera de línea. Docker y despliegue alojado requieren aceptación independiente.**

## 1. Instalación

Instala Python 3.13, Node.js para pruebas, Tesseract con modelos inglés y español para OCR, Pango y fuentes Noto para PDF. Crea un entorno virtual e instala las dependencias fijadas. En Windows usa activación PowerShell y variables `$env:`. Configura un directorio privado; no expongas el servidor legado `app.py`.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
export BC_ROOT="$PWD/data" BC_TLS=0 BC_HOSTS=127.0.0.1 BC_ORIGIN=http://127.0.0.1:8765
python admin.py company Demo
# COMPANY_ID = returned identifier
python admin.py user COMPANY_ID demo-owner --role owner
python admin.py user COMPANY_ID demo-analyst --role analyst
python -m uvicorn secure_app:app --host 127.0.0.1 --port 8765
```
```powershell
.venv\Scripts\Activate.ps1
$env:BC_ROOT = "$PWD\data"
$env:BC_TLS = "0"
$env:BC_HOSTS = "127.0.0.1"
$env:BC_ORIGIN = "http://127.0.0.1:8765"
```
http://127.0.0.1:8765/login

## 2. Cuentas y roles

Crea una empresa y dos propietarios distintos (o analista y propietario independiente). La CLI solicita contraseñas de al menos 14 caracteres; no hay credenciales por defecto. Abre el acceso y elige idioma. Lectores no escriben, analistas proponen y propietarios revisan solicitudes de otros usuarios.

## 3. Formato de entrada

Empieza con la demostración sintética. La plantilla estándar tiene once campos, indicados abajo; fecha ISO AAAA-MM-DD, unidades kg, l, ud (g y ml se normalizan), precios en EUR sin IVA. Cantidad positiva y total neto más portes menos descuento. CSV UTF-8, XLSX de una hoja sin fórmulas, macros ni enlaces externos, o PDF estructurado compatible. Máximo 2 MB por archivo, 10.000 líneas; lotes de 2–20 y 8 MB total. No admite indiscriminadamente facturas ni modelos fiscales.

```csv
supplier,invoice,line,date,product,unit,quantity,net_eur,shipping_eur,discount_eur,reported_total_eur
DEMO,INV-001,1,2026-01-01,ITEM,kg,10,100,0,0,100
```

## 4. Auditoría y comparación

Ejecuta Analizar archivo. Examina descuadres, posibles duplicados y subidas de precio de al menos 10 %. IDs repetidos conflictivos e importes descuadrados quedan fuera de comparación. Compara productos idénticos, unidades iguales y observaciones recientes dentro de 30 días. Ahorro potencial no equivale a ahorro pagado o realizado. El coste mensual incluye solo filas elegibles.

## 5. Revisión OCR

PDF escaneado: transcribe hasta cinco páginas con OCR inglés/español; contrasta con el original y corrige el CSV manualmente. Presenta original, CSV revisado y justificación de 10–1000 caracteres. El texto OCR no entra en cálculos sin revisión; esto no verifica independientemente el original.

## 6. Gobernanza

Propón códigos de equivalencia o ahorros declarados con evidencia y referencias distintas de base y compra. Otro propietario aprueba o rechaza; no hay autoaprobación. Los informes ordinarios son borradores. Solicita liberar informes reales (no sintéticos), con contraste aritmético favorable y revisor independiente. Liberación aprobada solo en JSON. Conserva cadena local y evidencias.

## 7. Inteligencia documental

En Inteligencia documental, presenta archivos compatibles clasificados reales/sintéticos, ID opcional de plantilla aprobada y evidencia. Para una plantilla, JSON con los once campos mapeados a cabeceras distintas, proveedor, separador y booleano `spanish` de formato numérico. Otro propietario revisa las líneas normalizadas y decide; plantillas caducadas o revocadas no son válidas. Los cambios de política requieren aprobación independiente.

```json
{
  "mapping": {
    "supplier": "supplier",
    "invoice": "invoice",
    "line": "line",
    "date": "date",
    "product": "product",
    "unit": "unit",
    "quantity": "quantity",
    "net_eur": "net_eur",
    "shipping_eur": "shipping_eur",
    "discount_eur": "discount_eur",
    "reported_total_eur": "reported_total_eur"
  },
  "supplier": "DEMO",
  "delimiter": ",",
  "spanish": false
}
```
## 8. ROI documentado

Para ROI documentado, selecciona dos documentos aprobados y números de línea desde 1, mismo producto/unidad y clasificación real/sintética. Compra posterior a base y dentro de ventana de política (180 días por defecto). Coste incremental como cadena decimal. Reducción bruta = (precio unitario base − actual) × cantidad actual; neta = bruta − coste; ROI % = neta / coste × 100, indefinido con coste cero. No acredita pago ni causalidad. Revocaciones invalidan ROI dependiente.

## 9. Histórico y exportaciones

Abre histórico local y descarga PDF borrador, JSON, alerts.csv o comparisons.csv. El idioma afecta a presentación, no a cifras o evidencias almacenadas. PDF resume hasta 20 alertas y comparaciones; CSV/JSON contienen detalle. Campos máquina y textos de origen se conservan; diagnósticos sin traducción incluyen original español.

## 10. Aprendizaje adaptativo

ALE es un módulo supervisado fuera de línea. Ejecuta pruebas unitarias y estrés sintético abajo. Guarda observaciones y candidatos en SQLite, requiere revisión independiente y separa empresas y datos reales/sintéticos. No aprende automáticamente de facturas subidas a producción ni modifica reglas; no lo uses como decisor autónomo.

```bash
python -m unittest adaptive_learning.test_learning
python -m adaptive_learning.stress --out /tmp/ledger64-ale --seed 20261126
```
## 11. Despliegue

Demo local por HTTP solo loopback. Producción exige HTTPS, BC_ORIGIN y BC_HOSTS correctos, volumen persistente protegido, backup/restauración, aceptación de contenedor y análisis de vulnerabilidades. Se incluyen Compose, Caddy y Railway; no publiques datos privados ni actives infraestructura de pago. Web promocional separada; genera metadatos solo con URL HTTPS verificada.

```bash
docker compose config
docker compose build
# Only after acceptance and with BC_DOMAIN configured:
docker compose up -d
```
## 12. Privacidad y copias

MIT cubre el código original; dependencias conservan licencias. No subas identificadores, documentos empresariales, credenciales, backups, parámetros privados ni registros. Respalda autenticación y bases de empresas por separado, restaura en una empresa nueva y restringe acceso. Cadenas locales, sin anclaje externo. Comunica vulnerabilidades por vía privada.

```bash
python admin.py backup-auth /secure/auth-backup.sqlite3
python admin.py backup COMPANY_ID /secure/company-backup.sqlite3
python admin.py restore-new RECOVERY /secure/company-backup.sqlite3
```
## 13. Solución de problemas

Si falla acceso, revisa host, origen, credenciales y límites de intentos. Si falla importación, revisa plantilla, tipos, divisa, columnas, fechas y límites. OCR: comprueba Tesseract y modelos. PDF: instala Noto CJK, Devanagari y Pango. SQLite: comprueba permisos y espacio; no eludas gobernanza. Ejecuta diagnóstico y comunica incidencia anonimizada con versión, SO y reproducción.

```bash
python scripts/doctor.py
python scripts/check.py
```
[README](../../README.es.md) · [SECURITY](../../SECURITY.md) · [LICENSE](../../LICENSE)
