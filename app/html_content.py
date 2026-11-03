"""Restricted HTML for the authenticated owner's guide editor (never executable code)."""
from html import escape
from html.parser import HTMLParser
import re
from urllib.parse import urlsplit

ALLOWED=set('section nav article aside header footer div span h1 h2 h3 h4 h5 p ol ul li dl dt dd a img figure figcaption strong b em i small code pre blockquote table thead tbody tr th td br hr button select option label details summary svg g path rect circle ellipse line polyline polygon text defs marker title'.split())
DROP_CONTENT={'script','style','iframe','object','embed'}
VOID={'img','br','hr'}

class GuideHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output=[];self.suppressed=0
    def handle_starttag(self,tag,attrs):
        if tag in DROP_CONTENT:
            self.suppressed+=1;return
        if self.suppressed or tag not in ALLOWED:return
        safe=[]
        for name,value in attrs:
            if name.startswith('on') or name in {'srcdoc','formaction','contenteditable'}:continue
            value=value or ''
            if name in {'href','src','xlink:href'}:
                normalized=re.sub(r'[\x00-\x20]','',value)
                if urlsplit(normalized).scheme not in ('','http','https'):continue
            if name=='style' and re.search(r'expression|javascript|url\s*\(',value,re.I):continue
            # Restore the SVG attribute casing expected by browsers.
            output_name={'viewbox':'viewBox','markerwidth':'markerWidth','markerheight':'markerHeight','refx':'refX','refy':'refY'}.get(name,name)
            safe.append(f' {output_name}="{escape(value,quote=True)}"')
        self.output.append('<'+tag+''.join(safe)+'>')
    def handle_endtag(self,tag):
        if tag in DROP_CONTENT:
            self.suppressed=max(0,self.suppressed-1);return
        if not self.suppressed and tag in ALLOWED and tag not in VOID:self.output.append('</'+tag+'>')
    def handle_data(self,data):
        if not self.suppressed:self.output.append(escape(data))

def sanitize(content):
    parser=GuideHTML();parser.feed(content);parser.close();return ''.join(parser.output)
