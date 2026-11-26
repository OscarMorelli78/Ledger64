'use strict';
// No external network, no credentials or company data stored in language preference.
(()=>{const select=document.getElementById('ledger_language');if(!select)return;select.addEventListener('change',()=>{document.cookie='ledger64_lang='+encodeURIComponent(select.value)+'; Path=/; Max-Age=31536000; SameSite=Lax'+(location.protocol==='https:'?'; Secure':'');location.reload()})})();
