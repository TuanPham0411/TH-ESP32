import 'esp-web-tools/dist/web/install-button.js';
customElements.whenDefined('esp-web-install-button').then(()=>{
 const status=document.getElementById('installer-status');
 if(status)status.textContent=('serial' in navigator && window.isSecureContext)?'Sẵn sàng. Chọn cổng USB để bắt đầu.':'Web Serial cần Chrome/Edge desktop qua HTTPS hoặc localhost. Bạn vẫn có thể tải gói offline.';
});
