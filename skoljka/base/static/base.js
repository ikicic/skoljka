$(function() {
  $('.collapse-button').each(function() {
    // Add toggle icon.
    var target_id = $(this).attr('data-target');
    $(this).html(
      $('#' + target_id).is(':hidden')
          ? '<i class="icon-chevron-down"></i>'
          : '<i class="icon-chevron-up"></i>'
    );
  });

  $('.collapse-button').click(function(event) {
    event.preventDefault();
    var target_id = $(this).attr('data-target');
    var icon = $(this).children('i');
    if (icon.attr('class') === 'icon-chevron-up')
      icon.attr('class', 'icon-chevron-down');
    else
      icon.attr('class', 'icon-chevron-up');
    $('#' + target_id).toggle();
  });

  $('.auto-toggler').click(function(event) {
    event.preventDefault();
    var target_id = $(this).attr('data-target');
    $('#' + target_id).toggle();
  });

  $('#history-select').change(function() {
    var index = parseInt($(this).val());
    $('#history-view').text(history_array[index]);
  });
});
