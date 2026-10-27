(function(){var seq=0,pend={};
addEventListener('message',function(e){var d=e.data;if(!d||d.__st!=='res')return;var p=pend[d.id];if(!p)return;delete pend[d.id];d.err?p.rej(new Error(d.err)):p.res(d.val);});
function call(m,a){return new Promise(function(res,rej){var id=++seq;pend[id]={res:res,rej:rej};
try{parent.postMessage({__st:'req',id:id,m:m,a:a},'*');}catch(x){delete pend[id];rej(x);return;}
setTimeout(function(){if(pend[id]){delete pend[id];rej(new Error('timeout'));}},4000);});}
window.storage={get:function(k,s){return call('get',[k,!!s])},set:function(k,v,s){return call('set',[k,v,!!s])},
'delete':function(k,s){return call('delete',[k,!!s])},list:function(p,s){return call('list',[p,!!s])}};
})();
