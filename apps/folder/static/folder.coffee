$ ->
  $('#folder-adv-history-select').change ->
    index = parseInt($(this).val()[0].split('.')[0]) - 1
    $('#folder-adv-history-view').text folder_history_array[index]

    # Used in inc_task_table_list.html
    $('.folder-checkbox').click ->
      id = $(this).data 'id'
      
      $.post(
        '/folder/select/task#{id}/'
        {checked: $(this).prop 'checked'}
      )
