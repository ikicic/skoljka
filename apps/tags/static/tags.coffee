# Tag list, put vote count next to the tag
refresh_tag_votes = (tag) ->
  # tag-vote-count MUST be next to the tag
  votes = parseInt tag.attr 'data-votes'
  span = tag.next '.tag-votes'
  if span.length
    span.html votes or ""
  else if votes
    tag.after '<sup class="tag-votes">' + votes + '</sup>'

new_tag_link = (tag) ->
  '<a href="/search/?q=' + tag + '" data-votes="0">' + tag + '</a>'

$ ->
  return if not is_authenticated
  return if not $('.tag-list').length

  VOTE_WRONG = -1

  $('.tag-list a').each (index) ->
    refresh_tag_votes $(@)

  $('body').append '''
    <div id="tag-tooltip" class="tag-tooltip">
      <a id="tt-plus" href="#" title="Valjan"><img src="/static/images/plus_circle.png"></a>
      <a id="tt-minus" href="#" title="Nevaljan"><img src="/static/images/minus_circle.png"></a>
      <a id="tt-delete-vote" href="#" title="Izbriši moju ocjenu"><img src="/static/images/cross.png"></a>
      <a id="tt-delete" href="#" title="Izbriši"><img src="/static/images/recycle_bin_full.png"></a>
      <span id="tt-info"></span><br>
      <input type="text" id="tt-add" name="tt_add" placeholder="Dodaj oznaku" class="input-small">
    </div>'''

  tt_info = $ '#tt-info'
  tooltip_options = {
    tip: '#tag-tooltip'
    position: 'bottom center'
    onBeforeShow: ->
      tag = @getTrigger()
      tt_info.html ""
      tt_info.data 'tag', tag
      tt_info.data 'tooltip', @
  }


  $('#tt-add').keypress (event) ->
    name = $(@).val()
    if event.which != 13 or name.length == 0
      return

    $(@).val ""
    tt_info.html "Slanje..."
    container = tt_info.data('tag').parent()
    $.post(
      '/ajax/tag/add/'
      content_type_id: container.attr 'data-content-type-id'
      object_id: container.attr 'data-object-id'
      name: name
      (data) ->
        if data == '1'
          tt_info.html "Spremljeno"
          target = tt_info.data('tag').parent()
          $(new_tag_link(name)).appendTo(target).tooltip tooltip_options
        else if data == '0'
          tt_info.html "Nemate ovlasti!"
        else if data == '00'
          tt_info.html "Nedozvoljena oznaka."
        else
          tt_info.html "Greška!"
    ).fail ->
      tt_info.html "Greška!"


  $('#tt-delete').click (event) ->
    event.preventDefault()

    tag = tt_info.data 'tag'
    tt_info.html "..."
    $.post(
      '/ajax/tag/delete/'
      name: tag.html()
      content_type_id: tag.parent().attr 'data-content-type-id'
      object_id: tag.parent().attr 'data-object-id'
      (data) ->
        if data == '1'
          tt_info.data('tooltip').hide()
          tag.remove()
        else
          tt_info.html if data == '0' then "Nemate ovlasti!" else "Greška!"
    ).fail ->
      tt_info.html "Greška!"

  vote_func = (event, value) ->
    event.preventDefault()

    tag = tt_info.data 'tag'
    tt_info.html "..."
    $.post(
      '/ajax/tag/vote/'
      value: value
      tag: tag.html()
      task: tag.parent().attr 'data-task'
      (vote_count) ->
        # TODO: color is not updated, maybe generate whole tag list using javascript
        tag.attr 'data-votes', vote_count
        tt_info.html ""

        tag.toggleClass 'tag-wrong', parseInt(vote_count) <= VOTE_WRONG
        refresh_tag_votes tag
    ).fail ->
      tt_info.html "Greška!"

  $('#tt-plus').click (event) -> vote_func event, 1
  $('#tt-minus').click (event) -> vote_func event, -1
  $('#tt-delete-vote').click (event) -> vote_func event, 0

  $('.tag-list a').tooltip tooltip_options
