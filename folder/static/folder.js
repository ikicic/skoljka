$(function() {
  $('#folder-adv-history-select').change(function() {
    var index = parseInt($(this).val()[0].split('.')[0]) - 1;
    $('#folder-adv-history-view').text(folder_history_array[index])
  })

  $('.folder-checkbox').click(function() {
    /* Used for inc_task_table_list.html. */
    $.post(
      '/folder/select/task/' + $(this).data('id') + '/',
      {checked: $(this).prop('checked')}
    );
  });
});
