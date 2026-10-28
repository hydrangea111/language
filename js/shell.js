// 저장소: 실행 환경이 window.storage 를 주지 않으면(GitHub Pages 등) 브라우저 localStorage 로 대신한다.
// 자식 문서들은 postMessage 브리지로 이 객체를 쓴다.
if(!window.storage){
  var PFX = 'language:';
  window.storage = {
    get: async function(k){ var v = localStorage.getItem(PFX + k); return v === null ? null : {key:k, value:v}; },
    set: async function(k, v){ localStorage.setItem(PFX + k, v); return {key:k, value:v}; },
    'delete': async function(k){ localStorage.removeItem(PFX + k); return {key:k, deleted:true}; },
    list: async function(prefix){
      var keys = [];
      for(var i = 0; i < localStorage.length; i++){
        var n = localStorage.key(i);
        if(n.indexOf(PFX) === 0 && n.slice(PFX.length).indexOf(prefix || '') === 0) keys.push(n.slice(PFX.length));
      }
      return {keys:keys};
    }
  };
}

// 자식 iframe -> 부모 storage 브리지
addEventListener('message', async function(e){
  var d = e.data; if(!d || d.__st !== 'req') return;
  var val = null, err = null;
  try{
    if(!window.storage) throw new Error('no storage');
    val = await window.storage[d.m].apply(window.storage, d.a);
  }catch(ex){ err = String((ex && ex.message) || ex); }
  try{ e.source.postMessage({__st:'res', id:d.id, val:val, err:err}, '*'); }catch(x){}
});

var fH = document.getElementById('f-hanja'), fL = document.getElementById('f-lang'), fY = document.getElementById('f-yue');
var btns = [].slice.call(document.querySelectorAll('#tabbar button'));
var cur = 'hanja';

function show(tab){
  cur = tab;
  btns.forEach(function(b){ b.setAttribute('aria-pressed', String(b.dataset.tab === tab)); });
  var yue = (tab === 'yue');
  var lang = (tab !== 'hanja' && !yue);
  if(yue && !fY.getAttribute('src')) fY.setAttribute('src', fY.dataset.src);   // 광동어는 처음 열 때만 불러온다
  fH.classList.toggle('on', tab === 'hanja');
  fL.classList.toggle('on', lang);
  fY.classList.toggle('on', yue);
  if(lang){
    try{ fL.contentWindow.postMessage({__st:'lang', lang:tab}, '*'); }catch(x){}
  }
  try{ window.storage && window.storage.set('shell:tab', JSON.stringify(tab)); }catch(x){}
}
btns.forEach(function(b){ b.addEventListener('click', function(){ show(b.dataset.tab); }); });

// 마지막에 보던 탭 복원
(async function(){
  try{
    var r = await window.storage.get('shell:tab');
    var t = r ? JSON.parse(r.value) : null;
    if(t === 'yue'){ show('yue'); }
    else if(['hanja','ja','zh','es'].indexOf(t) >= 0 && t !== 'hanja'){
      fL.addEventListener('load', function(){ show(t); }, {once:true});
      if(fL.contentDocument && fL.contentDocument.readyState === 'complete') show(t);
    }
  }catch(x){}
})();
