$ ->
  # Show / hide task text
  $('#solution-toggle-task').click (event) ->
    event.preventDefault()
    div = $ '#solution-task'
    $(this).html  \
        if div.is(':visible') then '(Prikaži tekst zadatka)' \
                              else '(Sakrij tekst zadatka)'
    div.toggle()

  # Toggle votes
  $('#solution-ratings-toggle').click (event) ->
    event.preventDefault()
    $('#solution-ratings').toggle()

  # 'Not solved' warning. Click to show solution text.
  $('#solution-unhide-box').click (event) ->
    $('#solution-unhide-box').attr 'style', 'display: none;'
    $('#solution-inner-container').attr 'style', 'visibility: visible;'

