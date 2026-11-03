var s=async t=>{let n;import("./chunks/install-dialog-im156JnI-AYDZQ7Z7.js").then((function(e){return e.i}));try{n=await navigator.serial.requestPort()}catch(e){return e.name==="NotFoundError"?void import("./chunks/index-Dt9w-IG1-PVF6HDQJ.js").then((i=>i.openNoPortPickedDialog((()=>s(t))))):void alert(`Error: ${e.message}`)}if(!n)return;try{await n.open({baudRate:115200,bufferSize:8192})}catch(e){return void alert(e.message)}let o=document.createElement("ewt-install-dialog");o.port=n,o.manifestPath=t.manifest||t.getAttribute("manifest"),o.overrides=t.overrides,o.addEventListener("closed",(()=>{n.close()}),{once:!0}),document.body.appendChild(o)},r=class t extends HTMLElement{connectedCallback(){if(this.renderRoot)return;if(this.renderRoot=this.attachShadow({mode:"open"}),!t.isSupported||!t.isAllowed)return this.toggleAttribute("install-unsupported",!0),void(this.renderRoot.innerHTML=t.isAllowed?"<slot name='unsupported'>Your browser does not support installing things on ESP devices. Use Mozilla Firefox, Google Chrome or Microsoft Edge.</slot>":"<slot name='not-allowed'>You can only install ESP devices on HTTPS websites or on the localhost.</slot>");this.toggleAttribute("install-supported",!0);let n=document.createElement("slot");n.addEventListener("click",(async e=>{e.preventDefault(),s(this)})),n.name="activate";let o=document.createElement("button");if(o.innerText="Connect",n.append(o),"adoptedStyleSheets"in Document.prototype&&"replaceSync"in CSSStyleSheet.prototype){let e=new CSSStyleSheet;e.replaceSync(t.style),this.renderRoot.adoptedStyleSheets=[e]}else{let e=document.createElement("style");e.innerText=t.style,this.renderRoot.append(e)}this.renderRoot.append(n)}};r.isSupported="serial"in navigator,r.isAllowed=window.isSecureContext,r.style=`
  button {
    position: relative;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    padding: 10px 24px;
    color: var(--esp-tools-button-text-color, #fff);
    background-color: var(--esp-tools-button-color, #03a9f4);
    border: none;
    border-radius: var(--esp-tools-button-border-radius, 9999px);
  }
  button::before {
    content: " ";
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    right: 0;
    opacity: 0.2;
    border-radius: var(--esp-tools-button-border-radius, 9999px);
  }
  button:hover::before {
    background-color: rgba(255,255,255,.8);
  }
  button:focus {
    outline: none;
  }
  button:focus::before {
    background-color: white;
  }
  button:active::before {
    background-color: grey;
  }
  :host([active]) button {
    color: rgba(0, 0, 0, 0.38);
    background-color: rgba(0, 0, 0, 0.12);
    box-shadow: none;
    cursor: unset;
    pointer-events: none;
  }
  .hidden {
    display: none;
  }`,customElements.define("esp-web-install-button",r);customElements.whenDefined("esp-web-install-button").then(()=>{let t=document.getElementById("installer-status");t&&(t.textContent="serial"in navigator&&window.isSecureContext?"S\u1EB5n s\xE0ng. Ch\u1ECDn c\u1ED5ng USB \u0111\u1EC3 b\u1EAFt \u0111\u1EA7u.":"Web Serial c\u1EA7n Chrome/Edge desktop qua HTTPS ho\u1EB7c localhost. B\u1EA1n v\u1EABn c\xF3 th\u1EC3 t\u1EA3i g\xF3i offline.")});
