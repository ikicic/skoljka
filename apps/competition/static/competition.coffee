window.reg_add_member_field = ->
  $('#creg-table').append(
    _reg_member_field_row arguments...
  )


_reg_member_field_row = (index, manual, username, accepted) ->
  if accepted
    extra = 'class="input-large creg-invitation-accepted" title="Prihvaćeno"'
  else
    extra = 'class="input-large"'
  cancel_or_delete = if accepted then "Izbriši" else "Odustani"

  output = """<div>Član ##{index}:</div>"""
  if username
    output += """
      <div>
        <input type="hidden" value="#{username}"
          id="member#{index}_username" name="member#{index}_username">
        <input type="text" value="#{manual}" disabled="disabled" #{extra}
          id="member#{index}_manual" name="member#{index}_manual">
      </div>
      <div>
        <button type="button" class="btn creg-cancel-invitation">
          #{cancel_or_delete}
        </button>
      </div>
    """
  else
    output += """
      <div>
        <input type="hidden" value=""
          id="member#{index}_username" name="member#{index}_username">
        <input type="text" value="#{manual}" #{extra}
          id="member#{index}_manual" name="member#{index}_manual">
      </div>
      <div>
        ili
        <button type="button" class="btn creg-invite">Pozovi korisnika</button>
      </div>
    """

  """<div class="creg-table-row" data-index="#{index}">#{output}</div>"""


window.reg_add_listeners = ->
  $('#creg-form').on 'click', '.creg-cancel-invitation', ->
    row = $(@).closest '.creg-table-row'
    row.replaceWith _reg_member_field_row row.attr('data-index'), '', '', false

  $('#creg-form').on 'click', '.creg-invite', ->
    row = $(@).closest '.creg-table-row'
    index = row.attr 'data-index'
    manual_field = $("#member#{index}_manual")
    manual_field.val ""
    manual_field.prop 'disabled', true
    manual_field.prop 'class', 'input-large'

    $(@).replaceWith """
      <input type="text" class="creg-invite-member input-large"
        name="member#{index}_username" placeholder="Unesite korisničko ime">
      <button type="button" class="btn creg-cancel-invitation">Odustani</button>
    """
    $('.creg-invite-member').autocomplete(reg_available_users)

$ ->
  $('#comp-post-target').change ->
    # value == 0 stands for competition (global), value != 0 for team
    value = $(@).val()
    $('#post-content-type-id').val if value then team_ct else competition_ct
    $('#post-object-id').val if value then value else competition_id
    set_reply ''

  $('.post-reply').click ->
    team_id = $(@).attr 'data-team-id'
    $('#post-content-type-id').val team_ct
    $('#post-object-id').val team_id
    $('#comp-post-target').val team_id # This won't trigger change event

  STATUS_CLASS = {
    'S': 'bar ctask-solved'
    'F': 'bar ctask-failed'
    'T': 'bar ctask-tried'
  }

  $('.ctask-solution-help i').click (event) ->
    event.preventDefault()
    a = $(@)
    span = a.next 'span'
    span.html (if span.html() then "" else a.attr 'title')

  $('#ctask-admin-panel select').change ->
    team_type = $('#id_filter_by_team_type').val()
    status = $('#id_filter_by_status').val()
    prefix = team_type + status

    stats = {}
    for key, value of ctask_statistics
      if key.substr(0, 2) == prefix
        stats[key.substr(2)] = value
    show_ctask_statistics stats, STATUS_CLASS[status], 'ctask-locked'


$ ->
  # Chain creation selection.
  selection = []
  trs = {}

  _set_html = (ctask_id, html) ->
    trs[ctask_id].find('.cchain-list-ctask-selected').html(html)

  $('#cchain-unused-ctasks-table a').click (event) ->
    event.stopImmediatePropagation()

  $('#cchain-unused-ctasks-table tr').click (event) ->
    me = $(@)
    id = me.attr('data-id')
    return if not id
    pos = null
    for ctask_id, index in selection
      if ctask_id == id
        pos = index
        _set_html(id, '')
      else if pos isnt null
        _set_html(ctask_id, '#' + index)
    if pos is null
      selection.push(id)
      trs[id] = me
      _set_html(id, '#' + selection.length)
    else
      selection.splice(pos, 1)
    $('#used-tasks-table').toggleClass('add-ctasks-here', selection.length > 0)
    $('#cchain-unused-ctasks-ids').val(selection.join(','))

  $('#used-tasks-table a').click (event) ->
    event.stopImmediatePropagation()

  $('#used-tasks-table tr').click (event) ->
    if selection.length == 0
      return
    me = $(@)
    id = me.attr('data-id')
    ctask_ids = selection.join(',')
    form = me.closest('form')
    what = if me.hasClass('cchain-list') then 'chain' else 'ctask'
    form.append(
        '<input type="hidden" name="action" value="add-after">' +
        '<input type="hidden" name="ctask-ids" value="' + ctask_ids + '">' +
        '<input type="hidden" name="after-what" value="' + what + '">' +
        '<input type="hidden" name="after-id" value="' + id + '">'
    )
    console.log form
    form.submit()


window.show_ctask_statistics = (stats, status_class, empty_class) ->
  $('.ctask').each ->
    _this = $(@)
    count = stats[_this.attr('data-id')]
    _this.attr 'class', 'ctask ' + (if count then status_class else empty_class)
    _this.html count or ''
