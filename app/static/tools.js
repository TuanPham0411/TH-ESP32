'use strict';
document.getElementById('tool-form').addEventListener('submit',async event=>{
 event.preventDefault();const form=event.currentTarget,button=form.querySelector('button'),output=document.getElementById('tool-result');button.disabled=true;output.textContent='Đang thực hiện…';
 try{const response=await fetch('/api/xiaozhi/tools/call',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:form.elements.tool.value,arguments:{query:form.elements.query.value,limit:5}})});const data=await response.json();output.textContent=data.summary_vi||JSON.stringify(data,null,2)}catch{output.textContent='Chưa thể kết nối công cụ. Vui lòng thử lại.'}finally{button.disabled=false}
});
