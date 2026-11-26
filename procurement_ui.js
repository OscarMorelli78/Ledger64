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
$('source').onchange=()=>{$('table-editor').replaceChildren();$('candidate').value='';$('evidence').value='';$('extraction').textContent='';};
$('extract').onclick=()=>action($('extract'),async()=>{$('candidate').value='';$('extraction').textContent='';$('table-editor').replaceChildren();$('source').disabled=true;try{const r=await request('extract',{...await source(),strategy:$('strategy').value});$('extraction').textContent=JSON.stringify(r,null,2);if(r.proposal?.candidate)$('candidate').value=JSON.stringify(r.proposal.candidate,null,2);renderTables(r)}finally{$('source').disabled=false}});
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

function renderTables(result){
  const root=$('table-editor');root.replaceChildren();
  for(const [index,draft] of (result.structured_tables||[]).entries()){
    if(!Array.isArray(draft.cells)||!draft.cells.length)continue;
    const section=document.createElement('section'), heading=document.createElement('h3');
    heading.textContent='Review table '+(index+1)+' · page '+draft.page;section.append(heading);
    const table=document.createElement('table'),inputs=[];
    for(const [i,row] of draft.cells.entries()){
      const tr=document.createElement('tr'),cells=[];
      for(const [j,value] of row.entries()){
        const td=document.createElement(i===0?'th':'td'),input=document.createElement('input');
        input.value=value;input.setAttribute('aria-label','Row '+(i+1)+' column '+(j+1));input.maxLength=2000;
        input.oninput=()=>{$('candidate').value='';};
        td.append(input);tr.append(td);cells.push(input);
      }
      inputs.push(cells);table.append(tr);
    }
    const scroll=document.createElement('div');scroll.style.overflowX='auto';scroll.append(table);section.append(scroll);
    const metadata={};
    for(const [key,label] of [['kind','Kind (order / receipt / invoice)'],['id','Document ID'],['supplier','Supplier'],['date','Date YYYY-MM-DD'],['currency','Currency EUR']]){
      const l=document.createElement('label'),input=document.createElement('input');l.textContent=label+' ';input.maxLength=160;
      if(key==='currency')input.value='EUR';
      input.oninput=()=>{$('candidate').value='';};l.append(input);section.append(l);metadata[key]=input;
    }
    const l=document.createElement('label'),mapping=document.createElement('textarea');l.textContent='Exact column mapping JSON (canonical fields → reviewed headers)';
    mapping.rows=4;mapping.placeholder='{"id":"Line","sku":"SKU","unit":"Unit","quantity":"Qty", ...}';
    mapping.oninput=()=>{$('candidate').value='';};l.append(mapping);section.append(l);
    const b=document.createElement('button');b.textContent='Build unapproved proposal';
    b.onclick=()=>action(b,async()=>{
      $('candidate').value='';$('source').disabled=true;
      try{
        const cells=inputs.map(row=>row.map(input=>input.value));
        const meta=Object.fromEntries(Object.entries(metadata).map(([k,input])=>[k,input.value]));
        const r=await request('table-propose',{...await source(),source_sha256:result.source_sha256,
          table:{page:draft.page,status:'REVIEW_REQUIRED',cells},metadata:meta,mapping:JSON.parse(mapping.value)});
        $('candidate').value=JSON.stringify(r.candidate,null,2);
        $('extraction').textContent=JSON.stringify(r,null,2);
      }finally{$('source').disabled=false}
    });section.append(b);root.append(section);
  }
}
