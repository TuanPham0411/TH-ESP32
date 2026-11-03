"""Independent, public TH-ESP32 website and XiaoZhi API."""
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import time

from flask import Flask, abort, jsonify, redirect, render_template, request, send_file
from auth import configure, connect, user, valid_csrf
from xiaozhi_tools import register_xiaozhi_tools, TOOLS
from html_content import sanitize

ROOT=Path(__file__).resolve().parent
RELEASES=ROOT/'releases'
app=Flask(__name__,root_path=str(Path(__file__).resolve().parent))
configure(app,os.environ.get('DATA_DIR',str(ROOT.parent/'data')))
with app.app_context(),connect() as connection:
    connection.execute('CREATE TABLE IF NOT EXISTS pages(name TEXT PRIMARY KEY,html TEXT NOT NULL)')
    connection.execute('CREATE TABLE IF NOT EXISTS page_revisions(id INTEGER PRIMARY KEY,html TEXT NOT NULL,editor_id INTEGER NOT NULL REFERENCES users(id),created_at INTEGER NOT NULL)')
    connection.execute('CREATE TABLE IF NOT EXISTS devices(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,mac TEXT NOT NULL,sid TEXT NOT NULL,name TEXT NOT NULL,created_at INTEGER NOT NULL,UNIQUE(user_id,mac))')


def artifacts():
    return json.loads((RELEASES/'catalog.json').read_text())


def validate_artifacts():
    if not (ROOT/'static/vendor/installer.js').is_file():
        raise RuntimeError('Installer bundle missing; run npm ci and npm run build in frontend/')
    for artifact in artifacts():
        name=artifact['filename']
        if Path(name).name!=name:
            raise RuntimeError('Invalid release filename')
        path=RELEASES/name
        if not path.is_file():
            raise RuntimeError('Release missing: '+name)
        with path.open('rb') as stream:
            actual=hashlib.file_digest(stream,'sha256').hexdigest()
        if actual!=artifact['sha256']:
            raise RuntimeError('Release verification failed: '+name)


validate_artifacts()


def is_admin():
    account=user()
    allowed={value.strip().casefold() for value in os.environ.get('ADMIN_EMAILS','').split(',') if value.strip()}
    return bool(account and account['email'].casefold() in allowed)


@app.context_processor
def project_context():
    return {'api_base':app.config['PUBLIC_URL'] or request.url_root.rstrip('/'),'admin_user':is_admin()}


@app.get('/')
def home():
    edit_mode=is_admin() and request.args.get('edit')=='1'
    with connect() as connection:
        content=connection.execute("SELECT html FROM pages WHERE name='guide'").fetchone()
    return render_template('xiaozhi_custom.html' if content else 'xiaozhi_project.html',content_html=content['html'] if content else '',edit_mode=edit_mode)


@app.get('/projects/xiaozhi-esp32')
def legacy_project():
    return redirect('/')


@app.post('/admin/xiaozhi-page/save')
def save_guide():
    if not is_admin():abort(403)
    if not valid_csrf():abort(400)
    body=request.get_json(silent=True)
    content=body.get('content_html') if isinstance(body,dict) else None
    if not isinstance(content,str) or not content.strip() or len(content)>1_500_000:abort(400)
    cleaned=sanitize(content)
    with connect() as connection:
        previous=connection.execute("SELECT html FROM pages WHERE name='guide'").fetchone()
        if previous:connection.execute('INSERT INTO page_revisions(html,editor_id,created_at) VALUES(?,?,?)',(previous['html'],user()['id'],int(time.time())))
        connection.execute("INSERT INTO pages VALUES('guide',?) ON CONFLICT(name) DO UPDATE SET html=excluded.html",(cleaned,))
    return jsonify(ok=True)


@app.post('/admin/xiaozhi-page/reset')
def reset_guide():
    if not is_admin():abort(403)
    if not valid_csrf():abort(400)
    with connect() as connection:
        previous=connection.execute("SELECT html FROM pages WHERE name='guide'").fetchone()
        if previous:connection.execute('INSERT INTO page_revisions(html,editor_id,created_at) VALUES(?,?,?)',(previous['html'],user()['id'],int(time.time())))
        connection.execute("DELETE FROM pages WHERE name='guide'")
    return redirect('/?edit=1')


@app.get('/downloads')
def downloads():
    return render_template('downloads.html',artifacts=artifacts())


@app.get('/install')
@app.get('/projects/xiaozhi-esp32/install')
def install():
    return render_template('install.html')


@app.get('/downloads/<filename>')
@app.get('/api/xiaozhi/firmware/download/<filename>')
def download(filename):
    artifact=next((entry for entry in artifacts() if entry['filename']==filename),None)
    if not artifact:
        abort(404)
    response=send_file(RELEASES/filename,as_attachment=True,download_name=filename)
    response.headers['X-Checksum-SHA256']=artifact['sha256']
    return response


@app.get('/download/xiaozhi-release')
def release_zip():
    return redirect('/downloads/xiaozhi-copper-robot-2.4.0-complete.zip')


@app.get('/tools')
def tools():
    return render_template('tools.html',tools=TOOLS)


@app.get('/account')
def account():
    if not user():
        return redirect('/login?next=/account')
    return render_template('account.html')


@app.get('/api/devices')
@app.get('/api/xiaozhi/account/access')
def devices():
    if not user():
        return jsonify(ok=False,error='Google login required'),401
    with connect() as connection:
        rows=[dict(row) for row in connection.execute('SELECT id,mac,sid,name FROM devices WHERE user_id=? ORDER BY id',(user()['id'],))]
    return jsonify(ok=True,free=True,robots=rows,tools=list(TOOLS))


@app.post('/api/devices')
def bind_device():
    if not user():
        return jsonify(ok=False,error='Google login required'),401
    body=request.get_json(silent=True)
    if not isinstance(body,dict) or not valid_csrf(body.get('csrf')):
        return jsonify(ok=False,error='Invalid CSRF token'),400
    mac=str(body.get('mac','')).upper().replace('-',':').strip()
    if not re.fullmatch(r'(?:[0-9A-F]{2}:){5}[0-9A-F]{2}',mac):
        return jsonify(ok=False,error='Địa chỉ MAC không hợp lệ'),400
    sid=body.get('sid') or secrets.token_urlsafe(18)
    if not isinstance(sid,str) or not re.fullmatch(r'[A-Za-z0-9._:-]{8,80}',sid):
        return jsonify(ok=False,error='SID không hợp lệ'),400
    name=str(body.get('name','Robot XiaoZhi')).strip()[:80]
    with connect() as connection:
        connection.execute('INSERT INTO devices(user_id,mac,sid,name,created_at) VALUES(?,?,?,?,?) ON CONFLICT(user_id,mac) DO UPDATE SET sid=excluded.sid,name=excluded.name',(user()['id'],mac,sid,name,int(time.time())))
    return jsonify(ok=True)


@app.delete('/api/devices/<int:device_id>')
def unbind_device(device_id):
    if not user():
        return jsonify(ok=False,error='Google login required'),401
    if not valid_csrf():
        return jsonify(ok=False,error='Invalid CSRF token'),400
    with connect() as connection:
        changed=connection.execute('DELETE FROM devices WHERE id=? AND user_id=?',(device_id,user()['id'])).rowcount
    if not changed:
        abort(404)
    return jsonify(ok=True)


@app.get('/healthz')
def health():
    with connect() as connection:
        connection.execute('SELECT 1 FROM users LIMIT 1')
    return jsonify(ok=True,service='th-esp32',revision=os.environ.get('APP_REVISION','development'))


register_xiaozhi_tools(app)
if __name__=='__main__':
    app.run(host='127.0.0.1',port=5000)
