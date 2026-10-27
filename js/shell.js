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

var fH = document.getElementById('f-hanja'), fL = document.getElementById('f-lang');
var btns = [].slice.call(document.querySelectorAll('#tabbar button'));
var cur = 'hanja';

function show(tab){
  cur = tab;
  btns.forEach(function(b){ b.setAttribute('aria-pressed', String(b.dataset.tab === tab)); });
  var lang = (tab !== 'hanja');
  fH.classList.toggle('on', !lang);
  fL.classList.toggle('on', lang);
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
    if(['hanja','ja','zh','es'].indexOf(t) >= 0 && t !== 'hanja'){
      fL.addEventListener('load', function(){ show(t); }, {once:true});
      if(fL.contentDocument && fL.contentDocument.readyState === 'complete') show(t);
    }
  }catch(x){}
})();
