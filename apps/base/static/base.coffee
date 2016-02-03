$ ->
  # ".collapse" reserved by Bootstrap
  $('.collapse-button').each ->
    # Add toggle icon
    target_id = $(@).attr 'data-target'
    $(@).html(
      if $('#' + target_id).is(':hidden') \
        then '<i class="icon-chevron-down"></i>'
        else '<i class="icon-chevron-up"></i>'
    )

  $('.collapse-button').click (event) ->
    event.preventDefault()
    target_id = $(@).attr 'data-target'
    icon = $(@).children 'i'
    if icon.attr('class') == 'icon-chevron-up'
      icon.attr 'class', 'icon-chevron-down'
    else
      icon.attr 'class', 'icon-chevron-up'
    $('#' + target_id).toggle()

  $('.auto-toggler').click (event) ->
    event.preventDefault()
    target_id = $(@).attr 'data-target'
    $('#' + target_id).toggle()

  $('#history-select').change ->
    index = parseInt $(this).val()
    $('#history-view').text history_array[index]
