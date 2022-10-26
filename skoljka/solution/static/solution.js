$(function() {
  // Show / hide task text.
  $('#solution-toggle-task').click(function(event) {
    event.preventDefault();
    var div = $('#solution-task');
    $(this).html(div.is(':visible') ? '(Prikaži tekst zadatka)'
                                    : '(Sakrij tekst zadatka)');
    div.toggle();
  });

  // Toggle votes.
  $('#solution-ratings-toggle').click(function(event) {
    event.preventDefault();
    $('#solution-ratings').toggle();
  });

  // 'Not solved' warning. Click to show the solution text.
  $('#solution-unhide-box').click(function(event) {
    $('#solution-unhide-box').attr('style', 'display: none;');
    $('#solution-inner-container').attr('style', 'visibility: visible;');
  });
});
