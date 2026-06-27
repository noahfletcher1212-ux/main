/* ============================================================
   FLIP TYCOON — Wholesale Empire
   A cartoon real-estate wholesaling tycoon game.
   All state in one object, saved to localStorage.
   ============================================================ */
(() => {
'use strict';

const SAVE_KEY = 'fliptycoon_v1';
const $ = id => document.getElementById(id);
const rand = (a, b) => Math.random() * (b - a) + a;
const randInt = (a, b) => Math.floor(rand(a, b + 1));
const pick = arr => arr[Math.floor(Math.random() * arr.length)];
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const fmt$ = n => '$' + Math.round(n).toLocaleString('en-US');
const fmtK = n => n >= 1000 ? '$' + (n / 1000).toFixed(n >= 100000 ? 0 : 1).replace('.0', '') + 'k' : fmt$(n);

/* ---------- Config: markets, upgrades, ranks ---------- */
const MARKETS = [
  { id:'suburbs', name:'Suburbs',   icon:'🏡', cost:0,       arv:[140000,260000], color:'#36d39a' },
  { id:'city',    name:'City Blocks',icon:'🏘️', cost:75000,  arv:[260000,460000], color:'#36c5f0' },
  { id:'metro',   name:'Metro High-Rise',icon:'🏢', cost:400000, arv:[480000,820000], color:'#7b5cff' },
  { id:'luxury',  name:'Luxury Coast',icon:'🌴', cost:1500000,arv:[900000,1800000],color:'#ff5d8f' },
];

const UPGRADES = {
  marketing:  { emoji:'📣', name:'Marketing Reach', max:5,
    desc:['Flyers','Postcards','Cold Calls','Bandit Signs','PPC Ads','Full Funnel'],
    descLine:'More & better leads per hunt',
    cost:[0, 4000, 12000, 30000, 70000, 150000] },
  negotiation:{ emoji:'🧠', name:'Negotiation Skill', max:5,
    desc:['Newbie','Smooth Talker','Closer','Persuader','Shark','Mastermind'],
    descLine:'Higher accept odds & lower buy price',
    cost:[0, 5000, 14000, 35000, 80000, 175000] },
  network:    { emoji:'🤝', name:'Buyer Network', max:5,
    desc:['1 Buyer','Small List','Buyer Pool','Investor Club','Hedge Funds','Nationwide'],
    descLine:'Bigger assignment fees from buyers',
    cost:[0, 6000, 16000, 40000, 90000, 200000] },
  energy:     { emoji:'⚡', name:'Hustle Stamina', max:5,
    desc:['5 / day','7 / day','9 / day','12 / day','15 / day','20 / day'],
    descLine:'More energy (actions) each day',
    cost:[0, 5000, 13000, 32000, 75000, 160000] },
};
const ENERGY_BY_LVL = [5, 7, 9, 12, 15, 20];

const RANKS = [
  { icon:'🥉', name:'Rookie',     at:0 },
  { icon:'🥈', name:'Dealer',     at:50000 },
  { icon:'🥇', name:'Closer',     at:150000 },
  { icon:'💎', name:'Investor',   at:400000 },
  { icon:'👑', name:'Mogul',      at:1000000 },
  { icon:'🏆', name:'Tycoon',     at:3000000 },
  { icon:'🚀', name:'Legend',     at:8000000 },
];

const STREETS = ['Maple','Oak','Pine','Sunset','Birch','Cedar','Willow','Elm','Aspen','Magnolia',
  'Riverside','Hillcrest','Park','Lakeview','Meadow','Bramble','Cherry','Walnut','Juniper','Harbor',
  'Crescent','Dogwood','Foxglove','Sycamore','Chestnut','Marigold','Briar','Cobblestone'];
const SUFFIX = ['St','Ave','Dr','Ln','Ct','Rd','Way','Blvd','Pl','Terr'];
const HOUSE_EMOJIS = ['🏠','🏡','🏚️','🏘️','🏢','🏬'];
const CONDITIONS = [
  { name:'Hoarder House', emoji:'🏚️', repairPct:[0.14,0.22] },
  { name:'Fixer-Upper',   emoji:'🏚️', repairPct:[0.10,0.16] },
  { name:'Tired Rental',  emoji:'🏠', repairPct:[0.07,0.12] },
  { name:'Cosmetic Reno', emoji:'🏡', repairPct:[0.04,0.08] },
  { name:'Move-in Ready', emoji:'🏡', repairPct:[0.02,0.05] },
  { name:'Storm Damaged', emoji:'🏚️', repairPct:[0.12,0.20] },
  { name:'Estate Sale',   emoji:'🏘️', repairPct:[0.06,0.13] },
];
const SELLER_REASONS = ['Job relocation','Inherited the property','Going through divorce','Facing foreclosure',
  'Tired landlord','Downsizing','Behind on taxes','Moving for retirement','Vacant & costly'];

/* ---------- Default state ---------- */
function freshState(){
  return {
    cash: 2000,
    day: 1,
    energy: 5,
    deals: [],
    dealSeq: 1,
    upgrades: { marketing:0, negotiation:0, network:0, energy:0 },
    marketsUnlocked: ['suburbs'],
    activeMarket: 'suburbs',
    stats: { dealsClosed:0, totalEarned:0, biggest:0, fellThrough:0, daysPlayed:1, leadsFound:0 },
    sound: true,
    seenHow: false,
  };
}
let S = load() || freshState();

function save(){ try{ localStorage.setItem(SAVE_KEY, JSON.stringify(S)); }catch(e){} }
function load(){ try{ const r = localStorage.getItem(SAVE_KEY); return r ? JSON.parse(r) : null; }catch(e){ return null; } }

/* ---------- Sound (tiny WebAudio blips) ---------- */
let actx = null;
function beep(freq, dur=0.08, type='sine', vol=0.12){
  if(!S.sound) return;
  try{
    actx = actx || new (window.AudioContext||window.webkitAudioContext)();
    const o = actx.createOscillator(), g = actx.createGain();
    o.type = type; o.frequency.value = freq;
    g.gain.value = vol;
    o.connect(g); g.connect(actx.destination);
    o.start();
    g.gain.exponentialRampToValueAtTime(0.0001, actx.currentTime + dur);
    o.stop(actx.currentTime + dur + 0.02);
  }catch(e){}
}
const sfx = {
  tap:   () => beep(440, .05, 'square', .06),
  hunt:  () => { beep(330,.08,'sawtooth',.08); setTimeout(()=>beep(440,.08,'sawtooth',.08),90); },
  found: () => { beep(523,.09,'triangle'); setTimeout(()=>beep(784,.12,'triangle'),100); },
  cash:  () => { beep(660,.07,'square',.09); setTimeout(()=>beep(880,.07,'square',.09),70); setTimeout(()=>beep(1175,.14,'square',.09),140); },
  fail:  () => { beep(220,.18,'sawtooth',.1); },
  buy:   () => { beep(587,.06,'square',.08); setTimeout(()=>beep(880,.1,'square',.08),60); },
  level: () => { [523,659,784,1047].forEach((f,i)=>setTimeout(()=>beep(f,.12,'triangle',.1),i*90)); },
};

/* ============================================================
   DEAL GENERATION
   ============================================================ */
function genDeal(){
  const mkt = MARKETS.find(m => m.id === S.activeMarket);
  const cond = pick(CONDITIONS);
  // Better marketing nudges toward bigger ARVs & more motivated sellers
  const mLvl = S.upgrades.marketing;
  const arv = Math.round(rand(mkt.arv[0], mkt.arv[1]) * (1 + mLvl*0.02) / 1000) * 1000;
  const repairs = Math.round(arv * rand(cond.repairPct[0], cond.repairPct[1]) / 500) * 500;
  // Max Allowable Offer (the wholesaler's golden 70% rule)
  const mao = Math.round((arv * 0.70 - repairs) / 500) * 500;
  // Motivation 1..5 — higher marketing finds hotter leads
  const motivation = clamp(randInt(1, 4) + (Math.random() < mLvl*0.12 ? 1 : 0), 1, 5);
  // Seller asking: hot sellers list near/under MAO; cold sellers want more
  const askMult = motivation >= 4 ? rand(0.92, 1.04)
                : motivation === 3 ? rand(1.0, 1.12)
                : rand(1.08, 1.25);
  const asking = Math.round(mao * askMult / 500) * 500;
  return {
    id: S.dealSeq++,
    addr: `${randInt(100,9899)} ${pick(STREETS)} ${pick(SUFFIX)}`,
    emoji: cond.emoji,
    cond: cond.name,
    reason: pick(SELLER_REASONS),
    arv, repairs, mao, asking, motivation,
    stage: 'lead',        // lead -> contracted
    contractPrice: 0,
  };
}

/* ============================================================
   RENDER
   ============================================================ */
let displayCash = S.cash;

function renderAll(){
  renderHUD();
  renderDeals();
  renderShop();
  renderMarkets();
  renderStats();
  renderHuntStats();
}

function currentRank(){
  let r = RANKS[0];
  for(const rk of RANKS) if(S.stats.totalEarned + S.cash >= rk.at) r = rk;
  return r;
}
function nextRank(){
  const nw = S.stats.totalEarned + S.cash;
  return RANKS.find(rk => rk.at > nw) || null;
}

function renderHUD(){
  // animated cash count-up
  animateCash();
  $('day').textContent = S.day;
  const maxE = ENERGY_BY_LVL[S.upgrades.energy];
  $('energy').textContent = S.energy;
  $('maxEnergy').textContent = maxE;
  $('energy').parentElement.classList.toggle('low', S.energy <= 1);
  $('dealsClosed').textContent = S.stats.dealsClosed;

  const rk = currentRank();
  $('rankIcon').textContent = rk.icon;
  $('rankName').textContent = rk.name;

  const nr = nextRank();
  const nw = S.stats.totalEarned + S.cash;
  if(nr){
    const prev = rk.at;
    const pct = clamp((nw - prev) / (nr.at - prev) * 100, 0, 100);
    $('goalFill').style.width = pct + '%';
    $('goalText').textContent = `${rk.name} → ${nr.name}: ${fmtK(nr.at - nw)} to go`;
  } else {
    $('goalFill').style.width = '100%';
    $('goalText').textContent = '👑 MAX RANK — Legendary Tycoon!';
  }

  // nav badge = active leads needing action
  const open = S.deals.length;
  const badge = $('navBadge');
  if(open > 0){ badge.classList.remove('hidden'); badge.textContent = open; }
  else badge.classList.add('hidden');

  $('muteBtn').textContent = S.sound ? '🔊' : '🔇';
  $('marketBadge').textContent = `${MARKETS.find(m=>m.id===S.activeMarket).icon} ${MARKETS.find(m=>m.id===S.activeMarket).name}`;
}

function animateCash(){
  const el = $('cash');
  const target = S.cash;
  const start = displayCash;
  if(start === target){ el.textContent = fmt$(target); return; }
  const t0 = performance.now(), dur = 600, diff = target - start;
  function step(t){
    const k = clamp((t - t0)/dur, 0, 1);
    const eased = 1 - Math.pow(1 - k, 3);
    displayCash = start + diff * eased;
    el.textContent = fmt$(displayCash);
    if(k < 1) requestAnimationFrame(step);
    else { displayCash = target; el.textContent = fmt$(target); }
  }
  requestAnimationFrame(step);
}

function motivationTag(m){
  if(m >= 4) return { cls:'tag-hot', txt:'🔥 Motivated' };
  if(m === 3) return { cls:'tag-warm', txt:'😐 Curious' };
  return { cls:'tag-cold', txt:'🧊 Cold' };
}

function renderDeals(){
  const list = $('dealList');
  const empty = $('emptyDeals');
  list.innerHTML = '';
  if(S.deals.length === 0){ empty.classList.remove('hidden'); return; }
  empty.classList.add('hidden');

  S.deals.forEach(d => {
    const card = document.createElement('div');
    card.className = 'deal-card' + (d.stage === 'contracted' ? ' contracted' : '');
    const tag = motivationTag(d.motivation);

    if(d.stage === 'lead'){
      card.innerHTML = `
        <div class="dc-top">
          <div class="dc-emoji">${d.emoji}</div>
          <div class="dc-info">
            <div class="dc-addr">${d.addr}</div>
            <div class="dc-sub">${d.cond} · ${d.reason}</div>
            <span class="dc-tag ${tag.cls}">${tag.txt}</span>
          </div>
        </div>
        <div class="dc-figures">
          <div class="fig"><span>ARV</span><b>${fmtK(d.arv)}</b></div>
          <div class="fig"><span>Repairs</span><b>${fmtK(d.repairs)}</b></div>
          <div class="fig"><span>Asking</span><b>${fmtK(d.asking)}</b></div>
        </div>
        <div class="dc-actions">
          <button class="dc-btn primary" data-act="negotiate" data-id="${d.id}">🤝 Make Offer</button>
          <button class="dc-btn drop" data-act="drop" data-id="${d.id}" title="Pass on this lead">✕</button>
        </div>`;
    } else {
      const fee = assignmentFee(d);
      card.innerHTML = `
        <div class="dc-status">📑 Under Contract</div>
        <div class="dc-top">
          <div class="dc-emoji">${d.emoji}</div>
          <div class="dc-info">
            <div class="dc-addr">${d.addr}</div>
            <div class="dc-sub">${d.cond}</div>
            <span class="dc-tag tag-contract">Locked at ${fmtK(d.contractPrice)}</span>
          </div>
        </div>
        <div class="dc-figures">
          <div class="fig"><span>ARV</span><b>${fmtK(d.arv)}</b></div>
          <div class="fig"><span>Your Cost</span><b>${fmtK(d.contractPrice)}</b></div>
          <div class="fig profit"><span>Est. Fee</span><b>${fmtK(fee)}</b></div>
        </div>
        <div class="dc-actions">
          <button class="dc-btn go" data-act="assign" data-id="${d.id}">💸 Find Cash Buyer</button>
        </div>`;
    }
    list.appendChild(card);
  });
}

function renderHuntStats(){
  const mLvl = S.upgrades.marketing;
  $('leadsPerHunt').textContent = `${1 + Math.floor(mLvl/2)}–${2 + mLvl}`;
  $('mktLevel').textContent = UPGRADES.marketing.desc[mLvl];
}

function renderShop(){
  const list = $('shopList');
  list.innerHTML = '';
  for(const key of Object.keys(UPGRADES)){
    const u = UPGRADES[key];
    const lvl = S.upgrades[key];
    const maxed = lvl >= u.max;
    const cost = maxed ? null : u.cost[lvl+1];
    const canAfford = !maxed && S.cash >= cost;
    const pips = Array.from({length:u.max}, (_,i)=>`<div class="pip ${i<lvl?'on':''}"></div>`).join('');
    const item = document.createElement('div');
    item.className = 'shop-item';
    item.innerHTML = `
      <div class="shop-emoji">${u.emoji}</div>
      <div class="shop-info">
        <div class="shop-name">${u.name}</div>
        <div class="shop-desc">${u.descLine} · <b>${u.desc[lvl]}</b></div>
        <div class="shop-lvl">${pips}</div>
      </div>
      <button class="shop-buy ${maxed?'maxed':canAfford?'':'locked'}" data-up="${key}" ${maxed||!canAfford?'disabled':''}>
        ${maxed ? 'MAX' : `${fmtK(cost)}<small>upgrade</small>`}
      </button>`;
    list.appendChild(item);
  }
}

function renderMarkets(){
  const list = $('marketList');
  list.innerHTML = '';
  MARKETS.forEach(m => {
    const unlocked = S.marketsUnlocked.includes(m.id);
    const active = S.activeMarket === m.id;
    const item = document.createElement('div');
    item.className = 'market-item' + (active?' active-mkt':'') + (!unlocked?' locked-mkt':'');
    let btn;
    if(active) btn = `<button class="shop-buy maxed" disabled>ACTIVE</button>`;
    else if(unlocked) btn = `<button class="shop-buy" data-mkt="${m.id}">SWITCH</button>`;
    else {
      const can = S.cash >= m.cost;
      btn = `<button class="shop-buy ${can?'':'locked'}" data-mkt-buy="${m.id}" ${can?'':'disabled'}>${fmtK(m.cost)}<small>unlock</small></button>`;
    }
    item.innerHTML = `
      <div class="shop-emoji">${m.icon}</div>
      <div class="shop-info">
        <div class="shop-name">${m.name}</div>
        <div class="shop-desc">Home values ${fmtK(m.arv[0])}–${fmtK(m.arv[1])}</div>
      </div>
      ${btn}`;
    list.appendChild(item);
  });
}

function renderStats(){
  const g = $('statGrid');
  const st = S.stats;
  const avg = st.dealsClosed ? st.totalEarned/st.dealsClosed : 0;
  const cells = [
    ['💰', fmtK(st.totalEarned), 'Total Earned'],
    ['🏆', st.dealsClosed, 'Deals Closed'],
    ['📈', fmtK(st.biggest), 'Biggest Deal'],
    ['⚖️', fmtK(avg), 'Avg / Deal'],
    ['🔍', st.leadsFound, 'Leads Found'],
    ['📅', st.daysPlayed, 'Days Hustled'],
  ];
  g.innerHTML = cells.map(c => `
    <div class="stat-card"><div class="s-ico">${c[0]}</div><div class="s-val">${c[1]}</div><div class="s-lbl">${c[2]}</div></div>`).join('');
}

/* ============================================================
   ECONOMICS
   ============================================================ */
// Assignment fee a cash buyer will pay = spread under MAO + network premium.
function assignmentFee(d){
  const nLvl = S.upgrades.network;
  const spread = d.mao - d.contractPrice;          // base profit from the 70% rule gap
  const premium = d.mao * (0.03 + nLvl * 0.012);   // buyer competition premium
  let fee = spread + premium;
  return Math.max(1500, Math.round(fee / 100) * 100);
}

/* ============================================================
   GAME ACTIONS
   ============================================================ */
function spendEnergy(n=1){ S.energy = Math.max(0, S.energy - n); }

function doHunt(){
  if(S.energy < 1){ toast('😴','Out of energy! End the day to refill.','bad'); sfx.fail(); return; }
  sfx.hunt();
  const emoji = $('huntEmoji');
  emoji.classList.add('searching');
  $('huntBtn').disabled = true;

  setTimeout(() => {
    emoji.classList.remove('searching');
    $('huntBtn').disabled = false;
    spendEnergy(1);
    const mLvl = S.upgrades.marketing;
    const count = randInt(1 + Math.floor(mLvl/2), 2 + mLvl);
    let added = 0;
    for(let i=0;i<count;i++){
      if(S.deals.length >= 8) break; // pipeline cap
      S.deals.push(genDeal());
      added++;
    }
    S.stats.leadsFound += added;
    sfx.found();
    emoji.textContent = pick(HOUSE_EMOJIS);
    if(added === 0) toast('📭','Pipeline full! Work your existing leads.','bad');
    else toast('📬', `Found ${added} new lead${added>1?'s':''}!`, 'good');
    maybeRandomEvent();
    save(); renderAll();
    switchTab('deals');
  }, 650);
}

function endDay(){
  S.day++;
  S.stats.daysPlayed++;
  S.energy = ENERGY_BY_LVL[S.upgrades.energy];
  // leads naturally age out a bit — a cold lead may vanish overnight
  const before = S.deals.length;
  S.deals = S.deals.filter(d => d.stage === 'contracted' || d.motivation >= 2 || Math.random() > 0.5);
  const lost = before - S.deals.length;
  sfx.tap();
  toast('🌅', `Day ${S.day} — energy refilled!`, 'good');
  if(lost > 0) setTimeout(()=>toast('🍃', `${lost} cold lead${lost>1?'s':''} went stale.`, 'bad'), 400);
  save(); renderAll();
}

/* ---------- Negotiation modal ---------- */
let activeDealId = null;

function openNegotiate(id){
  const d = S.deals.find(x => x.id === id);
  if(!d) return;
  activeDealId = id;
  sfx.tap();
  const goodDeal = d.mao > d.asking;
  const m = $('dealModal');

  const offers = buildOffers(d);
  const oHtml = offers.map((o,i) => `
    <button class="offer-opt" data-offer="${i}">
      <div class="oo-emoji">${o.emoji}</div>
      <div class="oo-main">
        <div class="oo-name">${o.name}</div>
        <div class="oo-desc">${o.desc}</div>
      </div>
      <div class="oo-right">
        <div class="oo-price">${fmtK(o.price)}</div>
        <div class="oo-odds ${o.oddsCls}">${o.oddsTxt}</div>
      </div>
    </button>`).join('');

  m.innerHTML = `
    <div class="dm-grab"></div>
    <div class="dm-head">
      <div class="dm-emoji">${d.emoji}</div>
      <div>
        <div class="dm-title">${d.addr}</div>
        <div class="dm-sub">${d.cond} · Seller: ${d.reason}</div>
      </div>
    </div>
    <div class="dm-section-label">📊 The Numbers</div>
    <div class="dm-figs">
      <div class="dm-fig"><span>After-Repair Value</span><b>${fmt$(d.arv)}</b></div>
      <div class="dm-fig"><span>Est. Repairs</span><b>${fmt$(d.repairs)}</b></div>
    </div>
    <div class="dm-figs" style="margin-top:8px">
      <div class="dm-fig"><span>Seller Asking</span><b>${fmt$(d.asking)}</b></div>
      <div class="dm-fig hl"><span>Max Offer (70% rule)</span><b>${fmt$(d.mao)}</b></div>
    </div>
    <div class="mao-banner">
      🎯 Stay at or below <b>${fmt$(d.mao)}</b> to lock in a profit.
      ${goodDeal ? 'This seller is priced to move!' : 'Seller wants over your max — negotiate hard!'}
    </div>
    <div class="dm-section-label">🤝 Choose Your Offer</div>
    <div class="offer-opts">${oHtml}</div>
    <button class="btn btn-ghost dm-close" data-close="1" style="color:var(--ink-soft);border-color:#e0d9f2">Walk Away</button>`;

  m.querySelectorAll('[data-offer]').forEach(b =>
    b.addEventListener('click', () => makeOffer(d, offers[+b.dataset.offer])));
  m.querySelector('[data-close]').addEventListener('click', closeModal);
  $('dealOverlay').classList.remove('hidden');
}

function buildOffers(d){
  const nLvl = S.upgrades.negotiation;
  const skillBonus = nLvl * 0.06; // each skill level adds accept odds
  // Three strategies relative to asking price
  const defs = [
    { name:'Lowball', emoji:'😈', mult:0.80, base:0.30, desc:'Big spread, risky' },
    { name:'Fair Offer', emoji:'😊', mult:0.90, base:0.58, desc:'Balanced & solid' },
    { name:'Generous', emoji:'🤲', mult:0.99, base:0.85, desc:'Likely yes, slim margin' },
  ];
  return defs.map(o => {
    const price = Math.round(d.asking * o.mult / 500) * 500;
    // motivation raises odds, price above MAO lowers buyer interest but that's later
    let odds = clamp(o.base + skillBonus + (d.motivation-3)*0.08, 0.08, 0.97);
    const oddsTxt = `${Math.round(odds*100)}% accept`;
    const oddsCls = odds >= 0.7 ? 'odds-hi' : odds >= 0.4 ? 'odds-mid' : 'odds-lo';
    return { ...o, price, odds, oddsTxt, oddsCls };
  });
}

function makeOffer(d, offer){
  if(S.energy < 1){ toast('😴','No energy to negotiate. Rest first!','bad'); sfx.fail(); closeModal(); return; }
  spendEnergy(1);
  const m = $('dealModal');
  // suspense animation
  m.innerHTML = `<div class="dm-grab"></div>
    <div class="nego-anim"><div class="na-emoji">🤔</div><div class="na-text">Calling the seller…</div></div>`;
  const win = Math.random() < offer.odds;

  setTimeout(() => {
    if(win){
      d.stage = 'contracted';
      d.contractPrice = offer.price;
      sfx.found();
      const fee = assignmentFee(d);
      m.innerHTML = `<div class="dm-grab"></div>
        <div class="nego-anim"><div class="na-emoji">📑</div>
        <div class="na-text" style="color:var(--green-d)">Under Contract!</div>
        <p style="font-weight:800;color:var(--ink-soft);margin-top:6px">Locked at ${fmt$(offer.price)} · est. fee ${fmtK(fee)}</p></div>
        <button class="btn btn-hunt" data-close2="1">💸 Now Find a Buyer →</button>`;
      m.querySelector('[data-close2]').addEventListener('click', () => { closeModal(); switchTab('deals'); });
      toast('🤝', `Contract signed on ${d.addr.split(' ').slice(1).join(' ')}!`, 'good');
    } else {
      sfx.fail();
      m.innerHTML = `<div class="dm-grab"></div>
        <div class="nego-anim"><div class="na-emoji">🙅</div>
        <div class="na-text" style="color:var(--red)">Seller declined.</div>
        <p style="font-weight:800;color:var(--ink-soft);margin-top:6px">${pick(['"I need more than that."','"Let me think about it..."','"Another investor offered more."','"Come back with a better number."'])}</p></div>
        <button class="btn btn-ghost" data-retry="1" style="border-color:#e0d9f2;color:var(--ink)">Try Another Offer</button>
        <button class="btn btn-ghost" data-close="1" style="border-color:#e0d9f2;color:var(--ink-soft)">Walk Away</button>`;
      m.querySelector('[data-retry]').addEventListener('click', () => openNegotiate(d.id));
      m.querySelector('[data-close]').addEventListener('click', closeModal);
      toast('🙅','Offer rejected — try again or pass.','bad');
    }
    save(); renderAll();
  }, 900);
}

/* ---------- Assign to buyer ---------- */
function openAssign(id){
  const d = S.deals.find(x => x.id === id);
  if(!d || d.stage !== 'contracted') return;
  sfx.tap();
  const baseFee = assignmentFee(d);
  const nLvl = S.upgrades.network;
  // generate 2-3 buyer offers around the base fee
  const nBuyers = clamp(2 + Math.floor(nLvl/2), 2, 4);
  const buyers = [];
  const BNAMES = [['🏦','Equity Partners'],['👔','J. Caldwell','flip investor'],['🏗️','BuildRight LLC'],
    ['💼','Sona Capital'],['🛠️','FixFast Homes'],['🏠','Hometown Holdings'],['📊','Vertex Group']];
  const used = new Set();
  for(let i=0;i<nBuyers;i++){
    let b; do { b = pick(BNAMES); } while(used.has(b[1])); used.add(b[1]);
    const variance = rand(0.82, 1.18) + (i===0?0.05:0);
    const fee = Math.max(1500, Math.round(baseFee * variance / 100) * 100);
    buyers.push({ emoji:b[0], name:b[1], fee, fast: Math.random()<0.4 });
  }
  buyers.sort((a,b)=>b.fee-a.fee);

  const m = $('dealModal');
  m.innerHTML = `
    <div class="dm-grab"></div>
    <div class="dm-head">
      <div class="dm-emoji">${d.emoji}</div>
      <div><div class="dm-title">Assign the Contract</div>
      <div class="dm-sub">${d.addr} · your cost ${fmt$(d.contractPrice)}</div></div>
    </div>
    <div class="mao-banner">💸 Cash buyers are bidding! Pick who to assign your contract to and pocket the fee.</div>
    <div class="dm-section-label">🤝 Buyer Offers</div>
    <div class="buyer-list">
      ${buyers.map((b,i)=>`
        <button class="offer-opt" data-buyer="${i}">
          <div class="oo-emoji">${b.emoji}</div>
          <div class="oo-main">
            <div class="oo-name">${b.name}</div>
            <div class="oo-desc">${b.fast?'⚡ Fast close, ready now':'Solid cash buyer'}</div>
          </div>
          <div class="oo-right">
            <div class="oo-price" style="color:var(--green-d)">+${fmt$(b.fee)}</div>
            <div class="oo-odds odds-hi">your fee</div>
          </div>
        </button>`).join('')}
    </div>
    <button class="btn btn-ghost" data-close="1" style="border-color:#e0d9f2;color:var(--ink-soft)">Hold the Contract</button>`;
  m.querySelectorAll('[data-buyer]').forEach(btn =>
    btn.addEventListener('click', () => closeDeal(d, buyers[+btn.dataset.buyer].fee)));
  m.querySelector('[data-close]').addEventListener('click', closeModal);
  $('dealOverlay').classList.remove('hidden');
}

function closeDeal(d, fee){
  // small chance the deal falls through even at the end (earnest risk)
  const fallChance = clamp(0.06 - S.upgrades.network*0.01, 0.01, 0.06);
  const m = $('dealModal');
  if(Math.random() < fallChance){
    sfx.fail();
    S.deals = S.deals.filter(x => x.id !== d.id);
    S.stats.fellThrough++;
    m.innerHTML = `<div class="dm-grab"></div>
      <div class="nego-anim"><div class="na-emoji">💥</div>
      <div class="na-text" style="color:var(--red)">Buyer backed out!</div>
      <p style="font-weight:800;color:var(--ink-soft);margin-top:6px">It happens. The contract expired. On to the next one!</p></div>
      <button class="btn btn-ghost" data-close="1" style="border-color:#e0d9f2;color:var(--ink)">Shake it off</button>`;
    m.querySelector('[data-close]').addEventListener('click', () => { closeModal(); switchTab('deals'); });
    toast('💥','Deal fell through — buyer got cold feet.','bad');
    save(); renderAll();
    return;
  }

  // SUCCESS
  S.cash += fee;
  S.stats.totalEarned += fee;
  S.stats.dealsClosed++;
  if(fee > S.stats.biggest) S.stats.biggest = fee;
  const prevRank = currentRank();
  S.deals = S.deals.filter(x => x.id !== d.id);

  sfx.cash();
  fireConfetti();
  m.innerHTML = `<div class="dm-grab"></div>
    <div class="dm-profit-big">
      <div class="pb-num">+${fmt$(fee)}</div>
      <div class="pb-lbl">Wholesale fee collected! 🎉</div>
    </div>
    <div class="dm-figs">
      <div class="dm-fig"><span>You bought at</span><b>${fmt$(d.contractPrice)}</b></div>
      <div class="dm-fig"><span>Assigned for</span><b>${fmt$(d.contractPrice + fee)}</b></div>
    </div>
    <button class="btn btn-hunt" data-close="1">🔥 Find the Next Deal</button>`;
  m.querySelector('[data-close]').addEventListener('click', () => { closeModal(); switchTab(S.deals.length?'deals':'hunt'); });
  toast('💰', `Closed ${d.addr.split(' ').slice(1).join(' ')} for +${fmt$(fee)}!`, 'gold');

  save();
  renderAll();
  // rank-up celebration
  const newRank = currentRank();
  if(newRank.name !== prevRank.name){
    setTimeout(() => { sfx.level(); toast(newRank.icon, `RANK UP! You're now a ${newRank.name}!`, 'gold'); fireConfetti(); }, 600);
  }
}

/* ---------- Random events for flavor & replayability ---------- */
function maybeRandomEvent(){
  if(Math.random() > 0.22) return;
  const events = [
    () => { const bonus = randInt(500,1500); S.cash += bonus; toast('🎁',`Referral bonus! +${fmt$(bonus)}`,'gold'); },
    () => { S.energy = Math.min(ENERGY_BY_LVL[S.upgrades.energy], S.energy+2); toast('☕','Energy drink! +2 energy','good'); },
    () => { // a hot motivated lead appears
      if(S.deals.length < 8){ const d = genDeal(); d.motivation = 5; d.asking = Math.round(d.mao*rand(0.85,0.95)/500)*500; S.deals.push(d); S.stats.leadsFound++; toast('🔥','A super-motivated seller called you!','gold'); } },
    () => { toast('📰','Market is hot — buyers paying top dollar today!','good'); },
  ];
  setTimeout(() => { pick(events)(); save(); renderAll(); }, 500);
}

/* ============================================================
   UPGRADES & MARKETS
   ============================================================ */
function buyUpgrade(key){
  const u = UPGRADES[key];
  const lvl = S.upgrades[key];
  if(lvl >= u.max) return;
  const cost = u.cost[lvl+1];
  if(S.cash < cost){ toast('💸','Not enough cash for that.','bad'); sfx.fail(); return; }
  S.cash -= cost;
  S.upgrades[key]++;
  if(key === 'energy'){ // top off energy when stamina increases
    S.energy = ENERGY_BY_LVL[S.upgrades.energy];
  }
  sfx.buy();
  toast(u.emoji, `${u.name} → ${u.desc[S.upgrades[key]]}!`, 'good');
  save(); renderAll();
}

function switchMarket(id){
  if(!S.marketsUnlocked.includes(id)) return;
  S.activeMarket = id;
  sfx.tap();
  toast(MARKETS.find(m=>m.id===id).icon, `Now hunting in ${MARKETS.find(m=>m.id===id).name}!`, 'good');
  save(); renderAll();
}
function unlockMarket(id){
  const m = MARKETS.find(x=>x.id===id);
  if(S.cash < m.cost){ toast('💸','Not enough to unlock that market.','bad'); sfx.fail(); return; }
  S.cash -= m.cost;
  S.marketsUnlocked.push(id);
  S.activeMarket = id;
  sfx.level(); fireConfetti();
  toast(m.icon, `Unlocked ${m.name}! Bigger homes, bigger fees!`, 'gold');
  save(); renderAll();
}

/* ============================================================
   UI PLUMBING: tabs, modal, toast, confetti
   ============================================================ */
function switchTab(tab){
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  document.querySelectorAll('.tab').forEach(t => t.classList.add('hidden'));
  $('tab-' + tab).classList.remove('hidden');
  $('content').scrollTop = 0;
}

function closeModal(){ $('dealOverlay').classList.add('hidden'); activeDealId = null; }

let toastTimer;
function toast(emoji, text, cls=''){
  const wrap = $('toastWrap');
  const t = document.createElement('div');
  t.className = 'toast ' + cls;
  t.innerHTML = `<span class="t-emoji">${emoji}</span><span>${text}</span>`;
  wrap.appendChild(t);
  setTimeout(() => { t.classList.add('out'); setTimeout(()=>t.remove(), 350); }, 2600);
  // cap stack
  while(wrap.children.length > 3) wrap.firstChild.remove();
}

/* ---------- Confetti ---------- */
const cv = $('confetti'); const cx = cv.getContext('2d');
let confetti = [], confettiRAF = null;
function sizeCanvas(){ cv.width = innerWidth; cv.height = innerHeight; }
sizeCanvas(); addEventListener('resize', sizeCanvas);
const CCOLORS = ['#ff5d8f','#7b5cff','#36c5f0','#36d39a','#ffd23f','#ff924c'];
function fireConfetti(){
  for(let i=0;i<90;i++){
    confetti.push({
      x: innerWidth/2 + rand(-60,60), y: innerHeight*0.4,
      vx: rand(-7,7), vy: rand(-14,-4),
      g: rand(0.25,0.45), size: rand(6,12),
      color: pick(CCOLORS), rot: rand(0,6.28), vr: rand(-0.3,0.3),
      life: rand(60,110),
    });
  }
  if(!confettiRAF) stepConfetti();
}
function stepConfetti(){
  cx.clearRect(0,0,cv.width,cv.height);
  confetti.forEach(p => {
    p.vy += p.g; p.x += p.vx; p.y += p.vy; p.rot += p.vr; p.life--;
    cx.save(); cx.translate(p.x,p.y); cx.rotate(p.rot);
    cx.fillStyle = p.color;
    cx.fillRect(-p.size/2, -p.size/2, p.size, p.size*0.6);
    cx.restore();
  });
  confetti = confetti.filter(p => p.life > 0 && p.y < cv.height + 30);
  if(confetti.length){ confettiRAF = requestAnimationFrame(stepConfetti); }
  else { confettiRAF = null; cx.clearRect(0,0,cv.width,cv.height); }
}

/* ---------- Floating background emojis ---------- */
function spawnFloaties(){
  const wrap = $('floaties');
  const emojis = ['🏠','🏡','💵','🔑','💰','📈','🏢','💎'];
  for(let i=0;i<10;i++){
    const s = document.createElement('span');
    s.textContent = pick(emojis);
    s.style.left = rand(0,100)+'%';
    s.style.fontSize = rand(18,38)+'px';
    s.style.animationDuration = rand(16,34)+'s';
    s.style.animationDelay = -rand(0,30)+'s';
    wrap.appendChild(s);
  }
}

/* ============================================================
   EVENT WIRING
   ============================================================ */
function startGame(){
  $('splash').classList.add('hidden');
  $('game').classList.remove('hidden');
  displayCash = 0;
  renderAll();
  if(!S.seenHow){ S.seenHow = true; save(); }
}

function wire(){
  // splash
  $('playBtn').addEventListener('click', () => { sfx.tap(); startGame(); });
  $('howBtn').addEventListener('click', () => { sfx.tap(); $('howScreen').classList.remove('hidden'); });
  $('howClose').addEventListener('click', () => { sfx.tap(); $('howScreen').classList.add('hidden'); });

  // if save exists, offer wipe
  if(localStorage.getItem(SAVE_KEY)){
    const wipe = $('continueWipe');
    wipe.classList.remove('hidden');
    wipe.addEventListener('click', () => {
      if(confirm('Start a brand new game? Your current empire will be erased.')){
        localStorage.removeItem(SAVE_KEY); S = freshState(); save(); displayCash = 0;
        toast('✨','Fresh start!','good'); startGame();
      }
    });
  }

  // nav
  document.querySelectorAll('.nav-btn').forEach(b =>
    b.addEventListener('click', () => { sfx.tap(); switchTab(b.dataset.tab); }));

  // hunt
  $('huntBtn').addEventListener('click', doHunt);
  $('sleepBtn').addEventListener('click', endDay);
  $('muteBtn').addEventListener('click', () => { S.sound = !S.sound; save(); renderHUD(); if(S.sound) sfx.tap(); });

  // deal list (delegated)
  $('dealList').addEventListener('click', e => {
    const btn = e.target.closest('[data-act]');
    if(!btn) return;
    const id = +btn.dataset.id;
    const act = btn.dataset.act;
    if(act === 'negotiate') openNegotiate(id);
    else if(act === 'assign') openAssign(id);
    else if(act === 'drop'){
      S.deals = S.deals.filter(x => x.id !== id);
      sfx.tap(); toast('🗑️','Passed on the lead.'); save(); renderAll();
    }
  });

  // shop (delegated)
  $('shopList').addEventListener('click', e => {
    const b = e.target.closest('[data-up]'); if(!b || b.disabled) return; buyUpgrade(b.dataset.up);
  });
  $('marketList').addEventListener('click', e => {
    const sw = e.target.closest('[data-mkt]');
    const bu = e.target.closest('[data-mkt-buy]');
    if(sw) switchMarket(sw.dataset.mkt);
    else if(bu && !bu.disabled) unlockMarket(bu.dataset.mktBuy);
  });

  // reset
  $('resetBtn').addEventListener('click', () => {
    if(confirm('Reset your entire career? This cannot be undone.')){
      localStorage.removeItem(SAVE_KEY); S = freshState(); displayCash = 0; save();
      toast('🗑️','Career reset.','bad'); renderAll(); switchTab('deals');
    }
  });

  // overlay click-out
  $('dealOverlay').addEventListener('click', e => { if(e.target.id === 'dealOverlay') closeModal(); });

  spawnFloaties();
}

wire();
// Auto-skip splash if a game is already in progress and they've played a bit
})();
