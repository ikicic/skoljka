window.reg_add_member_field = ->
  $('#creg-table').append(
    _reg_member_field_row arguments...
  )


_reg_member_field_row = (index, username, user_id, accepted) ->
  if accepted
    extra = 'class="span3 creg-invitation-accepted" title="Prihvaćeno"'
  else
    extra = 'class="span3"'
  cancel_or_delete = if accepted then "Izbriši" else "Odustani"

  output = """<div>Član ##{index}:</div>"""
  if user_id
    output += """
      <div>
        <input type="hidden" value="#{user_id}"
          id="member#{index}_user_id" name="member#{index}_user_id">
        <input type="text" value="#{username}" disabled="disabled" #{extra}
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
          id="member#{index}_user_id" name="member#{index}_user_id">
        <input type="text" value="#{username}" #{extra}
          id="member#{index}_manual" name="member#{index}_manual">
      </div>
      <div>
        <button type="button" class="btn creg-invite">Pozovi</button>
      </div>
    """

  """<div class="creg-table-row" data-index="#{index}">#{output}</div>"""


window.reg_add_listeners = ->
  $('#creg-form').on 'click', '.creg-cancel-invitation', ->
    row = $(@).closest '.creg-table-row'
    row.replaceWith _reg_member_field_row row.attr('data-index'), '', '', false

  $('#creg-form').on 'click', '.creg-invite', ->
    options = [
      '<option value="">Odaberite korisnika</option>'
      '<option value="">---------</option>'
    ]
    for key, value of reg_available_users
      options.push """<option value="#{value}">#{key}</option>"""
    options = options.join()

    row = $(@).closest '.creg-table-row'
    index = row.attr 'data-index'
    username_field = $ "#member#{index}_manual"
    username_field.val ""
    username_field.prop 'disabled', true

    $(@).replaceWith """
      <select class="creg-select-member span3">#{options}</select>
      <button type="button" class="btn creg-cancel-invitation">Odustani</button>
    """

  $('#creg-form').on 'change', '.creg-select-member', ->
    row = $(@).closest '.creg-table-row'
    index = row.attr 'data-index'
    selected = $(@).find 'option:selected'

    return unless selected.val()

    row.replaceWith _reg_member_field_row(
      row.attr('data-index'), selected.html(), selected.val(), false
    )

$ ->
  $('#comp-chain-edit').on 'click', '.comp-chain-edit-preview', ->
    row = $(@).closest '.creg-table-row'
    text = $('#' + $(@).attr('data-source')).val()
    target = row.prev().find 'div.outset'
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

