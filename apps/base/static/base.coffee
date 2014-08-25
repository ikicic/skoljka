$ ->
  # ".collapse" reserved by Bootstrap
  $('.collapse-button').each ->
    # Add toggle icon
    $(@).html '<i class="icon-chevron-down"></i>'

  $('.collapse-button').click (event) ->
    event.preventDefault()
    target_id = $(@).attr 'data-target'
    icon = $(@).children 'i'
    if icon.attr('class') == 'icon-chevron-up'
      icon.attr 'class', 'icon-chevron-down'
    else
      icon.attr 'class', 'icon-chevron-up'
    $('#' + target_id).toggle()
