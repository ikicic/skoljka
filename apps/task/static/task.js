$(function() {
  /* tb == task-bulk */
  $('#tb-preview-button').click(function(event) {
    event.preventDefault();
    $('#tb-loading-indicator').show();
    var text = $(this).closest('form').find('textarea').val();
    $.get(
        '/task/ajax/bulk/preview/',
        {text: text},
        function(result) {
          $('#tb-loading-indicator').hide()
          $('#tb-preview').html(result);
        });
  });

  /* Refresh bulk preview on Ctrl+M. */
  $(document).bind('keydown', function(event) {
    if (event.ctrlKey && event.keyCode === 77)
      $('#tb-preview-button').click();
  });
});
