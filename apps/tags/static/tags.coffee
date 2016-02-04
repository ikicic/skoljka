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
  return if not $('.tag-list-tooltip').length

  VOTE_WRONG = -1

  $('.tag-list-tooltip a').each (index) ->
    refresh_tag_votes $(@)

  $('body').append '''
    <div id="tag-tooltip" class="tag-tooltip">
      <a id="tt-plus" href="#" title="Valjan"><img src="/static/images/plus_circle.png"></a>
      <a id="tt-minus" href="#" title="Nevaljan"><img src="/static/images/minus_circle.png"></a>
      <a id="tt-delete-vote" href="#" title="Izbriši moju ocjenu"><img src="/static/images/cross.png"></a>
      <span id="tt-info"></span><br>
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

  vote_func = (event, value) ->
    event.preventDefault()

    tag = tt_info.data 'tag'
    tt_info.html "..."
    $.post(
      '/ajax/tag/vote/'
      value: value
      tag: tag.html()
      task: tag.parent().attr 'data-object-id'
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

  $('.tag-list-tooltip a').tooltip tooltip_options
