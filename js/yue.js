/* 광동어 학습: 한자 · 단어 · 예문 / 카드 · 문제 · 목록.  데이터는 처음 열 때 종류별로 내려받는다. */
(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const shuffle = a => { for (let i = a.length - 1; i > 0; i--) { const j = (Math.random() * (i + 1)) | 0; [a[i], a[j]] = [a[j], a[i]]; } return a; };
  const short = s => (s.length > 52 ? s.slice(0, 52) + '…' : s);

  // 학습 기록은 이 브라우저에만 저장한다
  const KEY = 'yue:known';
  let known = {};
  try { known = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { /* 저장소를 못 쓰면 이번 방문에만 기억 */ }
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(known)); } catch (e) { /* 무시 */ } };

  const MAIN = [['hanzi', '한자'], ['words', '단어'], ['sent', '예문']];
  const MODES = [['card', '카드'], ['quiz', '문제'], ['list', '목록']];
  const SRC = { hanzi: 'data/yue-hanzi.json', words: 'data/yue-words.json', sent: 'data/yue-sent.json' };
  const CONV = {
    hanzi: r => ({ id: 'h:' + r[0], front: r[0], jy: r[1], sub: r[3] ? '한자음 ' + r[3] : '', ko: r[5], en: r[2], tier: r[4], kind: 'g' }),
    words: r => ({ id: 'w:' + r[0], front: r[0], jy: r[1], sub: '', ko: r[4], en: r[2], tier: r[3], kind: 'w' }),
    sent: (r, i) => ({ id: 's:' + r[0], front: r[0], jy: r[1], sub: '', ko: r[3], en: r[2], tier: Math.floor(i / 500) + 1, kind: 's' }),
  };
  const GLYPH = { g: 'glyph', w: 'glyph w', s: 'glyph s' };
  const meaning = x => x.ko || x.en;

  const data = {};
  const S = { main: 'hanzi', mode: 'card', tier: 1, i: 0, flip: false, shown: 60, q: '' };

  const view = $('view'), foot = $('foot'), footBtns = $('footBtns');
  const items = () => data[S.main] || [];
  const list = () => items().filter(x => x.tier === S.tier);
  const tiers = () => [...new Set(items().map(x => x.tier))].sort((a, b) => a - b);
  const knownIn = L => L.filter(x => known[x.id]).length;

  async function load(main) {
    if (data[main]) return;
    const r = await fetch(SRC[main]);
    if (!r.ok) throw new Error(r.status);
    data[main] = (await r.json()).map(CONV[main]);
  }

  function toast(msg) {
    let t = document.querySelector('.toast');
    if (!t) { t = document.createElement('div'); t.className = 'toast'; document.body.appendChild(t); }
    t.textContent = msg; t.hidden = false;
    clearTimeout(toast.t); toast.t = setTimeout(() => { t.hidden = true; }, 2200);
  }

  function speak(text) {
    if (!('speechSynthesis' in window)) return toast('이 브라우저는 음성을 지원하지 않아요.');
    const v = speechSynthesis.getVoices().find(v => /zh[-_]HK|yue/i.test(v.lang));
    if (!v) return toast('이 기기에는 광동어 음성이 없어요.');
    const u = new SpeechSynthesisUtterance(text);
    u.voice = v; u.lang = v.lang; u.rate = 0.9;
    speechSynthesis.cancel(); speechSynthesis.speak(u);
  }

  /* ── 위쪽 컨트롤 ── */
  function drawControls() {
    $('main').innerHTML = MAIN.map(([k, n]) => `<button role="tab" aria-pressed="${S.main === k}" data-main="${k}">${n}</button>`).join('');
    $('modes').innerHTML = MODES.map(([k, n]) => `<button aria-pressed="${S.mode === k}" data-mode="${k}">${n}</button>`).join('');
    $('tiers').innerHTML = S.mode === 'list' ? '' : tiers().map(t => {
      const L = items().filter(x => x.tier === t);
      return `<button class="chip" aria-pressed="${S.tier === t}" data-tier="${t}"><span class="dot"></span>${t}단계 <span class="n">${L.length}</span></button>`;
    }).join('');
    $('tiers').hidden = S.mode === 'list';
    const all = items(), L = S.mode === 'list' ? all : list();
    $('sub').innerHTML = `익힌 항목 <b>${Object.keys(known).length}</b>`;
    $('metaL').textContent = S.mode === 'list' ? '전체 목록' : `${S.tier}단계`;
    $('metaR').innerHTML = `<b>${knownIn(L)}</b> / ${L.length} 익힘`;
    $('bar').style.width = L.length ? (knownIn(L) / L.length) * 100 + '%' : '0%';
  }

  /* ── 카드 ── */
  function frontHtml(x) { return `<span class="${GLYPH[x.kind]}">${esc(x.front)}</span>`; }

  function renderCard() {
    const L = list();
    if (!L.length) { view.innerHTML = '<div class="empty">이 단계에는 항목이 없어요.</div>'; foot.hidden = true; return; }
    S.i = Math.min(S.i, L.length - 1);
    const x = L[S.i];
    const back = x.kind === 's'
      ? `<span class="reading sm">${esc(x.jy)}</span><span class="mean">${esc(meaning(x))}</span>${x.ko ? `<span class="en">${esc(x.en)}</span>` : ''}`
      : `<span class="reading">${esc(x.jy)}</span>${x.sub ? `<span class="kr">${esc(x.sub)}</span>` : ''}<span class="mean">${esc(short(meaning(x)))}</span>${x.ko ? `<span class="en">${esc(short(x.en))}</span>` : ''}`;
    view.innerHTML = `<div class="cardwrap">
      <button class="card${S.flip ? ' flipped' : ''}" id="card" aria-label="카드 뒤집기">
        <span class="face front"><span class="badge">${known[x.id] ? '✓ 익힘' : S.tier + '단계'}</span>${frontHtml(x)}<span class="hint">눌러서 발음·뜻 보기</span></span>
        <span class="face back">${back}</span>
      </button>
      <button class="speak" id="speak" aria-label="소리 듣기">🔊</button></div>
      <div class="nav"><button class="round" id="prev" aria-label="이전" ${S.i === 0 ? 'disabled' : ''}>←</button>
        <div class="pos">${S.i + 1} / ${L.length}</div>
        <button class="round" id="next" aria-label="다음" ${S.i >= L.length - 1 ? 'disabled' : ''}>→</button></div>`;
    footBtns.innerHTML = '<button class="btn ghost" data-act="again">다시 볼래요</button><button class="btn solid" data-act="got">외웠어요</button>';
    foot.hidden = false;
  }

  function go(d) {
    const L = list();
    S.i = Math.max(0, Math.min(L.length - 1, S.i + d));
    S.flip = false; renderCard();
  }

  /* ── 문제 ── */
  function renderQuiz() {
    foot.hidden = true;
    const L = list();
    if (L.length < 4) { view.innerHTML = '<div class="empty">문제를 만들 항목이 부족해요.</div>'; return; }
    const pool = L.filter(x => !known[x.id]);
    const src = pool.length ? pool : L;
    const x = src[(Math.random() * src.length) | 0];
    const others = shuffle(L.filter(y => y !== x && short(meaning(y)) !== short(meaning(x)))).slice(0, 3);
    const opts = shuffle([x, ...others]);
    view.innerHTML = `<div class="qbox"><span class="${GLYPH[x.kind]}">${esc(x.front)}</span>
        <button class="speak" id="speak" aria-label="소리 듣기">🔊</button></div>
      <div class="opts">${opts.map((o, i) => `<button class="opt" data-k="${i}">${esc(short(meaning(o)))}</button>`).join('')}</div>
      <div id="qres"></div>`;
    view.dataset.speak = x.front;
    view.querySelectorAll('.opt').forEach((b, i) => b.addEventListener('click', () => {
      const ok = opts[i] === x;
      view.querySelectorAll('.opt').forEach((c, k) => { c.disabled = true; if (opts[k] === x) c.classList.add('right'); });
      if (!ok) b.classList.add('wrong');
      if (ok) known[x.id] = 1; else delete known[x.id];
      save(); drawControls();
      $('qres').innerHTML = `<div class="verdict ${ok ? 'ok' : 'no'}">${ok ? '정답!' : '아쉬워요'} · ${esc(x.jy)}</div>
        <button class="btn solid" id="qnext" style="margin-top:10px">다음 문제</button>`;
      $('qnext').addEventListener('click', renderQuiz);
    }));
  }

  /* ── 목록 ── */
  function renderList() {
    foot.hidden = true;
    const q = S.q.trim().toLowerCase();
    const all = items().filter(x => !q || (x.front + ' ' + x.jy + ' ' + (x.ko || '') + ' ' + x.en).toLowerCase().includes(q));
    const rows = all.slice(0, S.shown).map(x => `<div class="row">
      <div class="g${x.kind === 's' ? ' s' : ''}">${esc(x.front)}</div>
      <div class="t"><b>${esc(x.kind === 's' ? meaning(x) : x.jy)}</b><i>${esc(short(x.kind === 's' ? x.jy : meaning(x)))}</i></div>
      <button class="mk${known[x.id] ? ' on' : ''}" data-id="${esc(x.id)}" aria-label="익힘 표시">✓</button></div>`).join('');
    view.innerHTML = `<input class="search" id="search" placeholder="한자, 발음, 뜻으로 찾기" value="${esc(S.q)}">
      ${rows || '<div class="empty">찾는 항목이 없어요.</div>'}
      ${all.length > S.shown ? `<button class="more" id="more">더 보기 (${all.length - S.shown}개 남음)</button>` : ''}`;
    const s = $('search'); s.setSelectionRange(s.value.length, s.value.length);
  }

  /* ── 라우터 ── */
  async function render() {
    drawControls();
    view.removeAttribute('data-speak');
    if (!data[S.main]) {
      view.innerHTML = '<div class="empty">불러오는 중…</div>';
      try { await load(S.main); } catch (e) { view.innerHTML = '<div class="empty">데이터를 불러오지 못했어요. 새로고침 해 주세요.</div>'; return; }
      if (!tiers().includes(S.tier)) S.tier = tiers()[0];
      drawControls();
    }
    if (S.mode === 'card') renderCard(); else if (S.mode === 'quiz') renderQuiz(); else renderList();
    if (S.mode === 'card') view.dataset.speak = (list()[S.i] || {}).front || '';
  }

  document.addEventListener('click', e => {
    const t = e.target.closest('button, input');
    if (!t) return;
    if (t.dataset.main) { S.main = t.dataset.main; S.tier = 1; S.i = 0; S.flip = false; S.shown = 60; S.q = ''; render(); }
    else if (t.dataset.mode) { S.mode = t.dataset.mode; S.i = 0; S.flip = false; S.shown = 60; render(); }
    else if (t.dataset.tier) { S.tier = +t.dataset.tier; S.i = 0; S.flip = false; render(); }
    else if (t.id === 'card') { S.flip = !S.flip; t.classList.toggle('flipped', S.flip); }
    else if (t.id === 'prev') go(-1);
    else if (t.id === 'next') go(1);
    else if (t.id === 'speak') speak(view.dataset.speak || (list()[S.i] || {}).front || '');
    else if (t.id === 'more') { S.shown += 60; renderList(); }
    else if (t.classList.contains('mk')) { const id = t.dataset.id; if (known[id]) delete known[id]; else known[id] = 1; save(); t.classList.toggle('on'); drawControls(); }
    else if (t.dataset.act) {
      const x = list()[S.i];
      if (t.dataset.act === 'got') known[x.id] = 1; else delete known[x.id];
      save(); S.flip = false;
      if (S.i < list().length - 1) S.i++;
      drawControls(); renderCard();
    }
  });
  document.addEventListener('input', e => { if (e.target.id === 'search') { S.q = e.target.value; S.shown = 60; renderList(); } });
  document.addEventListener('keydown', e => {
    if (S.mode !== 'card' || e.target.tagName === 'INPUT') return;
    if (e.key === 'ArrowRight') go(1); else if (e.key === 'ArrowLeft') go(-1);
    else if (e.key === ' ') { e.preventDefault(); S.flip = !S.flip; const c = $('card'); if (c) c.classList.toggle('flipped', S.flip); }
  });
  if ('speechSynthesis' in window) speechSynthesis.getVoices();   // 음성 목록 미리 불러오기

  render();
})();
