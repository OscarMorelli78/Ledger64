"use strict";
const $=id=>document.getElementById(id);
const token=document.querySelector('meta[name=csrf]').content;
async function request(path,data){
  const res=await fetch('/procurement/api/'+path,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':token},body:JSON.stringify(data)});
  const obj=await res.json();if(!res.ok)throw Error(obj.error||'Error');return obj;
}
async function source(){
  const f=$('source').files[0];if(!f||f.size>2000000)throw Error('Choose a synthetic document up to 2 MB');
  const bytes=new Uint8Array(await f.arrayBuffer());let binary='';
  for(let i=0;i<bytes.length;i+=16384)binary+=String.fromCharCode(...bytes.subarray(i,i+16384));
  return {source:btoa(binary),suffix:f.name.slice(f.name.lastIndexOf('.')).toLowerCase()};
}
async function action(button,fn){button.disabled=true;try{await fn();$('status').textContent='OK / Correcto'}catch(e){$('status').textContent=e.message}finally{button.disabled=false}}
$('extract').onclick=()=>action($('extract'),async()=>{const r=await request('extract',await source());$('extraction').textContent=JSON.stringify(r,null,2);if(r.proposal?.candidate)$('candidate').value=JSON.stringify(r.proposal.candidate,null,2)});
$('submit').onclick=()=>action($('submit'),async()=>{await request('submit',{...await source(),candidate:JSON.parse($('candidate').value),evidence:$('evidence').value});await refresh()});
async function refresh(){
  const cases=await request('cases');const root=$('cases');root.replaceChildren();
  for(const item of cases){
    const box=document.createElement('article');const title=document.createElement('h3');title.textContent=item.candidate.kind+' · '+item.candidate.id+' · '+item.status;box.append(title);
    const pre=document.createElement('pre');pre.textContent=JSON.stringify(item,null,2);box.append(pre);
    const link=document.createElement('a');link.href='/procurement/api/source/'+encodeURIComponent(item.id);link.textContent='Download original for independent review';box.append(link);
    if(item.status==='PENDING'){
      const input=document.createElement('textarea');input.placeholder='Independent verification evidence';input.rows=2;box.append(input);
      for(const decision of ['APPROVED','REJECTED']){
        const b=document.createElement('button');b.textContent=decision;
        b.onclick=()=>action(b,async()=>{await request('review',{id:item.id,decision,evidence:input.value});await refresh()});box.append(b)
      }
    }
    root.append(box)
  }
}
$('refresh').onclick=()=>action($('refresh'),refresh);
$('date').value=new Date().toISOString().slice(0,10);
$('report').onclick=()=>action($('report'),async()=>{$('results').textContent=JSON.stringify(await request('report',{as_of:$('date').value,tolerances:{quantity:$('quantity').value,amount:$('amount').value,price_pct:$('price').value}}),null,2)});
refresh().catch(e=>$('status').textContent=e.message);
