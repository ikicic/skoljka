$ ->
  # Used in inc_task_table_list.html
  $('.folder-checkbox').click ->
    id = $(this).data 'id'

    $.post(
      "/folder/select/task/#{id}/"
      {checked: $(this).prop 'checked'}
    )
