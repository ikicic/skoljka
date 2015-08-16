/* TODO: replace _ with - */
/*
  PLEASE NOTE:

  To make some function public (and to keep its name), use this format:
    function_name = function(a, b, c) {
      (...)
    }

*/


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


/* Delayed action */
/* http://stackoverflow.com/a/2219966/2203044 */
/*
  Example:
  $(selector).keyup(function () {
    typewatch(function () {
      // executed only 500 ms after the last keyup event.
    }, 500);
  });
*/

typewatch = (function(){
  var timer = 0;
  return function(callback, ms){
    clearTimeout(timer);
    timer = setTimeout(callback, ms);
  }
})();

$(function(){
  /* Automatically add preview button, help link and div after each
   * MathContentForm marked with .mc-auto-preview-button. */
  var counter = 0;
  $('.mc-auto-preview-button').each(function(index) {
    var mc = $(this);
    var form = mc.closest('form');
    var source_id = mc.attr('id');
    if (!source_id) {
      source_id = 'mc-source-auto-id' + counter;
      mc.attr('id', source_id);
    }
    var target_id = 'mc-target-auto-id' + counter;
    form.children('input[type=submit]').after(
        ' <button type="button" class="btn mc-preview-button" ' +
            'data-source="' + source_id + '" ' +
            'data-target="' + target_id + '">' +
          'Pregled</button>' +
        ' <a href="/help/instructions/#format" title="Pomoć oko formata" ' +
            'target="_blank"><i class="icon-question-sign"></i></a>');
    form.append(
      '<div class="mc-preview outset" id="' + target_id + '" ' +
        'style="display:none;"></div>');
    ++counter;
  });

  /* Preview button, send AJAX request to convert to html (and generate
   * necessarry .png files). */
  $('.mc-preview-button').click(function(){
    var source = $('#' + $(this).attr('data-source'));
    var text = source.val();
    /* Currently we ignore only if the response from the last click already
     * arrived, and not if there is an AJAX request still running. */
    if (text == source.data('mc-last-refresh'))
      return;
    var preview = $('#' + $(this).attr('data-target'));
    if (text.length) {
      preview.html("Učitavanje...");
      preview.attr('style', '');
      $.get('/ajax/mathcontent/preview/', {text: text}, function(result){
        source.data('mc-last-refresh', text);
        preview.html(result);
      });
    } else {
      preview.html("");
    }
  });

  /* Trigger click on all preview buttons. */
  $('.mc-preview-all').click(function() {
    console.log('adfasdf');
    $('.mc-preview-button').click();
  });

  /* Refresh all previews on Ctrl-X. */
  $(document).bind('keydown', function(event) {
    if (event.ctrlKey && event.keyCode == 88)
      $('.mc-preview-button').click();
  });
});


/* Reply link for comments, Used for inc_post_list_small.html */
/* MathContent View source & quote link */
function quote(mc) {
  var s = $.trim(mc.find('.mc-viewsource-text').text());
  $('#id_text').val('\n\n[quote]' + s + '[/quote]');
};

function set_reply(id) {
  $('.post-reply-to').removeClass('post-reply-to');
  if (id)
    $('#post' + id).addClass('post-reply-to');

  $('input[name="post_reply_id"]').val(id);
  $('#reply-to-info').attr('style', id ? 'display:inline;' : 'display:none;');
};
window.set_reply = set_reply;

$(function(){
  /* Post reply */
  $('.post-reply').click(function(){
    var id = $(this).attr('id').substr(2)

    set_reply(id);
    quote($(this).closest('.post').find('.mc'));

    var a = $('#reply-to-info a:first')
    a.html(a.html().split(' ')[0] + ' #' + id)
    a.attr('href', '#post' + id)
  });

  /* Cancel post reply */
  $('#reply-to-info a:last').click(function(){
    set_reply('');
  });

  /* MathContent view source link */
  $('body').on('click', '.mc-viewsource-toggle', function(e) {
    e.preventDefault();
    $(this).closest('.mc').find('.mc-viewsource-text').toggle();
  });

  /* MathContent quote link */
  $('body').on('click', '.mc-viewsource-quote', function(e) {
    set_reply('');
    quote($(this).closest('.mc'));
  });
});


/* Task tooltip */
$(function(){
  if (!is_authenticated) return;
  if (!( $('a.task').length)) return;
  $('body').append(
      '<div id="task-tooltip" class="btn-group">'
    + '<a id="task-tt-submit" href="#" title="Pošalji rješenje" class="btn btn-mini"><i class="icon-file"></i></a>'
    + '<a id="task-tt-as-solved" href="#" title="Označi kao riješeno" class="btn btn-mini"><i class="icon-ok"></i></a>'
    + '<a id="task-tt-todo" href="#" title="To Do" class="btn btn-mini"><i class="icon-tag"></i></a>'
    + '<a id="task-tt-blank" href="#" title="Izbriši" class="btn btn-mini"><i class="icon-remove"></i></a>'
    + '</div>'
  );

  var solution_action = function(e, action) {
    e.preventDefault();
    /* The same code is responsible for labels (small task view) and the table rows (table view) */

    /* Find label and mark with '...' */
    var container = $('#task-tooltip').data('container');
    var label_container = container.find('.sol-label-container');
    var label;
    /* If small box, not a table. */
    if (label_container.length > 0) {
      label = label_container.children('.label');
      if (label.length > 0) {
        label.attr('class', 'label');
      } else {
        label_container.append('<span class="label">. . .</span>');
        label = label_container.children('.label');
      }
    }

    $.post('/ajax/task/' + container.attr('data-task-id') + '/', {
        action: action,
      }, function(json) {
        info = $.parseJSON(json);
        if (label) { /* small box */
          if (action == 'blank') {
            label.remove();
          } else {
            label.attr('class', 'label ' + info.label_class);
            label.html(info.label_text);
          }
        } else {  /* table view */
          /* container == tr */
          container.attr('class', 'task-container ' + info.tr_class);
        }
    }).fail(function() {
      if (label)
        label.html('Greška');
      else /* Table view */
        container.children(':first-child').css('color', 'red').attr('title', 'Greška!');
    });
  };

  $('#task-tt-as-solved').click(function(e) {solution_action(e, 'as_solved');});
  $('#task-tt-todo').click(function(e) {solution_action(e, 'todo');});
  $('#task-tt-blank').click(function(e) {solution_action(e, 'blank');});

  /* Tooltip will be shown only for tasks with this marker. */
  $('.task-tt-marker').tooltip({
    tip: '#task-tooltip',
    position: 'bottom center',
    onBeforeShow: function() {
      /* Save container and update submit href. */
      /* Container can be both div and tr. */
      var container = this.getTrigger().closest('.task-container');
      var id = container.attr('data-task-id');
      $('#task-tooltip').data('container', container);
      $('#task-tt-submit').attr('href', '/task/' + id + '/submit/');
    }
  });
});

/* email = even position characters + reversed(odd) (0-based) */
function decode_email(e) {
  var output = '';
  for (var i = 0; i < e.length; ++i)
    output += i % 2 == 0 ? e[i / 2] : e[e.length - (i + 1) / 2];
  return output;
};

$(function() {
  /* Please sort somehow! (e.g. alphabetically by description) */

  /* Decode emails */
  $('.imejl').each(function() {
    var a = $(this);
    var email = decode_email(a.attr('data-address'));
    if (a.html().length == 0)
      a.html(email);
    a.attr('href', 'mailto:' + email);
  });

  /* Delete attachments */
  $('.mc-attachment-delete').click(function() {
    var id = $(this).attr('data-id');
    var name = $(this).attr('data-name');
    if (confirm('Jeste li sigurni da želite izbrisati datoteku \'' + name + '\'?')) {
      $.ajax({
        url: '/attachment/' + id + '/delete/',
        success: function() {
          window.location.reload();
        }
      });
    }
  });

  /* Replace "Cancel Rating" with translation */
  $('.rating-cancel > a').each(function() {
    /* This works only if the following code is evaluated after jquery.rating.js */
    $(this).attr('title', 'Poništi ocjenu');
  });

  /* Search toggler */
  $(".toggler").click(function(e){
    e.preventDefault();
    $(".toggle").toggle();
  });

  /* Task prerequisites ajax information */
  var pre = $('.task-prerequisites')
  pre.attr('data-old', pre.val());  /* remember old value */
  pre.parent().append(' <span id="task-pre-info"></span>');
  pre.keyup(function () {          /* ajax info */
    typewatch(function () {
      var value = pre.val();
      if (value == pre.attr('data-old'))
        return; /* if value not changed, ignore */

      pre.attr('data-old', value);

      $.get('/task/ajax/prerequisites/', {
        ids: value,
        task_id: pre.attr('data-task-id')
      }, function(json) {
        result = $.parseJSON(json);
        var info = $('#task-pre-info');
        if (typeof result == 'string') {
          info.css('color', 'red');
          info.html(result);
        } else {
          info.css('color', '');
          var values = new Array();
          for (var key in result)
            values.push(result[key]);
          info.html(values.join(', '));
        }
      });
    }, 500);
  });
});
