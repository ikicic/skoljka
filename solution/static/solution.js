$(function(){
  /* Show / hide task text */
  $('#solution-toggle-task').click(function(e) {
    e.preventDefault();
    var div = $('#solution-task');

    var content_id = div.attr('data-content-id');
    if (content_id) {
      /* Mark as 'loading...' */
      div.attr('data-content-id', '');
      div.html('Učitavam...');

      var quote = div.attr('data-quote') == '1' ? 'quote/' : '';
      $.get('/ajax/mathcontent/' + content_id + '/' + quote, {}, function(d) {
        div.html(d);
      });
    }

    $(this).html(div.is(':visible') ? '(Prikaži tekst zadatka)'
      : '(Sakrij tekst zadatka)');
    div.toggle();
  });

  /* Toggle votes */
  $('#solution-ratings-toggle').click(function(e) {
    e.preventDefault();
    $('#solution-ratings').toggle();
  });

  /* 'Not solved' warning. Click to show solution text. */
  $('#solution-unhide-box').click(function(e) {
    $('#solution-unhide-box').attr('style', 'display:none;');
    $('#solution-inner-container').attr('style', 'visibiliy:visible;');
  });

});
