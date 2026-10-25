(function(){
  var btn=document.querySelector('.menu-btn'), nav=document.getElementById('site-nav');
  if(btn&&nav){btn.addEventListener('click',function(){var o=nav.classList.toggle('open');btn.setAttribute('aria-expanded',o?'true':'false');});}
  document.querySelectorAll('.yt').forEach(function(box){
    var b=box.querySelector('.yt-btn'); if(!b) return;
    b.addEventListener('click',function(){
      var f=document.createElement('iframe');
      f.src='https://www.youtube-nocookie.com/embed/'+box.getAttribute('data-yt')+'?autoplay=1';
      f.title='YouTube video'; f.allow='accelerometer; autoplay; encrypted-media; picture-in-picture'; f.allowFullscreen=true;
      box.innerHTML=''; box.appendChild(f);
    });
  });
})();
