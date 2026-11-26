"""Generate canonical and hreflang URLs for a verified public site. Run only after URL is confirmed."""
import sys, re, html
from pathlib import Path
from urllib.parse import urlsplit
from xml.sax.saxutils import escape
u=urlsplit(sys.argv[1]); assert u.scheme=='https' and u.hostname and not u.username and not u.password and not u.query and not u.fragment
base=sys.argv[1].rstrip('/')+'/'
root=Path(__file__).resolve().parents[1]/'site'
pages={'en':'index.html',**{l:l+'.html' for l in ('es','fr','it','de','pt-BR','zh-CN','ja','hi')}}
urls={lang:base+name for lang,name in pages.items()};urls['en']=base
alternates={**urls,'x-default':base}
links=''.join(f'<link rel="alternate" hreflang="{lang}" href="{html.escape(url,quote=True)}">' for lang,url in alternates.items())
for lang,name in pages.items():
 p=root/name;s=p.read_text(encoding='utf-8');s=re.sub(r'<link rel="(?:canonical|alternate)"[^>]*>','',s);s=s.replace('noindex,follow','index,follow');s=s.replace('</head>',f'<link rel="canonical" href="{html.escape(urls[lang],quote=True)}">'+links+'</head>');p.write_text(s,encoding='utf-8')
(root/'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {base}sitemap.xml\n')
entries=''.join('<url><loc>'+escape(url)+'</loc>'+''.join(f'<xhtml:link rel="alternate" hreflang="{l}" href="{html.escape(v,quote=True)}" />' for l,v in alternates.items())+'</url>' for url in urls.values())
(root/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">'+entries+'</urlset>',encoding='utf-8')
