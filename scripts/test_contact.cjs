"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs"), vm = require("node:vm");
const src = fs.readFileSync(require("node:path").join(__dirname,"../site/contact.js"),"utf8");
function simulate(service,scope,consent) {
 let callback, sent=[];
 const elements={commercial:{addEventListener:(name,fn)=>{assert.equal(name,"submit");callback=fn;}},service:{value:service},scale:{value:scope},consent:{checked:consent}};
 vm.runInNewContext(src,{document:{getElementById:id=>elements[id]},window:{location:{assign:url=>sent.push(url)}},URL,Set});
 assert.equal(sent.length,0); let prevented=false; callback({preventDefault:()=>{prevented=true}});assert(prevented); return sent;
}
const valid=simulate("Installation","Single deployment",true);assert.equal(valid.length,1);
const u=new URL(valid[0]);assert.equal(u.origin,"https://github.com");assert.equal(u.pathname,"/OscarMorelli78/Ledger64/issues/new");assert.equal(u.searchParams.get("template"),"commercial.yml");assert.match(u.searchParams.get("objective"),/Single deployment/);
assert.equal(simulate("Installation","Single deployment",false).length,0);
assert.equal(simulate("<script>","Single deployment",true).length,0);
assert.equal(simulate("Installation","private details",true).length,0);
console.log("PASS: 4 form scenarios (valid draft, consent, invalid service, invalid scope); no initial network request");
