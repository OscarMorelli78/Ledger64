const fs=require('node:fs'), vm=require('node:vm'), assert=require('node:assert/strict');
const base=process.env.BC_TEST_URL||'http://127.0.0.1:18765';
class Element { constructor(){this.children=[];this.textContent='';this.hidden=true;this.files=[];this.disabled=false;} append(x){this.children.push(x)} replaceChildren(){this.children=[]} createTHead(){const x=new Element();this.append(x);return x} createTBody(){return this.createTHead()} insertRow(){return this.createTHead()} insertCell(){return this.createTHead()} }
(async()=>{
const html=await (await fetch(base)).text();const token=html.match(/name="csrf" content="([^"]+)"/)[1];const elements=Object.fromEntries([...html.matchAll(/id="([^"]+)"/g)].map(m=>[m[1],new Element()]));
const context=vm.createContext({document:{getElementById:id=>elements[id],querySelector:()=>({content:token}),createElement:()=>new Element()},btoa,fetch:(url,opts)=>fetch(base+url,opts),console});
const script=await (await fetch(base+'/ui.js')).text();vm.runInContext(script,context);
const check=(name,fn)=>{fn();console.log('PASS '+name)};
await vm.runInContext('history()',context);
await elements.demo.onclick();
check('Demo button calls real backend',()=>assert.equal(elements.status.textContent,'Auditoría completada y guardada localmente.'));
check('Results visible',()=>assert.equal(elements.result.hidden,false));
check('Six rows',()=>assert.equal(elements.rows.textContent,6));
check('Three alerts',()=>assert.equal(elements.alerts.textContent,3));
check('Potential savings 30 EUR',()=>assert.match(elements.saving.textContent,/30,00/));
check('Alerts table populated',()=>assert.equal(elements.alerttable.children[1].children.length,3));
check('Comparison table populated',()=>assert.ok(elements.comparisontable.children[1].children.length>0));
check('Four export links',()=>assert.equal(elements.exports.children.length,4));
for(const a of elements.exports.children){const r=await fetch(base+a.href);check('Export '+a.href.split('/').pop(),()=>{assert.equal(r.status,200);assert.ok(r.headers.get('content-disposition'))});assert.ok((await r.text()).length>0)}
check('History entry created',()=>assert.ok(elements.history.children.length>0));await elements.history.children[0].onclick();check('History reload',()=>assert.equal(elements.status.textContent,'Informe histórico recuperado.'));
await elements.run.onclick();check('Missing CSV error',()=>assert.equal(elements.status.textContent,'Selecciona un archivo.'));
elements.file.files=[Buffer.from('invalid')];await elements.run.onclick();check('Invalid CSV rejected',()=>assert.notEqual(elements.status.textContent,'Auditoría completada y guardada localmente.'));
elements.file.files=[fs.readFileSync(__dirname+'/demo.csv')];await elements.run.onclick();check('CSV upload',()=>assert.equal(elements.status.textContent,'Auditoría completada y guardada localmente.'));check('Imported data label',()=>assert.match(elements.kind.textContent,/DATOS IMPORTADOS/));check('Buttons reenabled',()=>assert.equal(elements.run.disabled||elements.demo.disabled,false));
for(const ext of ['xlsx','pdf']){elements.file.files=[fs.readFileSync(__dirname+'/demo.'+ext)];await elements.run.onclick();check(ext+' upload through UI',()=>assert.equal(elements.status.textContent,'Auditoría completada y guardada localmente.'));check(ext+' savings',()=>assert.match(elements.saving.textContent,/30,00/));}
check('Monthly cost table',()=>assert.equal(elements.monthtable.children[1].children[0].children[1].textContent,'390.00'));
for(const [k,v] of Object.entries({supplier:'Test supplier',sku:'X1',canonical:'COMMON',evidence:'Spec verified in synthetic fixture'}))elements['alias_'+k].value=v;
await elements.alias_save.onclick();check('Alias approval via UI',()=>assert.equal(elements.decision_status.textContent,'Registro guardado.'));check('Alias table populated',()=>assert.equal(elements.aliastable.children[1].children[0].children[2].textContent,'COMMON'));
for(const [k,v] of Object.entries({product:'COMMON',unit:'kg',baseline_reference:'BASE',purchase_reference:'BUY',baseline_price:'12',actual_price:'9',quantity:'10'}))elements['save_'+k].value=v;
await elements.save_record.onclick();check('Savings via UI',()=>assert.equal(elements.decision_status.textContent,'Registro guardado.'));check('Savings calculated',()=>assert.equal(elements.savingtable.children[1].children[0].children[2].textContent,'30.00'));check('Savings not verified',()=>assert.equal(elements.savingtable.children[1].children[0].children[3].textContent,'DECLARADO_NO_VERIFICADO'));
const raw=fs.readFileSync(__dirname+'/demo.csv');const fake=(name)=>({name,size:raw.length,arrayBuffer:async()=>raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.byteLength)});elements.file.files=[fake('a.csv'),fake('b.csv')];await elements.run.onclick();check('Multi-file batch via UI',()=>assert.equal(elements.status.textContent,'Auditoría completada y guardada localmente.'));check('Batch rows',()=>assert.equal(elements.rows.textContent,12));
elements.file.files=[Buffer.from('not a PDF')];await elements.ocr.onclick();check('OCR rejects invalid file via UI',()=>assert.match(elements.status.textContent,/OCR requiere un PDF/));check('OCR draft remains hidden',()=>assert.equal(elements.ocr_panel.hidden,true));
console.log('33 checks passed; simulated DOM, actual JavaScript and HTTP backend; no real browser rendering.');
})().catch(e=>{console.error(e);process.exitCode=1});
