"""Presentation-only localization; stored reports and API codes remain unchanged."""
import csv, json, re, html
from pathlib import Path
from html.parser import HTMLParser
BASE=Path(__file__).parent
with (BASE/'locales/strings.tsv').open(encoding='utf-8',newline='') as f:
    rows=list(csv.reader(f,delimiter='\t'))
LANGS=tuple(rows[0]); CATALOG={l:{r[0]:r[i] for r in rows[1:]} for i,l in enumerate(LANGS)}
LABELS={'en':'English','es':'Español','fr':'Français','it':'Italiano','de':'Deutsch','pt-BR':'Português (Brasil)','zh-CN':'简体中文','ja':'日本語','hi':'हिन्दी'}

def locale(req):
    # Explicit selection persists. Default English; no change to authentication.
    value=req.cookies.get('ledger64_lang','en')
    return value if value in LANGS else 'en'

def tr(s,lang='en'):
    mapping=CATALOG.get(lang,CATALOG['en'])
    if s in mapping:return mapping[s]
    match=re.fullmatch(r'Precio unitario \+([0-9.]+)%; verificar condiciones\.',s)
    return mapping['Precio unitario +{n}%; verificar condiciones.'].replace('{n}',match[1]) if match else s

def diagnostic(s,lang='en',depth=0):
    # Preserve the precise original error in API `error`. Translate known dynamic prefixes
    # and leave original third-party diagnostics as explicit technical detail.
    if lang=='es' or s in CATALOG[lang]:return tr(s,lang)
    if depth<4:
        m=re.fullmatch(r'Fila ([0-9]+): (.*)',s,re.DOTALL)
        if m:return tr('Fila',lang)+' '+m[1]+': '+diagnostic(m[2],lang,depth+1)
        a,sep,b=s.partition(': ')
        if sep:
            if a in CATALOG[lang]:return tr(a,lang)+': '+b
            if b in CATALOG[lang] or b.startswith('Fila '):return a+': '+diagnostic(b,lang,depth+1)
    return tr('Operación rechazada. Consulta el diagnóstico original.',lang)+' ('+s+')'

class Localizer(HTMLParser):
    def __init__(self,lang):
        super().__init__(convert_charrefs=False); self.lang=lang; self.out=[]; self.literal=0
    def handle_decl(self,s):self.out.append('<!'+s+'>')
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.literal+=1
        a=[]
        for k,v in attrs:
            if v is not None:
                if k in ('placeholder','aria-label','title'):v=tr(v,self.lang)
                if tag=='html' and k=='lang':v=self.lang
                a.append(f'{k}="{html.escape(v,quote=True)}"')
            else:a.append(k)
        self.out.append('<'+tag+(' '+' '.join(a) if a else '')+'>')
        if tag=='header':
            options=''.join(f'<option value="{k}"'+(' selected' if k==self.lang else '')+'>'+html.escape(v)+'</option>' for k,v in LABELS.items())
            self.out.append('<select id="ledger_language" aria-label="'+html.escape(tr('Language / Idioma',self.lang),quote=True)+'">'+options+'</select>')
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.literal-=1
        self.out.append('</'+tag+'>')
    def handle_data(self,s):
        if self.literal or not s.strip():self.out.append(s);return
        v=tr(s.strip(),self.lang);self.out.append(s[:len(s)-len(s.lstrip())]+html.escape(v)+s[len(s.rstrip()):])
    def handle_entityref(self,s):self.out.append('&'+s+';')
    def handle_charref(self,s):self.out.append('&#'+s+';')
    def handle_comment(self,s):self.out.append('<!--'+s+'-->')

def localize_html(source,lang):
    p=Localizer(lang);p.feed(source);p.close();return ''.join(p.out)

def localize_js(source,lang):
    # Translate only complete string literals, not keys, identifiers, source documents or evidence.
    mapping=CATALOG[lang]
    def replace(m):
        value=m[1];core=value.strip()
        if core not in mapping or core in ('PENDING','APPROVED','REJECTED','REVOKED','DUPLICADO_POSIBLE','ID_CONFLICTIVO','DESCUADRE','SUBIDA_PRECIO','CONTRASTE_ARITMETICO_SUPERADO'):return m[0]
        return json.dumps(value[:len(value)-len(value.lstrip())]+mapping[core]+value[len(value.rstrip()):],ensure_ascii=False)
    # Match complete quoted JS literals; skip escaped literals to preserve source semantics.
    result=re.sub(r"'((?:[^'\\\n]|\\.)*)'",replace,source).replace("'es-ES'",json.dumps({'es':'es-ES','en':'en-GB','fr':'fr-FR','it':'it-IT','de':'de-DE','pt-BR':'pt-BR','zh-CN':'zh-CN','ja':'ja-JP','hi':'hi-IN'}[lang]))

    prefix='globalThis.ledgerTr=(s)=>{const m='+client_catalog(lang)+';if(Object.prototype.hasOwnProperty.call(m,s))return m[s];const x=typeof s==="string"&&s.match(/^Precio unitario \\+([0-9.]+)%; verificar condiciones\\.$/);return x?m["Precio unitario +{n}%; verificar condiciones."].replace("{n}",x[1]):s};'
    return result.replace("'use strict';","'use strict';"+prefix,1)

def client_catalog(lang):
    return json.dumps(CATALOG[lang],ensure_ascii=False,separators=(',',':'))
