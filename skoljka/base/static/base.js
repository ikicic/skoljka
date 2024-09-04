$(function() {
  console.log("DOM loaded (base.js)");
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

  var b = document.querySelector('#change-theme-btn');
  b.addEventListener('mouseenter', function() {
    console.log("change-theme-btn mouseenter");
  });
  b.addEventListener('mouseleave', function() {
    console.log("change-theme-btn mouseleave");
  });
});