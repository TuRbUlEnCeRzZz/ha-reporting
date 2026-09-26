const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../ha-reporting/app/app.js'), 'utf8');
const sandbox = {};
vm.createContext(sandbox);
for (const name of ['signedValue','esc','formatSeriesNumber','localDateTime','qualityBadge','metricCardData','reportSourceCardData','renderExecutedSource','comparisonStatusLabel','comparisonSourceCard','renderAiAnalysis']) {
  const match = source.match(new RegExp(`^function ${name}\\([^]*?^}`, 'm'));
  assert.ok(match, name);
  vm.runInContext(match[0], sandbox);
}
let checks = 0;
function check(fn) { fn(); checks++; }
const raw = {status:'ok', sensor_key:'compressor', entity_id:'sensor.compressor', metric:'runtime',unit:'h', points:1506,retrieval_mode:'series_fallback',analysis:{quality:{period_coverage_percent:1.3,density_applicable:false,sample_density_percent:null},statistics:{delta:20.152,plausible:true,anomalies_ignored:2,resets_detected:0},validation:{valid:true,warnings:['Diagnostic conservé']}}};
check(() => assert.match(sandbox.renderExecutedSource(raw,{duration_seconds:86400}), /points bruts/));
check(() => assert.match(sandbox.renderExecutedSource(raw,{duration_seconds:86400}), /densité n\/a/));
check(() => assert.match(sandbox.renderExecutedSource(raw,{duration_seconds:86400}), /1506 point/));
check(() => assert.match(sandbox.renderExecutedSource(raw,{duration_seconds:86400}), /Diagnostic conservé/));
const verified = {...raw,retrieval_mode:'provider_rollup',verification:{classification:'minor_corrections',diagnostic:{negative_transitions:2}},analysis:{quality:raw.analysis.quality,statistics:{delta:20.152,plausible:true,anomalies_ignored:0,resets_detected:0,minor_corrections_accepted:2},validation:{valid:true,warnings:[]}}};
check(() => assert.match(sandbox.renderExecutedSource(verified,{duration_seconds:86400}), /correction\(s\) mineure\(s\).*fallback évité/));
check(() => assert.match(sandbox.renderExecutedSource(verified,{duration_seconds:86400}), /2 correction\(s\) mineure\(s\)/));
check(() => assert.match(sandbox.renderExecutedSource({...raw,status:'error',message:'Export incomplet'},{}), /Export incomplet/));
check(() => assert.doesNotMatch(sandbox.renderExecutedSource({...raw,status:'error'},{}), /Temps période/));
check(() => assert.match(sandbox.renderExecutedSource({...raw,status:'no_data'},{}), /Pas d'historique/));
check(() => assert.match(sandbox.qualityBadge({density_applicable:true,sample_density_percent:68.4}), /densité 68.4 %/));
check(() => assert.match(sandbox.renderExecutedSource({...raw,sensor_key:'<script>x</script>'},{}), /&lt;script&gt;/));
check(() => assert.equal(sandbox.metricCardData({...raw,analysis:{statistics:{plausible:false,delta:null},validation:{valid:false}}},{}).cells[0].value,'Incohérent'));
check(() => assert.doesNotMatch(sandbox.comparisonSourceCard({metric:'temperature',comparison_status:'comparable',values:[{label:'Moyenne',base:25,reference:20,absolute_change:5,relative_change_percent:null,relative_change_applicable:false}]}), /comparisonMiniLabel">%/));

check(() => assert.match(sandbox.renderAiAnalysis({ai_analysis:{enabled:true,status:'completed',entity_id:'ai_task.local',duration_seconds:1.23,text:'SYNTHÈSE\nOK'}}), /Analyse IA/));
check(() => assert.match(sandbox.renderAiAnalysis({ai_analysis:{enabled:true,status:'completed',entity_id:'ai_task.local',duration_seconds:1.23,text:'<script>x<\/script>'}}), /&lt;script&gt;/));
check(() => assert.match(sandbox.renderAiAnalysis({ai_analysis:{enabled:true,status:'error',error:'boom'}}), /boom/));
console.log(`${checks} JavaScript UI checks passed`);
