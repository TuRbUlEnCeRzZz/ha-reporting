const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../ha-reporting/app/app.js'), 'utf8');
const i18nSource = fs.readFileSync(path.join(__dirname, '../ha-reporting/app/i18n.js'), 'utf8');
const indexSource = fs.readFileSync(path.join(__dirname, '../ha-reporting/app/index.html'), 'utf8');
const sandbox = {};
vm.createContext(sandbox);
for (const name of ['signedValue','esc','formatSeriesNumber','localDateTime','qualityBadge','metricCardData','reportSourceCardData','renderExecutedSource','comparisonStatusLabel','comparisonSourceCard','renderAiAnalysis','periodTypeLabel','periodModeLabel','comparisonCountLabel']) {
  const match = source.match(new RegExp(`^function ${name}\\([^]*?^}`, 'm'));
  assert.ok(match, name);
  vm.runInContext(match[0], sandbox);
}
let checks = 0;
function check(fn) { fn(); checks++; }

const i18nSandbox = {
  window: {},
  localStorage: {
    getItem(key) { return key === 'ha_reporting_language' ? 'en' : null; },
    setItem() {}
  },
  navigator: {language:'fr-CH'}
};
vm.createContext(i18nSandbox);
vm.runInContext(i18nSource.replace(/hrInitI18n\(\);\s*$/, ''), i18nSandbox);
check(() => assert.equal(i18nSandbox.window.hrTranslateValue('Paramètres'),'Settings'));
check(() => assert.equal(i18nSandbox.window.hrTranslateValue('Langue du rapport'),'Report language'));
check(() => assert.equal(i18nSandbox.window.hrTranslateValue('Rapport « Test » dupliqué'),'Report “Test” duplicated'));
check(() => assert.equal(i18nSandbox.window.hrDefaultReportLanguage(),'en'));
const i18nFrenchSandbox = {
  window: {},
  localStorage: {
    getItem(key) { return key === 'ha_reporting_language' ? 'fr' : null; },
    setItem() {}
  },
  navigator: {language:'en-GB'}
};
vm.createContext(i18nFrenchSandbox);
vm.runInContext(i18nSource.replace(/hrInitI18n\(\);\s*$/, ''), i18nFrenchSandbox);
check(() => assert.equal(i18nFrenchSandbox.window.hrTranslateValue('Languages'),'Langues'));
check(() => assert.equal(i18nFrenchSandbox.window.hrTranslateValue('Report language'),'Langue du rapport'));
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
check(() => assert.match(sandbox.renderAiAnalysis({ai_analysis:{enabled:true,status:'completed',entity_id:'ai_task.local',duration_seconds:1.23,text:'OK'}}), /nuancer ou contester/));
check(() => assert.match(sandbox.renderAiAnalysis({ai_analysis:{enabled:true,status:'completed',entity_id:'ai_task.local',duration_seconds:1.23,text:'<script>x<\/script>'}}), /&lt;script&gt;/));
check(() => assert.match(sandbox.renderAiAnalysis({ai_analysis:{enabled:true,status:'error',error:'boom'}}), /boom/));
check(() => assert.match(sandbox.renderAiAnalysis({ai_analysis:{enabled:true,status:'pending'}}), /rapport est terminé/));
check(() => assert.match(source, /statusData\.execution/));
check(() => assert.match(source, /result\.execution = \{\.\.\.\(result\.execution \|\| \{\}\), \.\.\.statusData\.execution\}/));

check(() => assert.match(source, /function generateNativePdf\(/));
check(() => assert.match(source, /function currentUiTheme\(/));
check(() => assert.match(source, /JSON\.stringify\(\{theme:currentUiTheme\(\)\}\)/));
check(() => assert.match(source, /function showDocuments\(/));
check(() => assert.match(source, /reportFilenameTemplate/));
check(() => assert.match(source, /api\/document\/\$\{encodeURIComponent\(id\)\}\/download/));

check(() => assert.match(source, /function showExportProviders\(/));
check(() => assert.match(source, /function exportDocument\(/));
check(() => assert.match(source, /api\/export-providers\/paperless\/test/));
check(() => assert.match(source, /api\/export-providers\/paperless/));
check(() => assert.match(source, /paperlessMode/));
check(() => assert.match(source, /paperlessConsumePath/));
check(() => assert.match(source, /consume_folder/));
check(() => assert.match(source, /Tester le dossier consume/));
check(() => assert.match(source, /\/export\/\$\{encodeURIComponent\(providerId\)\}/));
check(() => assert.match(source, /Réessayer \$\{provider\.name\}/));

check(() => assert.equal(sandbox.periodModeLabel('day','previous'),'précédent complet'));
check(() => assert.equal(sandbox.periodModeLabel('month','previous'),'précédent complet'));
check(() => assert.equal(sandbox.periodModeLabel('week','previous'),'précédente complète'));
check(() => assert.equal(sandbox.periodModeLabel('year','previous'),'précédente complète'));
check(() => assert.equal(sandbox.comparisonCountLabel(1,'period'),'1 période précédente'));
check(() => assert.equal(sandbox.comparisonCountLabel(2,'period'),'2 périodes précédentes'));
check(() => assert.equal(sandbox.comparisonCountLabel(1,'year'),'1 année précédente'));
check(() => assert.match(source, /const PRIMARY_PAGES = new Set/));
check(() => assert.match(source, /history\.replaceState\(\{haReporting:true,page/));
check(() => assert.doesNotMatch(source, /history\.pushState/));
check(() => assert.match(source, /function showParentPage\(/));
check(() => assert.match(source, /reportDayBoundary/));
check(() => assert.doesNotMatch(source, /N-1…N-\$\{comparisons\.previous_periods\} période\(s\)/));
check(() => assert.match(source, /function duplicateReportDefinition\(/));
check(() => assert.match(source, /exportProvidersPage:"tabSettings"/));
check(() => assert.match(source, /--hr-page-background-image/));
check(() => assert.match(source, /automationNotifyEntity/));
check(() => assert.match(source, /automationTtsEntity/));
check(() => assert.match(source, /automationMediaPlayer/));
check(() => assert.match(source, /reportLanguage/));
check(() => assert.match(source, /hrDefaultReportLanguage/));
check(() => assert.match(indexSource, /id="uiLanguage"/));
check(() => assert.match(indexSource, /id="defaultReportLanguage"/));
check(() => assert.match(indexSource, /id="reportLanguage"/));
check(() => assert.match(indexSource, /<script src="i18n\.js"><\/script>[\s\S]*<script src="app\.js"><\/script>/));
check(() => assert.match(i18nSource, /"nav\.settings"/));
check(() => assert.match(i18nSource, /function hrDetectLanguage\(/));
check(() => assert.match(i18nSource, /function hrDefaultReportLanguage\(/));
check(() => assert.match(i18nSource, /MutationObserver/));
console.log(`${checks} JavaScript UI checks passed`);
