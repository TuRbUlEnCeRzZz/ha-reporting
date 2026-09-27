const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../ha-reporting/app/app.js'),'utf8');
const elements=new Map();
function element(id){if(!elements.has(id))elements.set(id,{textContent:'',innerHTML:'',className:'',classList:{contains:()=>false,add(){}},contains:()=>false,querySelectorAll:()=>[]});return elements.get(id);}
let timer=null, timerDelay=null;
const sandbox={document:{hidden:false,activeElement:null},$:element,Date,AbortSignal,Set,clearTimeout(){timer=null;},setTimeout(fn,ms){timer=fn;timerDelay=ms;return 1;},scheduledAutomations:[],reports:[],launchingAutomations:new Set(),automationLaunchErrors:new Map(),toastTimer:null,automationPollTimer:null,automationLoadPromise:null,visibleAutomationHistory:null,fetch:async()=>({ok:true,json:async()=>({automations:[]})})};
vm.createContext(sandbox);
for(const name of ['esc','formatAutomationDuration','automationStatusLabel','automationStatusClass','automationScheduleLabel','automationAiLabel','formatAutomationDate','automationTriggerLabel','automationIsActive','renderPipelineProgress','showToast','loadScheduledAutomations','runScheduledAutomationNow','scheduleAutomationRefresh','renderScheduledAutomations']){
 const match=source.match(new RegExp(`^(?:async )?function ${name}\\([^]*?^}`,'m'));assert.ok(match,name);vm.runInContext(match[0],sandbox);
}
let checks=0;async function check(fn){await fn();checks++;}
(async()=>{
 await check(()=>assert.equal(sandbox.formatAutomationDuration(null),'—'));
 await check(()=>assert.equal(sandbox.formatAutomationDuration(59.9),'1 min 00 s'));
 await check(()=>assert.equal(sandbox.automationIsActive({progress:{status:'ai_running'},runtime:{last_status:'completed'}}),true));
 await check(()=>assert.equal(sandbox.automationIsActive({progress:{status:'completed_with_errors'}}),false));
 const job={status:'error',steps:{data:{state:'completed'},ai:{state:'skipped'},pdf:{state:'error'},export:{state:'pending'}}};
 await check(()=>{const html=sandbox.renderPipelineProgress(job);assert.match(html,/Désactivé/);assert.match(html,/Échec/);assert.match(html,/Non exécuté/);assert.doesNotMatch(html,/undefined/);});
 await check(()=>assert.doesNotMatch(sandbox.renderPipelineProgress({status:'<script>',steps:{}}),/<script>/));
 await check(()=>assert.match(sandbox.renderPipelineProgress({status:'exporting',steps:{notification:{state:'running'}}}),/<strong>Notification<\/strong>/));
 await check(()=>{sandbox.scheduledAutomations=[{progress:{status:'ai_running'}}];sandbox.scheduleAutomationRefresh();assert.equal(timerDelay,3000);});
 await check(()=>{sandbox.scheduledAutomations=[];sandbox.scheduleAutomationRefresh();assert.equal(timerDelay,15000);});
 await check(()=>{sandbox.document.hidden=true;sandbox.scheduleAutomationRefresh();assert.equal(timer,null);sandbox.document.hidden=false;});
 await check(async()=>{sandbox.fetch=async()=>{throw Error('offline');};sandbox.scheduleAutomationRefresh();await timer();assert.match(element('automationRefreshStatus').textContent,/Connexion interrompue/);assert.equal(typeof timer,'function');});
 await check(async()=>{let calls=0,release;sandbox.fetch=()=>{calls++;return new Promise(r=>release=r);};const a=sandbox.loadScheduledAutomations(),b=sandbox.loadScheduledAutomations();release({ok:true,json:async()=>({automations:[]})});await Promise.all([a,b]);assert.equal(calls,1);});
 await check(async()=>{let posts=0;sandbox.scheduledAutomations=[{id:'a',enabled:true,pipeline:{},retry:{},runtime:{}}];sandbox.fetch=async(url,options)=>{if(options.method==='POST'){posts++;return{ok:true,json:async()=>({job:{id:'j',status:'queued'}})};}throw Error('offline');};await sandbox.runScheduledAutomationNow('a');assert.equal(posts,1);assert.equal(element('appToast').textContent,'Rapport lancé');assert.equal(sandbox.scheduledAutomations[0].progress.status,'queued');assert.equal(sandbox.launchingAutomations.size,0);});
 await check(async()=>{sandbox.launchingAutomations.add('a');sandbox.fetch=()=>{throw Error('should not POST');};await sandbox.runScheduledAutomationNow('a');sandbox.launchingAutomations.clear();});
 await check(async()=>{sandbox.fetch=async()=>{throw Error('timeout');};await sandbox.runScheduledAutomationNow('a');assert.match(element('appToast').textContent,/peut-être démarré/);assert.equal(sandbox.launchingAutomations.size,0);});
 await check(()=>{const run=source.match(/^async function runScheduledAutomationNow\([^]*?^}/m)[0];assert.doesNotMatch(run,/alert\(/);});
 console.log(`${checks} beta.18 UI checks passed`);
})().catch(error=>{console.error(error);process.exitCode=1;});
