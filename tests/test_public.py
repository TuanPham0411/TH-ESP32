import hashlib
from pathlib import Path
from unittest.mock import patch
from test_auth import ApplicationTest

class PublicWebsiteTests(ApplicationTest):
    def test_public_pages_and_downloads_without_login(self):
        for path in ('/','/downloads','/install','/tools','/api/xiaozhi/health','/api/xiaozhi/tools/list','/healthz'):
            with self.subTest(path=path):self.assertEqual(self.client.get(path).status_code,200)
        for path in ('/static/vendor/installer.js','/static/vendor/THIRD_PARTY_NOTICES.txt'):
            response=self.client.get(path)
            self.assertEqual(response.status_code,200)
            response.close()
        for artifact in self.module.artifacts():
            response=self.client.get('/downloads/'+artifact['filename'])
            self.assertEqual(response.status_code,200)
            self.assertEqual(hashlib.sha256(response.data).hexdigest(),artifact['sha256'])
            self.assertEqual(response.headers['X-Checksum-SHA256'],artifact['sha256'])
            response.close()
        self.assertEqual(self.client.get('/downloads/../auth.py').status_code,404)
        self.assertEqual(self.client.get('/unlock/1').status_code,404)
        self.assertEqual(self.client.post('/purchase-services').status_code,404)

    def test_tools_do_not_require_bearer_token_or_subscription(self):
        import xiaozhi_tools
        with patch.object(xiaozhi_tools,'_search',return_value={'ok':True,'summary_vi':'local mock result'}):
            response=self.client.post('/api/xiaozhi/tools/call',json={'name':'search_web','arguments':{'query':'ESP32'}})
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.json['ok'])
        self.assertTrue(response.json['session_id'])
        self.assertEqual(self.client.post('/api/xiaozhi/tools/call',json=['bad']).status_code,400)
        self.assertEqual(self.client.post('/api/xiaozhi/tools/call',json={'name':'search_web','arguments':{'limit':'bad'}}).status_code,400)
        with patch.dict('os.environ',{'OPENAI_API_KEY':''}):
            self.assertEqual(self.client.post('/api/xiaozhi/tools/call',json={'name':'chat_with_gpt','arguments':{'query':'hello'}}).status_code,503)

    def test_devices_are_private_and_csrf_protected_but_not_licensed(self):
        self.assertEqual(self.client.get('/api/devices').status_code,401)
        self.google_login()
        with self.client.session_transaction() as session:csrf=session['csrf']
        payload={'mac':'AA:BB:CC:DD:EE:FF','name':'My device','csrf':csrf}
        self.assertEqual(self.client.post('/api/devices',json=dict(payload,csrf='wrong')).status_code,400)
        self.assertEqual(self.client.post('/api/devices',json=payload).status_code,200)
        data=self.client.get('/api/devices').json
        self.assertTrue(data['free']);self.assertEqual(len(data['robots']),1)
        device_id=data['robots'][0]['id']
        another=self.app.test_client();self.google_login(client=another,sub='another-google-user',email='another@example.invalid')
        self.assertEqual(another.get('/api/devices').json['robots'],[])
        with another.session_transaction() as session:other_csrf=session['csrf']
        self.assertEqual(another.delete('/api/devices/'+str(device_id),headers={'X-CSRF-Token':other_csrf}).status_code,404)
        self.assertEqual(self.client.delete('/api/devices/'+str(device_id),headers={'X-CSRF-Token':csrf}).status_code,200)

    def test_no_old_hostname_in_runtime_pages_or_scripts(self):
        for path in (self.module.ROOT/'templates',self.module.ROOT/'static'):
            for file in path.rglob('*'):
                if file.suffix in ('.html','.js','.md'):
                    self.assertNotIn('thienha.io.vn',file.read_text(),str(file))

    def test_guide_editor_is_owner_only_and_strips_executable_html(self):
        payload={'content_html':'<section><h1>Standalone guide</h1><script>bad()</script><a href="javascript:bad()" onclick="bad()">Link</a><svg viewBox="0 0 10 10"><path d="M0 0L1 1"/></svg></section>'}
        self.assertEqual(self.client.post('/admin/xiaozhi-page/save',json=payload).status_code,403)
        self.google_login()
        self.assertEqual(self.client.post('/admin/xiaozhi-page/save',json=payload).status_code,403)
        with patch.dict('os.environ',{'ADMIN_EMAILS':'person@example.invalid'}):
            self.assertEqual(self.client.post('/admin/xiaozhi-page/save',json=payload).status_code,400)
            with self.client.session_transaction() as session:csrf=session['csrf']
            response=self.client.post('/admin/xiaozhi-page/save',json=payload,headers={'X-CSRF-Token':csrf})
            self.assertEqual(response.status_code,200)
            page=self.client.get('/').data.decode()
            self.assertIn('Standalone guide',page)
            self.assertNotIn('javascript:',page)
            self.assertNotIn('onclick="bad()',page)
            self.assertNotIn('bad()',page)
            self.assertIn('viewBox="0 0 10 10"',page)
            self.assertIn('</path>',page)
            self.assertEqual(self.client.post('/admin/xiaozhi-page/reset',data={'csrf':csrf}).status_code,302)
            self.assertIn(b'XiaoZhi Copper Robot',self.client.get('/').data)
