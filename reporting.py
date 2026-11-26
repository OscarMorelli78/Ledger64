"""Localized bounded PDF review report; no external resources or network access."""
from html import escape
from i18n import tr, LANGS
from weasyprint import HTML
from weasyprint.urls import URLFetcher

class NoExternalResources(URLFetcher):
    def fetch(self, url, headers=None):
        raise ValueError('External PDF resources prohibited')

CSS='''@page {size:A4; margin:15mm 19mm 22mm; @bottom-left {content: "Ledger64 | " string(report);font-size:8pt;color:#173746;} @bottom-right {content:counter(page);font-size:8pt;}} body{font:9pt/1.45 "Noto Sans","Noto Sans Devanagari","Noto Sans CJK SC","Noto Sans CJK JP",sans-serif;color:#173746} html[lang=ja] body{font-family:"Noto Sans CJK JP","Noto Sans",sans-serif} html[lang=zh-CN] body{font-family:"Noto Sans CJK SC","Noto Sans",sans-serif} html[lang=hi] body{font-family:"Noto Sans Devanagari","Noto Sans",sans-serif} h1{font-size:20pt;margin:2mm 0;string-set:report content()} h2{font-size:13pt;color:#087b68;margin:4mm 0 2mm;break-after:avoid} p{margin:1.5mm 0;overflow-wrap:anywhere} table{width:100%;border-collapse:collapse;table-layout:fixed;font-size:8pt} th,td{padding:2mm;text-align:left;vertical-align:top;border-bottom:.3pt solid #d7e2df;overflow-wrap:anywhere} th{background:#edf5f3} tr{break-inside:avoid} .draft{font-weight:bold}.small{font-size:8pt}'''

def report_pdf(r,lang='es'):
    if lang not in LANGS:lang='en'
    def t(s):return tr(s,lang)
    def e(s):return escape(str(s)[:300] if s is not None else '—')
    def p(s,cls=''):return f'<p class="{cls}">{e(s)}</p>'
    def heading(s):return '<h2>'+e(t(s))+'</h2>'
    def table(headers,rows,widths):
        cols=''.join(f'<col style="width:{w/sum(widths)*100:.3f}%">' for w in widths)
        return '<table><colgroup>'+cols+'</colgroup><thead><tr>'+''.join('<th>'+e(t(x))+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+e(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table>'
    title=t('Informe ejecutivo de compras')
    parts=[f'<h2>LEDGER64 / BUSINESS CONTROL</h2><h1>{e(title)}</h1>',p(t('DATOS SINTÉTICOS · DEMOSTRACIÓN' if r['synthetic'] else 'DATOS IMPORTADOS · SIN VALIDACIÓN EXTERNA')),p(t('BORRADOR DE REVISIÓN · NO APROBADO PARA USO EMPRESARIAL'),'draft'),p(t('Auditoría asistida de costes y proveedores. No certifica cuentas, pagos ni ahorros realizados.')),heading('Resumen')]
    parts.append(table(['Indicador','Resultado'],[[t('Líneas importadas'),r['rows']],[t('Líneas elegibles'),r['eligible_rows']],[t('Incidencias para revisión'),r['review_alerts']],[t('Ahorro potencial estimado (EUR)'),r['potential_saving_eur']],[t('Pérdida confirmada'),t('No acreditada')]],[110,62]))
    parts.extend([heading('Coste por mes'),table(['Periodo','Coste elegible (EUR)'],[[x['month'],x['eligible_cost_eur']] for x in r.get('monthly_costs',{}).get('months',[])[:24]] or [[t('Sin datos'),'—']],[86,86]),heading('Incidencias para revisar'),table(['Tipo','Proveedor / factura','Importe EUR','Acción'],[[t(a['type']),a['supplier']+' / '+a['invoice'],a['amount_eur'],t(a['detail'])] for a in r['alerts'][:20]] or [[t('Sin incidencias'),'—','—','—']],[34,43,23,72]),p(t('Resumen limitado a 20 alertas. Consulta alerts.csv para el detalle completo.'),'small'),heading('Comparación de precios observados'),table(['Producto','Proveedor','EUR/unidad','Referencia','Potencial EUR'],[[a['product'],a['supplier'],a['unit_price_eur'],a['reference_supplier'],a['potential_eur']] for a in r['comparisons'][:20]] or [[t('Sin comparación'),'—','—','—','—']],[36,39,28,39,30]),p(t('Resumen limitado a 20 comparaciones. Los importes son oportunidades, no ahorros realizados.'),'small'),heading('Trazabilidad y límites'),p(t('SHA-256 de origen:')+' '+r['input_sha256'],'small'),p(t('SHA-256 normalizado:')+' '+r.get('normalized_sha256',r['input_sha256']),'small')])
    if r.get('verification'):parts.append(p(t(r['verification']['status'])+' · '+t(r['verification']['scope']),'small'))
    if r.get('manual_review'):parts.append(p(t('Transcripción aprobada por usuario; no verificada independientemente contra el original.'),'small'))
    parts.extend(p('• '+t(x),'small') for x in r.get('limitations',[]))
    # All untrusted values are escaped; no images, hyperlinks, or external CSS.
    html=f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><title>{e(title)}</title><style>{CSS}</style></head><body>'+''.join(parts)+'</body></html>'
    return HTML(string=html,url_fetcher=NoExternalResources()).write_pdf()
