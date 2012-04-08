/* Django & Ajax POST method */
/* http://stackoverflow.com/questions/5100539/django-csrf-check-failing-with-an-ajax-post-request */
$.ajaxSetup({ 
     beforeSend: function(xhr, settings) {
         function getCookie(name) {
             var cookieValue = null;
             if (document.cookie && document.cookie != '') {
                 var cookies = document.cookie.split(';');
                 for (var i = 0; i < cookies.length; i++) {
                     var cookie = jQuery.trim(cookies[i]);
                     // Does this cookie string begin with the name we want?
                 if (cookie.substring(0, name.length + 1) == (name + '=')) {
                     cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                     break;
                 }
             }
         }
         return cookieValue;
         }
         if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
             // Only send the token to relative URLs i.e. locally.
             xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
         }
     } 
});

/* Automatically add preview button, help link and div after MathContentForm */
$(function(){
 mc=$('.mathcontent_text');
 f=mc.closest('form');
 /* Preview button and help link */
 f.children('input[type=submit]').after(
     ' <button type="button" class="btn mathcontent_preview_button">Pregled</button>'
   + ' <a href="/help/#format" title="Pomoć oko formata" target="_blank"><i class="icon-question-sign"></i></a>'
 )
 f.append('<br><div class="mathcontent_preview well" style="display:none;"></div>')

 /* Preview button, send AJAX request to convert to html (and generate necessarry .png files) */
 $('.mathcontent_preview_button').click(function(){
  t=$('.mathcontent_text').val();
  p=$('.mathcontent_preview');
  p.html('Učitavanje...');
  p.attr('style', 'block');
  $.get('/ajax/mathcontent/preview/', {text: t}, function(d){
   p.html(d);
  });
 });
});

/* Used for inc_post_list_small.html */
$(function(){
 $('.post_reply').click(function(){
  id=$(this).attr('id').substr(2)
  $('.post_reply_to').removeClass('post_reply_to');
  $('#post'+id).addClass('post_reply_to');
  $('input[name="post_reply_id"]').val(id);
   
  s='\n\n[quote]'+$(this).next().html()+'[/quote]';
  $('#id_text').val(s);

  $('#reply_to_info').attr('style', 'inline')       
  a = $('#reply_to_info a:first')
  a.html('komentar #'+id)
  a.attr('href', '#post'+id)
 });
});
$(function(){
 $('#reply_to_info a:last').click(function(){
  $('.post_reply_to').removeClass('post_reply_to');
  $('input[name="post_reply_id"]').val('');
  $('#reply_to_info').attr('style', 'display:none;');
 });
});



/* Tag tooltip & add new tag */
$(function(){
  if(!($('.tag_list').length))return;
  $('body').append(
      '<div id="tag_tooltip" class="tag_tooltip">'
    + '<span id="tt_text"></span> '
    + '<a id="tt_plus" href="#" title="Valjan"><img src="/static/images/plus_circle.png"></a> '
    + '<a id="tt_minus" href="#" title="Nevaljan"><img src="/static/images/minus_circle.png"></a> '
    + '<a id="tt_delete" href="#" title="Izbriši"><img src="/static/images/cross.png"></a> '
    + '<span id="tt_info"></span><br>'
    + '<input type="text" id="tt_add" name="tt_add" placeholder="Dodaj tag" class="input-small"></div>'
  );
  
  /* Add tag */
  $('#tt_add').keypress(function(event){
   name = $(this).val()
   if (event.which != 13 || name.length == 0) return;
   $(this).val('');
   $('#tt_info').html('Slanje...');
   $.post('/ajax/tag/add/', {
     name: name,
     task: $('#tt_text').data('tag').parent().attr('data-task')
   }, function(data){
     ok = data == '1'
     $('#tt_info').html(ok ? 'Spremljeno' : 'Greška');
     if (ok) $('#tt_text').data('tag').parent().append(' | ' + name);
   });
  });
  
  /* Delete tag */
  $('#tt_delete').click(function(e){
    e.preventDefault();
    tag=$('#tt_text').data('tag');
    $('#tt_info').html('...');
    $.post('/ajax/tag/delete/', {
      name: tag.html(),
      task: tag.parent().attr('data-task')
    }, function(data) {
      if ( data == '1' ) {
        $('#tt_text').data('tooltip').hide();
        tag.remove();
      } else {
        msg = data == '0' ? 'Nemaš prava.' : 'Greška!';
        $('#tt_info').html(msg);
      }
    });
  });

  /* Tag tooltip */
  vote_func = function(e,v){
    e.preventDefault();
    tag=$('#tt_text').data('tag');
    $('#tt_info').html('...');
    $.post('/ajax/tag/vote/', {
      value: v,
      tag: tag.html(),
      task: tag.parent().attr('data-task')
    }, function(data){
      tag.attr('data-votes', data);      
      $('#tt_info').html('');
      $('#tt_text').html(data); /* bug if response is delayed */
    });
  }
  $('#tt_plus').click(function(e){vote_func(e,1)});
  $('#tt_minus').click(function(e){vote_func(e,-1)});

  $('.tag_list a').tooltip({
    tip: '#tag_tooltip',
    position: 'bottom center',
    onBeforeShow: function(){
      tag=this.getTrigger();
      x=$('#tt_text');
      x.html(tag.attr('data-votes'));
      x.data('tag', tag);
      x.data('tooltip', this);
    }
  });
});

/* Task tooltip */
$(function(){
  /* NOT COMPLETED */
  return;
  if(!($('a.task').length))return;
  $('body').append(
      '<div id="task_tooltip" class="task_tooltip btn-group">'
    + '<a id="task_tt_submit" href="#" title="Pošalji rješenje" class="btn btn-mini"><i class="icon-file"></i></a>'
    + '<a id="task_tt_as_solved" href="#" title="Označi kao riješeno" class="btn btn-mini"><i class="icon-ok"></i></a>'
    + '<a id="task_tt_todo" href="#" title="To Do" class="btn btn-mini"><i class="icon-tag"></i></a>'
    + '</div>'
  );
  
  $('a.task').tooltip({
    tip: '#task_tooltip',
    position: 'bottom center',
  });
});


/* UserProfile solved task list, view solution link */
$(function(){
  $('span.task_submitted').hover(
    function(){
      id=$(this).attr('data-solution');
      $(this).append(' <a id="view_solution123" href="/solution/'+id+'/"><i class="icon-search"></i></a>');
    }, function(){$('#view_solution123').remove();});
});
