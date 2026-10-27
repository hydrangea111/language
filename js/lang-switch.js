addEventListener('message',function(e){var d=e.data;if(!d||d.__st!=='lang')return;
var b=document.querySelector('.langbar button[data-lang="'+d.lang+'"]');
if(b&&b.getAttribute('aria-pressed')!=='true')b.click();});
