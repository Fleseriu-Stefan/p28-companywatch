'use strict';

// Design review only. Rows and measured outcomes come from the repository's synthetic ETL tests.
const editions = ['19.10.2026', '04.11.2026'];
const sourceLinks = [
  'https://data.gov.ro/dataset/1962670f-acda-41b5-b52c-c430d7a1ef5e',
  'https://data.gov.ro/dataset/c2c88c9d-4824-45f1-90ec-656f1c0d8785',
];
const companies = [
  { id:50, change:'modified', field:'Localitate', before:'Indisponibil', after:'LOC SINTETIC' },
  { id:51, change:'modified', field:'Denumire', before:'EXEMPLU SINTETIC 51 SRL', after:'exemplu sintetic 51 srl' },
  { id:52, change:'removed' }, { id:53, change:'unchanged' }, { id:54, change:'added' },
];
const labels = {
  added:['+', 'Adăugată', 'good'], removed:['−', 'Eliminată', 'bad'],
  modified:['↔', 'Modificată', 'change'], unchanged:['=', 'Neschimbată', ''],
};
const pages = {
  firme:['DS-CW-registru', 'Caută firme', 'Companii', 'search', 'visitor'],
  istoric:['DS-CW-istoric', 'Istoric observat', 'Companii', 'clock', 'visitor'],
  editii:['DS-CW-editii', 'Compară ediții', 'Date ONRC', 'compare', 'visitor'],
  analiza:['DS-CW-analiza', 'Analiză', 'Date ONRC', 'chart', 'visitor'],
  vizualizari:['DS-CW-vizualizari', 'Vizualizări salvate', 'Date ONRC', 'bookmark', 'visitor'],
  calitate:['DS-CW-calitate', 'Calitatea datelor', 'Operațiuni', 'check', 'curator'],
  schema:['DS-CW-schema', 'Revizuire schemă', 'Operațiuni', 'compare', 'curator'],
  api:['DS-CW-api', 'API și surse', 'Resurse', 'code', 'visitor'],
  acces:['DS-CW-acces', 'Administrare acces', 'Operațiuni', 'key', 'admin'],
};
const roles = ['visitor','curator','admin'];
const roleLabels = {visitor:'Acces public', curator:'Curator', admin:'Administrator'};
const paths = {
  search:'<circle cx="10.5" cy="10.5" r="5.5"/><path d="m15 15 4 4"/>',
  clock:'<circle cx="12" cy="12" r="8"/><path d="M12 7v5l3 2"/>',
  compare:'<path d="M4 8h15l-3-3m4 11H5l3 3"/>',
  chart:'<path d="M5 4v15h15M9 15v-3m4 3V7m4 8v-5"/>',
  bookmark:'<path d="M7 4h10v16l-5-3-5 3z"/>',
  check:'<path d="m12 3 7 3v6c0 4-4 7-7 9-3-2-7-5-7-9V6z"/><path d="m9 12 2 2 4-4"/>',
  code:'<path d="m8 7-5 5 5 5m8-10 5 5-5 5m-3-12-2 14"/>',
  key:'<circle cx="8" cy="12" r="4"/><path d="M12 12h8m-2 0v3"/>',
};
const icon = name => `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name]}</svg>`;
const $ = selector => document.querySelector(selector);
const workspace = $('#workspace');
const dialog = $('#dialog');
const state = {query:'', draftQuery:'', id:50, form:'', county:'', locality:'', sort:'asc', old:0, current:1, change:'', all:false, date:'2026-11-04', metric:'form', group:'', edition:1, access:'users'};
let saved = null;
let qualityReviewed = false;
let qualityDisclosureOpen = true;
let mappingReviewed = false;
let feedbackTimer;
const clean = value => String(value).replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
const cui = company => 100000 + company.id;
const euid = company => `ROONRC.J01/${company.id}/2020`;
const name = company => company.id === 51 ? company.after : `EXEMPLU SINTETIC ${company.id} SRL`;
const info = (label,value) => `<div><dt>${label}</dt><dd>${value}</dd></div>`;
const tag = type => `<span class="tag ${labels[type][2]}"><span aria-hidden="true">${labels[type][0]}</span> ${labels[type][1]}</span>`;
const select = (id, label, items, value) => `<label>${label}<select id="${id}">${items.map(([key, text]) => `<option value="${key}" ${String(key)===String(value)?'selected':''}>${text}</option>`).join('')}</select></label>`;
const exportButton = '<button type="button" data-action="export">↓ Exportă</button>';
const panel = (content, className='') => `<section class="panel pad stack ${className}">${content}</section>`;
const head = (title, description, action='') => `<div class="page-head"><div><h1>${title}</h1><p class="muted">${description}</p></div>${action}</div>`;
const sectionHead = (title, description='', action='') => `<div class="section-head"><div><h2>${title}</h2>${description?`<p class="muted small">${description}</p>`:''}</div>${action}</div>`;
const table = (columns, rows) => `<table class="table" role="table"><thead role="rowgroup"><tr role="row">${columns.map(column=>`<th role="columnheader" scope="col">${column}</th>`).join('')}</tr></thead><tbody role="rowgroup">${rows.map(row=>`<tr role="row">${row.map((cell,index)=>`<td role="cell" data-label="${columns[index]}">${cell}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
const metric = (label,value) => `<div class="metric"><span class="small">${label}</span><b>${value}</b></div>`;
const source = i => `<a href="${sourceLinks[i]}" aria-label="Sursă ONRC — ediția ${editions[i]}">Sursă ONRC ↗</a>`;
const variant = () => $('#state').value;
const editionOptions = editions.map((date, index) => [index,date]);

function pair() {
  return `<div class="pair">
    <div>${select('old','Ediția anterioară',editionOptions,state.old)}<small>ONRC · ${source(state.old)}</small></div>
    <span aria-hidden="true">→</span>
    <div>${select('current','Ediția curentă',editionOptions,state.current)}<small>ONRC · ${source(state.current)}</small></div>
  </div>`;
}

function pairBody(content, heading='h3') {
  if (state.old >= state.current) {
    return notice('error','Alege două ediții distincte','Selectează ediția mai veche în primul câmp.','',heading);
  }
  return content;
}

function notice(kind, title, detail, action='', heading='h3') {
  const role = kind==='error'?'alert':'status';
  const skeleton = kind==='loading'?'<div class="skeleton" aria-hidden="true"><i></i><i></i><i></i></div>':'';
  return `<div class="state ${kind}" role="${role}" ${kind==='loading'?'aria-busy="true"':''}><${heading} class="notice-heading">${title}</${heading}><p>${detail}</p>${skeleton}${action}</div>`;
}

function loadable(content, noun, emptyDetail='Revino după ce sunt disponibile date pentru această selecție.', heading='h2') {
  switch (variant()) {
    case 'loading': return notice('loading','Se încarcă…',`Se încarcă ${noun}.`,'',heading);
    case 'empty': return notice('empty','Nu sunt date disponibile',emptyDetail,'<button data-action="reset">Revino la selecția inițială</button>',heading);
    case 'error': return notice('error','Încărcarea a eșuat',`Reîncearcă încărcarea pentru ${noun}.`,'<button data-action="retry">Reîncearcă</button>',heading);
    case 'success': return notice('success','Date actualizate',`Sunt disponibile ${noun} pentru selecția curentă.`,'',heading)+content;
    default: return content;
  }
}

function filtered(items, search = false) {
  const query = search ? state.query.trim().toLocaleLowerCase('ro') : '';
  return items.filter(company =>
    (!query || name(company).toLocaleLowerCase('ro').includes(query) || String(cui(company)).includes(query)) &&
    (!state.form || state.form==='SRL') &&
    (!state.county || state.county==='JUDET SINTETIC') &&
    (!state.locality || state.locality===(company.id===50?'LOC SINTETIC':'LOCALITATE SINTETICA'))
  ).sort((a,b)=>state.sort==='asc'?a.id-b.id:b.id-a.id);
}

function publicFilters() {
  return `<div class="filters">
    ${select('form','Formă juridică',[['','Toate'],['SRL','SRL']],state.form)}
    ${select('county','Județ',[['','Toate'],['JUDET SINTETIC','Județ sintetic']],state.county)}
    ${select('locality','Localitate',[['','Toate'],['LOC SINTETIC','Loc sintetic'],['LOCALITATE SINTETICA','Localitate sintetică']],state.locality)}
    ${select('sort','Sortare după CUI',[['asc','Crescător'],['desc','Descrescător']],state.sort)}
  </div>`;
}

function dashboard() {
  const matches = filtered(companies.filter(company=>company.change!=='removed'),true);
  const selected = matches.find(company=>company.id===state.id) ?? matches[0];
  if (selected) state.id=selected.id;
  const results = matches.length
    ? `<p class="count" role="status">${matches.length} ${matches.length===1?'rezultat':'rezultate'} · ${editions[1]}</p>
       <ul class="results">${matches.map(company=>`<li><button class="result" data-company="${company.id}" aria-pressed="${selected?.id===company.id}"><span class="row"><strong>${name(company)}</strong><span aria-hidden="true">↗</span></span><span class="mono">CUI ${cui(company)} · SRL</span></button></li>`).join('')}</ul>`
    : notice('empty','Nicio firmă găsită','Verifică denumirea sau CUI și ajustează filtrele.','<button data-action="reset">Resetează căutarea</button>');
  const hero = `<section class="hero">
    <div class="eyebrow">${icon('search')} Registrul firmelor din România</div>
    <h1>Caută o firmă</h1><p>Consultă profilul ONRC și vezi ce s-a schimbat între ediții.</p>
    <form class="search-form" id="search-form">
      <label for="query">Denumire sau CUI</label>
      <div class="search-row"><input id="query" name="q" type="search" placeholder="Scrie denumirea sau CUI" value="${clean(state.draftQuery)}"><button class="primary">Caută în registru</button></div>
    </form>
  </section>`;
  const detail = selected ? companyProfile(selected) : '';
  return hero+`<div class="columns">${panel(sectionHead('Rezultatele căutării','',exportButton)+publicFilters()+loadable(results,'rezultatele căutării','Încearcă o altă denumire, un CUI sau alte filtre.','h3'))}
    <div class="stack">${['ready','success'].includes(variant())?detail:''}</div></div>`;
}

function companyProfile(company) {
  const locality = company.id===50?'LOC SINTETIC':'LOCALITATE SINTETICA';
  const profile = panel(`<div class="profile-title"><div class="row between"><span class="tag good">● Prezentă în ediție</span><span class="mono">CUI ${cui(company)}</span></div>
    <h2>${name(company)}</h2><p class="muted">${locality} · JUDET SINTETIC</p></div>
    <dl class="dl">${info('EUID',euid(company))}${info('Număr de înmatriculare',`J01/${company.id}/2020`)}${info('Formă juridică','SRL')}${info('Data înmatriculării','01.02.2020')}</dl>
    <div class="row between"><p class="small muted">Observată la ${editions[1]} · ${source(1)}</p><a class="button" href="#istoric?firma=${company.id}">Istoric observat →</a></div>`);
  const changes = [];
  if (company.field) changes.push([company.field,company.before,company.after,tag(company.change)]);
  if (company.change==='added') changes.push(['Prezență','Absentă','Prezentă',tag('added')]);
  if (state.all && company.change!=='added') changes.push(['Formă juridică','SRL','SRL',tag('unchanged')],['CUI',cui(company),cui(company),tag('unchanged')]);
  const detail = changes.length
    ? table(['Câmp',editions[state.old],editions[state.current],'Schimbare'],changes)
    : '<p class="muted">Nu sunt câmpuri modificate în această comparație.</p>';
  const comparison = panel(sectionHead('Comparația firmei','',exportButton)+pair()+pairBody(`
    <div class="row between">${tag(company.change)}<label class="small check-control"><input id="all" type="checkbox" ${state.all?'checked':''}> Arată câmpurile neschimbate</label></div>${detail}`));
  return profile+comparison;
}

function observedHistory() {
  const company=companies.find(item=>item.id===state.id) ?? companies[0];
  const iso=['2026-10-19','2026-11-04'];
  const index=state.date>=iso[1]?1:(state.date>=iso[0]?0:-1);
  const absent=index===0&&company.change==='added' || index===1&&company.change==='removed';
  const locality=index===0&&company.id===50?'Indisponibil':(company.id===50?'LOC SINTETIC':'LOCALITATE SINTETICA');
  let observed;
  if(index<0) observed=notice('empty','Istoric indisponibil','Data cerută este anterioară primei ediții disponibile.');
  else if(absent) observed=notice('empty','Firmă absentă în ediția selectată',`Ediția ${editions[index]} nu conține EUID-ul selectat.`);
  else observed=`<div class="row"><span class="tag good">● Prezentă în ediție</span><span class="small">${editions[index]} · ${source(index)}</span></div>
    <dl class="dl">${info('Denumire',index===0&&company.id===51?company.before:name(company))}${info('CUI',cui(company))}${info('EUID',euid(company))}${info('Localitate',locality)}</dl>`;
  return head('Istoric observat','Consultă starea firmei în ultima ediție publicată până la data cerută.',`<a class="button" href="#firme?firma=${company.id}">← Profilul firmei</a>`)+
    panel(sectionHead(name(company),euid(company))+`<form class="filters" id="history-form"><label>Data cerută <input id="date" type="date" value="${state.date}" required></label><button class="primary">Consultă ediția</button></form>`+loadable(observed,'starea observată',undefined,'h3'));
}

function comparisons() {
  const cards=['added','removed','modified','unchanged'].map(type=>`<button class="metric" data-change="${type}" aria-pressed="${state.change===type}">${tag(type)}<b>${companies.filter(item=>item.change===type).length}</b></button>`).join('');
  const matching = filtered(companies).filter(company=>!state.change||company.change===state.change);
  const rows = matching.map(company=>[
    `<a href="#istoric?firma=${company.id}">${name(company)}</a><br><span class="mono">${euid(company)}</span>`,tag(company.change),
    company.field ?? 'Prezență', company.before ?? (company.change==='added'?'Absentă':'Prezentă'),
    company.after ?? (company.change==='removed'?'Absentă':'Prezentă'),
  ]);
  return head('Compară edițiile ONRC','Explorează schimbările observate între două ediții publicate.',exportButton)+panel(pair())+
    loadable(pairBody(`<div class="cover" aria-label="Filtre după tipul schimbării">${cards}</div>`+
      panel(sectionHead('Schimbări în registru','Eliminarea indică absența din ediția curentă.',state.change?'<button data-change="">Toate schimbările</button>':'')+publicFilters()+
      (rows.length?table(['Firmă','Schimbare','Câmp',editions[state.old],editions[state.current]],rows):notice('empty','Nicio schimbare în selecție','Ajustează filtrele pentru a vedea alte rezultate.'))),'h2'),'schimbările între ediții');
}

const metrics = [
  ['form','Companii după formă juridică'],['sum','Totaluri de validare pe ediții'],['rate','Rată medie de carantină'],
];

function analysis(pinned=false) {
  const metricId=pinned?saved.metric:state.metric;
  const edition=pinned?saved.edition:state.edition;
  const group=pinned?saved.group:state.group;
  let rows, legend, maximum, unit='rânduri';
  if(metricId==='sum'){
    rows=edition===0?[['Acceptate',5],['Carantină',0],['Excluse',0]]:[['Acceptate',3],['Carantină',4],['Excluse',1]];
    legend='Rânduri după rezultat, pentru ediția selectată';
    maximum=edition===0?5:8;
  } else if(metricId==='rate'){
    rows=[['Medie',25]];
    legend='Media ratelor celor două ediții · 0% și 50%';
    maximum=100;
    unit='%';
  } else {
    rows=edition===0?[['SRL',5]]:[['SRL',1],['SA',1],['SNC',1]];
    legend='Companii acceptate după formă juridică';
    maximum=edition===0?5:3;
    unit='companii';
  }
  const actions=`<div class="tools">${exportButton}${roles.indexOf($('#role').value)>0&&!pinned?'<button class="primary" data-action="save">Salvează vizualizarea</button>':''}</div>`;
  const detail=rows.filter(([label])=>!group||group===label);
  const chart=`<div class="chart" aria-label="${legend}">${rows.map(([label,value])=>`<button class="bar-action" data-group="${label}" aria-pressed="${group===label}" aria-label="${label}, ${value} ${value===1&&unit==='companii'?'companie':unit}" ${pinned?'disabled':''}><span>${label}</span><span class="track" aria-hidden="true"><i style="--bar:${value/maximum*100}%"></i></span><b>${value}${unit==='%'?'%':''}</b></button>`).join('')}</div>`;
  return head(pinned?'Vizualizare salvată':'Analiză ONRC',pinned?'Filtre și ediții fixate la salvare.':'Explorează agregate din edițiile selectate și exportă datele grupate.',actions)+
    (!pinned?panel(`<div class="filters">${select('metric','Indicator',metrics,metricId)}
       ${metricId==='rate'?'<span class="small muted">Ediții · 19.10.2026 și 04.11.2026</span>':select('edition','Ediție',editionOptions,edition)}</div>`):'')+
    loadable(panel(sectionHead(legend,`Unitate · ${unit} · ${metricId==='rate'?'19.10.2026 și 04.11.2026':editions[edition]}`)+chart+
      (group&&!pinned?'<button data-group="">Arată toate grupurile</button>':'')+table(['Grup',`Valoare (${unit})`],detail)),'datele grupate');
}

function savedViews() {
  const hasPinned=new URLSearchParams(location.hash.split('?')[1]).get('indicator');
  if(hasPinned && saved) return analysis(true);
  return head('Vizualizări salvate','Deschide o analiză cu edițiile și filtrele fixate la salvare.')+
    loadable(panel(sectionHead('Vizualizări disponibile')+(saved
      ? `<div class="row between"><strong>${metrics.find(item=>item[0]===saved.metric)[1]}</strong><a class="button" href="${savedLink()}">Deschide vizualizarea →</a></div>`
      : notice('empty','Nu există vizualizări salvate','Vizualizările pregătite de curatori apar aici.','<a class="button" href="#analiza">Deschide analiza</a>'))),'vizualizările salvate');
}

function quality() {
  const report=`<div class="cover">${metric('Rânduri analizate',8)}${metric('Acceptate',3)}${metric('În carantină',4)}${metric('Excluse',1)}</div>`+
    `<div class="columns equal">
      ${panel(sectionHead('Raport de ingestie','Ediția 04.11.2026 · fixture sintetic')+
        `<div class="row"><span class="tag good">✓ Fișier validat</span><span class="tag ${qualityReviewed ? 'good' : 'warn'}">${qualityReviewed ? '✓ Raport revizuit' : 'Așteaptă revizuirea'}</span></div>`+
        table(['Rezultat','Rânduri'],[['Acceptate',3],['În carantină',4],['Excluse intenționat',1]])+
        '<a class="button" href="#schema">Revizuiește schema →</a>')}
      ${panel(sectionHead('Anomalii și publicare','Comparație cu ediția 19.10.2026')+
        `<details id="quality-anomalies"${qualityDisclosureOpen?' open':''}><summary>Semnale din comparația de calitate</summary><ul><li>Au apărut înregistrări duplicate.</li><li>Rândurile acceptate au scăzut de la 5 la 3.</li></ul></details>`+
        `<p class="muted small">Publicarea necesită revizuirea raportului, aprobarea mapării și aprobarea versiunii validate.</p><div class="row"><button data-action="review">Revizuiește raportul</button><button data-action="publish" ${qualityReviewed&&mappingReviewed?'':'disabled'}>Publică ediția</button></div>`)}
    </div>`;
  return head('Calitatea datelor','Revizuiește ingestia, rezultatele validării și starea publicării.')+loadable(report,'rapoartele de ingestie','Rapoartele apar după prima încercare de ingestie.');
}

function schema() {
  return head('Revizuire schemă','Verifică legătura dintre antetul sursă și câmpurile canonice.','<a class="button" href="#calitate">← Raport de ingestie</a>')+
    loadable(panel(sectionHead('Mapare canonică','Exemple din proiecția ONRC M2')+
      table(['Coloană anterioară','Coloană curentă','Câmp canonic'],[['EUID','EUID','EUID'],['DENUMIRE','DENUMIRE','Denumire'],['ADR_LOCALITATE','ADR_LOCALITATE','Localitate']])+
      `<details><summary>Când se blochează publicarea</summary><p class="muted">O mapare obligatorie ambiguă trebuie rezolvată explicit înaintea aprobării și validării ediției.</p></details><div class="row"><button data-action="mapping">Revizuiește maparea</button>${mappingReviewed?'<span class="tag good">✓ Mapare revizuită</span>':''}</div>`),'mapările schemei');
}

function api() {
  return head('API și surse','Consultă contractul API și documentația datasetului ONRC.')+
    loadable(`<div class="columns equal">${panel(sectionHead('Documentația API','FastAPI · OpenAPI')+
      '<ul class="rows"><li class="observation"><strong>GET /health/live</strong><p class="muted small">Disponibilitatea procesului API.</p></li><li class="observation"><strong>GET /health/ready</strong><p class="muted small">Disponibilitatea serviciului și a bazei de date la schema așteptată.</p></li></ul><p class="mono">/docs · /openapi.json</p><p class="small muted">Accesul cu chei și cotele pentru API-ul extern sunt prevăzute pentru o etapă ulterioară.</p>')}
      ${panel(sectionHead('Dataset ONRC','OD_FIRME.CSV · CC BY 4.0')+
      '<ul class="rows"><li class="observation"><a href="../../../../DATA.md">Proveniență, licență și limite ↗</a></li><li class="observation"><a href="../../../ONRC-SOURCE.md">Sursă, ediții și câmpuri ONRC ↗</a></li></ul>')}
    </div>`,'resursele de documentație');
}

function access() {
  const keyView=state.access==='keys';
  return head('Administrare acces','Gestionează utilizatorii, rolurile și accesul la API.')+
    panel(`<div class="row"><button data-access="users" aria-pressed="${!keyView}">Utilizatori și roluri</button><button data-access="keys" aria-pressed="${keyView}">Chei API</button></div>
      ${loadable(keyView
        ? notice('empty','Nicio cheie API în această previzualizare','Cheile, ratele și cotele vor fi gestionate după integrarea API-ului extern.','<button data-action="keys">Vezi accesul API</button>','h2')
        : sectionHead('Roluri disponibile','Accesul privilegiat necesită autentificare.')+table(['Rol','Drepturi'],[['Curator','Revizuiește ingestia și maparea. Aprobă și publică ediții validate.'],['Administrator','Gestionează utilizatori, roluri, chei API și permisiuni.']])+
          '<button data-action="roles">Vezi drepturile rolurilor</button>','datele de administrare')}`);
}

const renderPage={firme:dashboard,istoric:observedHistory,editii:comparisons,analiza:analysis,vizualizari:savedViews,calitate:quality,schema,api,acces:access};
function route(readCompany = false) {
  const [page, query]=location.hash.slice(1).split('?');
  const params=new URLSearchParams(query);
  const company=Number(params.get('firma'));
  if(readCompany && companies.some(item=>item.id===company)) state.id=company;
  const metricId=params.get('indicator');
  const edition=Number(params.get('editie'));
  if(page==='vizualizari'&&metrics.some(([key])=>key===metricId)&&[0,1].includes(edition)){
    const group=params.get('grup')??'';
    const groups={form:['SRL','SA','SNC'],sum:['Acceptate','Carantină','Excluse'],rate:['Medie']};
    saved={metric:metricId,edition,group:groups[metricId].includes(group)?group:''};
  }
  return Object.hasOwn(pages,page)?page:'firme';
}

function render(restoreFocus=false, readCompany=false) {
  const focused=document.activeElement;
  const page=route(readCompany);
  const role=$('#role').value;
  const visible=Object.entries(pages).filter(([,info])=>info[4]==='visitor'||info[4]===role);
  $('#navigation').innerHTML=[...new Set(visible.map(([,info])=>info[2]))].map(group=>`<div class="group"><p>${group}</p>${visible.filter(([,info])=>info[2]===group).map(([key,info])=>`<a class="nav-link" href="#${key}" ${key===page?'aria-current="page"':''}>${icon(info[3])}${info[1]}</a>`).join('')}</div>`).join('');
  $('#location').textContent=pages[page][1];
  $('#context').textContent=`ONRC · ${roleLabels[role]}`;
  workspace.innerHTML=visible.some(([key])=>key===page)
    ? renderPage[page]()
    : head('Acces restricționat','Această secțiune necesită un rol autorizat.')+notice('error','Drepturi insuficiente','Perspectiva selectată nu are acces la această secțiune.','<a class="button" href="#firme">Revino la căutare</a>','h2');
  document.title=`${pages[page][1]} · CompanyWatch`;
  if (restoreFocus) {
    if (focused?.id && workspace.contains($('#'+focused.id))) $('#'+focused.id).focus();
    else {
      const attr=['company','change','group','access','action'].find(key=>focused?.dataset[key]!==undefined);
      const replacement=attr&&[...workspace.querySelectorAll(`[data-${attr}]`)].find(item=>item.dataset[attr]===focused.dataset[attr]);
      if(replacement) replacement.focus();
      else if(!document.contains(focused)) workspace.focus();
    }
  }
}

function feedback(text) {
  const status=$('#feedback');
  status.textContent=text;
  status.hidden=false;
  clearTimeout(feedbackTimer);
  feedbackTimer=setTimeout(()=>{status.hidden=true},4500);
}

function savedLink() {
  const params=new URLSearchParams({indicator:saved.metric,editie:saved.edition,grup:saved.group});
  return '#vizualizari?'+params;
}

const dialogData={
  export:['Exportă rezultatele','Exportul folosește toate rezultatele potrivite cu filtrele, sortarea și edițiile selecției curente.',['CSV','XLSX']],
  save:['Salvează vizualizarea','Linkul păstrează indicatorul, filtrele și edițiile exacte.',['Salvează în mockup']],
  review:['Revizuiește raportul','Raport sintetic. În aplicație, aprobarea se leagă de fișier, datele pregătite și raportul verificat.',['Confirmă în mockup']],
  mapping:['Revizuiește maparea','Verifică toate câmpurile obligatorii înainte de a confirma maparea.',['Confirmă în mockup']],
  publish:['Publică ediția','În aplicație, publicarea necesită aprobarea versiunii validate și actualizează ediția disponibilă vizitatorilor. În mockup, acțiunea afișează starea de confirmare.',['Simulează confirmarea']],
  keys:['Acces API','API-ul extern va solicita o cheie validă. Valorile limitelor și cotelor rămân de stabilit. ',[]],
  roles:['Drepturile rolurilor','Curatorul gestionează ingestia și publicarea. Administratorul gestionează accesul. Vizitatorul poate consulta datele publicate.',[]],
};

function openDialog(action) {
  const [title,description,buttons]=dialogData[action];
  dialog.dataset.action=action;
  dialog.innerHTML=`<form class="stack" method="dialog"><h2 id="dialog-title">${title}</h2><p class="muted">${description}</p><div class="row"><button value="cancel" autofocus>Închide</button>${buttons.map(label=>`<button class="primary" value="${label}">${label}</button>`).join('')}</div></form>`;
  dialog.returnValue='cancel';
  dialog.showModal();
}

dialog.addEventListener('close',()=>{
  if (dialog.returnValue==='cancel') return;
  if (dialog.dataset.action==='save') {
    saved={metric:state.metric,edition:state.edition,group:state.group};
    location.hash=savedLink();
    feedback('Vizualizarea este disponibilă prin linkul din acest mockup.');
  } else if(dialog.dataset.action==='export'){
    feedback(`Format selectat în previzualizare · ${dialog.returnValue}`);
  } else if(dialog.dataset.action==='publish'){
    $('#state').value='success';
    render(true);
    feedback('Confirmare de publicare afișată în previzualizare.');
  } else {
    if(dialog.dataset.action==='review') {
      qualityDisclosureOpen=$('#quality-anomalies')?.open??qualityDisclosureOpen;
      qualityReviewed=true;
    }
    if(dialog.dataset.action==='mapping') mappingReviewed=true;
    render(true);
    feedback('Revizuire confirmată în previzualizare.');
  }
});

document.addEventListener('change',event=>{
  const {id,value,checked}=event.target;
  if(id==='theme') document.documentElement.dataset.theme=value;
  else if(id==='role'||id==='state'){
    render();
  } else if(['old','current','edition','metric','form','county','locality','sort','all'].includes(id)){
    state[id]=id==='all'?checked:(['old','current','edition'].includes(id)?Number(value):value);
    if(id==='metric'||id==='edition') state.group='';
    render(true);
  }
});

workspace.addEventListener('input',event=>{
  if(event.target.id==='query') state.draftQuery=event.target.value;
});

workspace.addEventListener('submit',event=>{
  event.preventDefault();
  if(event.target.id==='search-form') {
    state.draftQuery=$('#query').value;
    state.query=state.draftQuery;
  }
  if(event.target.id==='history-form') state.date=$('#date').value;
  render(true);
});

workspace.addEventListener('click',event=>{
  const button=event.target.closest('button');
  if(!button) return;
  const {company,change,group,access,action}=button.dataset;
  if(company){
    state.id=Number(company);
    window.history.replaceState(null,'',`#firme?firma=${state.id}`);
  } else if(change!==undefined) state.change=state.change===change?'':change;
  else if(group!==undefined) state.group=state.group===group?'':group;
  else if(access) state.access=access;
  else if(action==='retry') $('#state').value='ready';
  else if(action==='reset') {
    Object.assign(state,{query:'',draftQuery:'',form:'',county:'',locality:'',sort:'asc',change:'',group:'',old:0,current:1});
    $('#state').value='ready';
  } else if(action in dialogData) {
    openDialog(action);
    return;
  } else return;
  render(true);
});

function closeMenu() {
  $('#capture').dataset.menu='closed';
  $('#menu').setAttribute('aria-expanded','false');
}
$('#menu').addEventListener('click',()=>{
  if($('#menu').getAttribute('aria-expanded')==='true') closeMenu();
  else {
    $('#capture').dataset.menu='open';
    $('#menu').setAttribute('aria-expanded','true');
    $('#navigation a')?.focus();
  }
});
$('#navigation').addEventListener('click',event=>{
  if(event.target.closest('a')&&$('#menu').getAttribute('aria-expanded')==='true'){
    closeMenu();
    workspace.focus();
  }
});
document.addEventListener('keydown',event=>{
  if(event.key==='Escape'&&$('#menu').getAttribute('aria-expanded')==='true'&&!dialog.open){
    closeMenu();
    $('#menu').focus();
  }
});
document.querySelector('.skip').addEventListener('click',event=>{
  event.preventDefault();
  workspace.focus();
  workspace.scrollIntoView();
});
window.addEventListener('hashchange',()=>{
  closeMenu();
  render(false,true);
  workspace.focus();
  window.scrollTo(0,0);
});
document.querySelector('.review').addEventListener('submit',event=>event.preventDefault());
render(false,true);
