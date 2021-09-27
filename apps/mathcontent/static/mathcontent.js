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
          'Pregled</button> '
        /*
        '<span style="color:gray;font-style:italic;">' +
            'U tijeku je testiranje (nedovršenog) ' +
            '<a href="/help/format/" target="_blank">' +
                'novog formata unosa' +
            '</a>, koji bi trebao biti kompatibilniji samom LaTeX-u. ' +
            'Ukoliko vam ovaj format ne radi ili ako iz bilo kojeg razloga ' +
            'želite stari format, dodajte <code>%V0</code> na početak teksta.' +
        '</span>'
        */
    );
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

  /* Refresh all previews on Ctrl+M. */
  $(document).bind('keydown', function(event) {
    if (event.ctrlKey && event.keyCode == 77)
      $('.mc-preview-button').click();
  });

  /* Handle [hide]...[/hide] show/hide links. */
  $('body').on('click', '.mc-hide-link', function(event) {
      event.preventDefault();
      $(this).next().toggle();
  });
});
