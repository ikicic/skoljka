$(function() {
  // Used in in_task_table_list.html.
  $('.folder-checkbox').click(function() {
    var id = $(this).data('id');
    return $.post("/folder/select/task/" + id + "/", {
      checked: $(this).prop('checked')
    });
  });
});
