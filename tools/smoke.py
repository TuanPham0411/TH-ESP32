#!/usr/bin/env python3
import argparse,json,hashlib
from urllib.request import urlopen
p=argparse.ArgumentParser();p.add_argument('--origin',default='http://127.0.0.1:5081');a=p.parse_args()
def get(path):
    with urlopen(a.origin.rstrip('/')+path,timeout=30) as r:
        assert r.status==200;return r.read()
assert json.loads(get('/healthz'))['ok']
for path in ('/','/downloads','/install','/tools'):
    html=get(path);assert b'<!doctype html' in html.lower();assert b'thienha.io.vn' not in html
assert len(json.loads(get('/api/xiaozhi/tools/list'))['tools'])==8
manifest=json.loads(get('/static/xiaozhi/manifest.json'))
assert manifest['builds'][0]['chipFamily']=='ESP32-S3'
firmware=get('/static/xiaozhi/'+manifest['builds'][0]['parts'][0]['path'])
assert hashlib.sha256(firmware).hexdigest()=='c8e77c6e00c9e38dcd8c0b48ee637a8c37d8aa376dbcfa7ac51cd2bad25bba5a'
assert len(get('/static/vendor/installer.js'))>1000
print('PASS: independent pages, public downloads/install, local ESP32 firmware, self-hosted installer and eight public tools')
