/* 일본어·중국어·스페인어 탭: 단어, 가나, 예문 옆에 🔊 버튼을 붙여 브라우저 음성으로 읽어 준다. */
(function () {
  var LANGS = { ja: 'ja-JP', zh: 'zh-CN', es: 'es-ES' };
  var HANGUL = /[가-힣]/;
  var toastEl;

  function toast(msg) {
    if (!toastEl) { toastEl = document.createElement('div'); toastEl.className = 'tts-toast'; document.body.appendChild(toastEl); }
    toastEl.textContent = msg; toastEl.hidden = false;
    clearTimeout(toast.t); toast.t = setTimeout(function () { toastEl.hidden = true; }, 2200);
  }

  function curLang() {
    var m = document.body.className.match(/lang-(ja|zh|es)/);
    return m ? m[1] : 'ja';
  }

  function speak(text) {
    if (!('speechSynthesis' in window)) return toast('이 브라우저는 음성을 지원하지 않아요.');
    var tag = LANGS[curLang()], pre = tag.slice(0, 2).toLowerCase();
    var voices = speechSynthesis.getVoices();
    var v = voices.find(function (x) { return x.lang.replace('_', '-').toLowerCase() === tag.toLowerCase(); }) ||
            voices.find(function (x) { return x.lang.slice(0, 2).toLowerCase() === pre; });
    if (!v && voices.length) return toast('이 기기에는 이 언어의 음성이 없어요.');
    var u = new SpeechSynthesisUtterance(text);
    u.lang = v ? v.lang : tag; if (v) u.voice = v; u.rate = 0.9;
    speechSynthesis.cancel(); speechSynthesis.speak(u);
  }

  /* 요소가 직접 가진 글자만 모은다(옆에 붙은 병음·읽기 span, 버튼은 제외). */
  function ownText(el) {
    var s = '';
    el.childNodes.forEach(function (n) { if (n.nodeType === 3) s += n.nodeValue; });
    return s.replace(/[~〜～]/g, '').replace(/\s+/g, ' ').trim();
  }

  function speakable(el) {
    var t = ownText(el);
    if (!t || HANGUL.test(t)) return '';                       // 한국어 뜻 문제는 읽지 않는다
    if (curLang() === 'ja' && /^[一-鿿]$/.test(t)) return '';  // 한자 한 글자는 읽는 법이 여러 개라 제외
    return t;
  }

  var SEL = '.face .word, .face .glyph, .ex .s, .e .s, .row .t > b, .qcard .qmid, .qcard .qbig';

  function decorate() {
    var stage = document.getElementById('stage'); if (!stage) return;
    stage.querySelectorAll(SEL).forEach(function (el) {
      if (el.querySelector(':scope > .tts') || !speakable(el)) return;
      var b = document.createElement('button');
      b.type = 'button'; b.className = 'tts'; b.textContent = '🔊'; b.setAttribute('aria-label', '소리 듣기');
      el.appendChild(b);
    });
  }

  /* 눌린 곳에서 읽을 글자를 찾는다. 가장 안쪽에 있는 대상이 우선이라, 예문을 누르면 예문, 단어를 누르면 단어를 읽는다. */
  function textFor(el) {
    if (el.matches('.opt')) {                                   // 퀴즈 보기: 번호(.k)는 빼고 읽는다
      var t = Array.prototype.map.call(el.children, function (c) { return c.classList.contains('k') ? '' : c.textContent; }).join(' ').trim();
      return t && !HANGUL.test(t) ? t : '';
    }
    if (el.matches('.gcell')) {                                 // 가나표 칸
      var k = el.querySelector('b'); return k ? k.textContent.trim() : '';
    }
    if (el.id === 'card') {                                     // 카드 어디를 눌러도 앞면 단어를 읽는다
      var w = el.querySelector('.front .word, .front .glyph');
      return w ? speakable(w) : '';
    }
    return speakable(el);
  }

  document.addEventListener('click', function (e) {
    var tgt = e.target.closest && e.target.closest('.tts');
    if (tgt) {                                                   // 🔊 버튼: 카드 뒤집기로 번지지 않게 막는다
      e.stopPropagation(); e.preventDefault();
      var t0 = speakable(tgt.parentNode); if (t0) speak(t0);
      return;
    }
    var el = e.target.closest && e.target.closest(SEL + ', .opt, .gcell, #card');
    if (!el || !document.getElementById('stage').contains(el)) return;
    var t = textFor(el); if (t) speak(t);                        // 원래 동작(뒤집기, 정답 선택)은 그대로 진행
  }, true);
  document.addEventListener('keydown', function (e) {
    if ((e.key === 'Enter' || e.key === ' ') && e.target.closest && e.target.closest('.tts')) e.stopPropagation();
  }, true);

  var pending = false;
  function schedule() { if (pending) return; pending = true; requestAnimationFrame(function () { pending = false; decorate(); }); }
  var stage = document.getElementById('stage');
  if (stage) new MutationObserver(schedule).observe(stage, { childList: true, subtree: true });
  if ('speechSynthesis' in window) speechSynthesis.getVoices();   // 음성 목록 미리 불러오기
  schedule();
})();
