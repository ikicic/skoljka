# jQuery Rating Submit Function
window.jquery_rating_submit = (name, url, read_only) ->
  $ ->
    $('.' + name + '-star').rating
      readOnly: read_only
      callback: (value, link) ->
        data = {}
        data[name] = value or 0
        $.post url, data, (x) ->
          $('#' + name + '-value').html x
