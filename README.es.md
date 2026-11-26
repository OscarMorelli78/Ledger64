# Ledger64

**Aprende de cada factura. Haz que cada decisión cuente.**

Auditoría de facturas, comparación de costes de compra y gobernanza financiera de código abierto para pymes. Interfaz inspirada en C64 y procesamiento local sin IA externa.

[English](README.en.md) · [Español](README.es.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [हिन्दी](README.hi.md)

**Versión candidata: utiliza solo datos sintéticos. No certifica contabilidad ni impuestos. Solo compras en EUR; sin abonos. ALE es experimental y fuera de línea. Docker y despliegue alojado requieren aceptación independiente.**

## Inicio rápido

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


## Documentación

[Español — Documentación](docs/manual/es.md) · [MIT](LICENSE) · [SECURITY](SECURITY.md)

### Formato de entrada

Empieza con la demostración sintética. La plantilla estándar tiene once campos, indicados abajo; fecha ISO AAAA-MM-DD, unidades kg, l, ud (g y ml se normalizan), precios en EUR sin IVA. Cantidad positiva y total neto más portes menos descuento. CSV UTF-8, XLSX de una hoja sin fórmulas, macros ni enlaces externos, o PDF estructurado compatible. Máximo 2 MB por archivo, 10.000 líneas; lotes de 2–20 y 8 MB total. No admite indiscriminadamente facturas ni modelos fiscales.

### Auditoría y comparación

Ejecuta Analizar archivo. Examina descuadres, posibles duplicados y subidas de precio de al menos 10 %. IDs repetidos conflictivos e importes descuadrados quedan fuera de comparación. Compara productos idénticos, unidades iguales y observaciones recientes dentro de 30 días. Ahorro potencial no equivale a ahorro pagado o realizado. El coste mensual incluye solo filas elegibles.

### Gobernanza

Propón códigos de equivalencia o ahorros declarados con evidencia y referencias distintas de base y compra. Otro propietario aprueba o rechaza; no hay autoaprobación. Los informes ordinarios son borradores. Solicita liberar informes reales (no sintéticos), con contraste aritmético favorable y revisor independiente. Liberación aprobada solo en JSON. Conserva cadena local y evidencias.

### Aprendizaje adaptativo

ALE es un módulo supervisado fuera de línea. Ejecuta pruebas unitarias y estrés sintético abajo. Guarda observaciones y candidatos en SQLite, requiere revisión independiente y separa empresas y datos reales/sintéticos. No aprende automáticamente de facturas subidas a producción ni modifica reglas; no lo uses como decisor autónomo.

### Privacidad y copias

MIT cubre el código original; dependencias conservan licencias. No subas identificadores, documentos empresariales, credenciales, backups, parámetros privados ni registros. Respalda autenticación y bases de empresas por separado, restaura en una empresa nueva y restringe acceso. Cadenas locales, sin anclaje externo. Comunica vulnerabilidades por vía privada.


## Community & professional services

[Commercial services](COMMERCIAL.md) · [Support](SUPPORT.md) · [Roadmap](ROADMAP.md) · [Contact](CONTACT.md) · [Contribute worldwide](COLLABORATORS.md)
