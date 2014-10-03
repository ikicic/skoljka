window.reg_add_member_field = ->
  $('#comp-reg-table').append(
    _reg_member_field_tr arguments...
  )


_reg_member_field_tr = (index, username, user_id, accepted) ->
  accepted = if accepted \
    then 'class="comp-reg-invitation-accepted" title="Prihvaćeno"' \
    else ''

  output = """<td>Član ##{index}</td>"""
  if user_id
    output += """
      <td>
        <input type="hidden" value="#{user_id}"
          id="member#{index}_user_id" name="member#{index}_user_id">
        <input type="text" value="#{username}" disabled="disabled" #{accepted}
          id="member#{index}_manual" name="member#{index}_manual">
      </td>
      <td>
        <button type="button" class="btn comp-reg-cancel-invitation">
          Odustani
        </button>
      </td>
    """
  else
    output += """
      <td>
        <input type="hidden" value=""
          id="member#{index}_user_id" name="member#{index}_user_id">
        <input type="text" value="#{username}"
          id="member#{index}_manual" name="member#{index}_manual">
      </td>
      <td>
        <button type="button" class="btn comp-reg-invite">Pozovi</button>
      </td>
    """

  return """<tr data-index="#{index}">#{output}</tr>"""


window.reg_add_listeners = ->
  $('#comp-reg-form').on 'click', '.comp-reg-cancel-invitation', ->
    tr = $(@).closest 'tr'
    tr.replaceWith _reg_member_field_tr tr.attr('data-index'), '', '', false

  $('#comp-reg-form').on 'click', '.comp-reg-invite', ->
    options = [
      '<option value="">Odaberite korisnika</option>'
      '<option value="">---------</option>'
    ]
    for key, value of reg_available_users
      options.push """<option value="#{value}">#{key}</option>"""
    options = options.join()

    tr = $(@).closest 'tr'
    index = tr.attr 'data-index'
    username_field = $ "#member#{index}_manual"
    username_field.val ""
    username_field.prop 'disabled', true

    $(@).replaceWith """
      <select class="comp-reg-select-member">#{options}</select>
    """

  $('#comp-reg-form').on 'change', '.comp-reg-select-member', ->
    tr = $(@).closest 'tr'
    index = tr.attr 'data-index'
    selected = $(@).find 'option:selected'

    return unless selected.val()

    tr.replaceWith _reg_member_field_tr(
      tr.attr('data-index'), selected.html(), selected.val(), false
    )

$ ->
  $('#comp-chain-edit').on 'click', '.comp-chain-edit-preview', ->
    tr = $(@).closest 'tr'
    text = $('#' + $(@).attr('data-source')).val()
    target = tr.prev().find 'div.outset'
    $.get(
      '/ajax/mathcontent/preview/'
      text: text
      (html) ->
        target.html html
    )

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

