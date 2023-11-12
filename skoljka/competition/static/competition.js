(function() {
  window.reg_add_member_field = function() {
    // Pass all arguments to _reg_member_field_row and append the result.
    $('#creg-table-category').before(_reg_member_field_row.apply(null, arguments));
  };

  var _reg_member_field_row = function(index, manual, username, accepted) {
    var extra = accepted ?
      'class="input-large creg-invitation-accepted" title="' + gettext("Accepted") + '"' :
      'class="input-large"';
    var cancel_or_delete = accepted ? gettext("Delete") : gettext("Cancel");
    var output = "<div>" + gettext("Member") + " #" + index + ":</div>";

    if (username) {
      output +=
        '<div>' +
        '<input type="hidden" value="' + username + '"' +
        ' id="member' + index + '_username"' +
        ' name="member' + index + '_username">\n' +
        '<input type="text" value="' + manual + '" disabled="disabled"' +
        ' id="member' + index + '_manual" ' + extra +
        ' name="member' + index + '_manual">' +
        '</div>\n' +
        '<div>' +
        '<button type="button" class="btn creg-cancel-invitation">' +
        cancel_or_delete +
        '</button>' +
        '</div>';
    } else {
      output +=
        '<div>' +
        '<input type="hidden" value="" id="member' + index + '_username"' +
        ' name="member' + index + '_username">\n' +
        '<input type="text" value="' + manual + '" ' + extra +
        ' id="member' + index + '_manual" ' +
        ' name="member' + index + '_manual">' +
        '</div>\n' +
        '<div>' +
        gettext('or') + ' ' +
        '<button type="button" class="btn creg-invite">' +
        gettext("Invite user") +
        '</button>' +
        '</div>';
    }
    return '<div class="creg-table-row" data-index="' + index + '">' +
      output +
      '</div>';
  };

  window.reg_add_listeners = function() {
    $('#creg-form').on('click', '.creg-cancel-invitation', function() {
      var row = $(this).closest('.creg-table-row');
      row.replaceWith(
        _reg_member_field_row(row.attr('data-index'), '', '', false));
    });

    $('#creg-form').on('click', '.creg-invite', function() {
      var row = $(this).closest('.creg-table-row');
      var index = row.attr('data-index');
      var manual_field = $("#member" + index + "_manual");
      manual_field.val("");
      manual_field.prop('disabled', true);
      manual_field.prop('class', 'input-large');
      // FIXME: There are two inputs with the same name, a hidden field and a new one.
      //        Either fix it or document how it works, because it is not clear it is
      //        fully bug-free.
      $(this).replaceWith(
        '<input type="text" class="creg-invite-member input-large"' +
        ' name="member' + index + '_username"' +
        ' placeholder="' + gettext("Enter username") + '">\n' +
        '<button type="button" class="btn creg-cancel-invitation">' +
        gettext("Cancel") +
        '</button>'
      );
      // FIXME: Stop previous autocomplete, because they keep accumulating.
      //        Also investigate whether we need 2 autocompletes for 2 extra members.
      // FIXME: Delete should add the user to reg_available_users, since it
      //        excludes existing members.
      $('.creg-invite-member').autocomplete(reg_available_users);
    });
  };

  $(function() {
    $('#comp-post-target').change(function() {
      var value = $(this).val();
      $('#post-content-type-id').val(value ? team_ct : competition_ct);
      $('#post-object-id').val(value ? value : competition_id);
      set_reply('');
    });

    $('.post-reply').click(function() {
      var team_id = $(this).attr('data-team-id');
      $('#post-content-type-id').val(team_ct);
      $('#post-object-id').val(team_id);
      $('#comp-post-target').val(team_id);
    });

    var STATUS_CLASS = {
      'S': 'bar ctask-solved',
      'F': 'bar ctask-failed',
      'T': 'bar ctask-tried'
    };

    $('.ctask-solution-help i').click(function(event) {
      event.preventDefault();
      var a = $(this);
      var span = a.next('span');
      span.html((span.html() ? "" : a.attr('title')));
    });

    $('#ctask-admin-panel select').change(function() {
      var team_type = $('#id_filter_by_team_type').val();
      var status = $('#id_filter_by_status').val();
      var prefix = team_type + status;
      var stats = {};
      for (var key in ctask_statistics) {
        var value = ctask_statistics[key];
        if (key.substr(0, 2) === prefix)
          stats[key.substr(2)] = value;
      }
      show_ctask_statistics(stats, STATUS_CLASS[status], 'ctask-locked');
    });

    $('#comp-tasks a').click(function(event) {
      event.stopImmediatePropagation();
    });

    // table#comp-tasks tr.comp-chain-unfinished
    $('.comp-chain-unfinished').click(function(event) {
      var id = $(this).attr('data-next');
      var current_url =
        location.protocol + '//' + location.host + location.pathname;
      window.location = current_url + id + '/';
    });
  });

  $(function() {
    // Chain screation selection.
    var selection = [];
    var trs = {};
    var _set_html = function(ctask_id, html) {
      trs[ctask_id].find('.cchain-list-ctask-selected').html(html);
    };

    $('#cchain-unused-ctasks-table a').click(function(event) {
      event.stopImmediatePropagation();
    });

    $('#cchain-unused-ctasks-table tr').click(function(event) {
      var me = $(this);
      var id = me.attr('data-id');
      if (!id)
        return;
      var pos = null;
      for (var index = _i = 0, _len = selection.length; _i < _len; index = ++_i) {
        var ctask_id = selection[index];
        if (ctask_id === id) {
          pos = index;
          _set_html(id, '');
        } else if (pos !== null) {
          _set_html(ctask_id, '#' + index);
        }
      }
      if (pos === null) {
        selection.push(id);
        trs[id] = me;
        _set_html(id, '#' + selection.length);
      } else {
        selection.splice(pos, 1);
      }
      $('#used-tasks-table').toggleClass('add-ctasks-here',
        selection.length > 0);
      $('#cchain-unused-ctasks-ids').val(selection.join(','));
    });

    $('#used-tasks-table a').click(function(event) {
      event.stopImmediatePropagation();
    });

    $('#used-tasks-table tr').click(function(event) {
      if (selection.length === 0)
        return;
      var me = $(this);
      var id = me.attr('data-id');
      var ctask_ids = selection.join(',');
      var form = me.closest('form');
      var what = me.hasClass('cchain-list') ? 'chain' : 'ctask';
      form.append(
        '<input type="hidden" name="action" value="add-after">' +
        '<input type="hidden" name="ctask-ids" value="' + ctask_ids + '">' +
        '<input type="hidden" name="after-what" value="' + what + '">' +
        '<input type="hidden" name="after-id" value="' + id + '">'
      );
      form.submit();
    });

    /* Show/hide sample solution button. */
    $('#ctask-show-sample-solution').click(function(event) {
      // Show-text is first stored as .html(), and hide-text as
      // data-toggle-text. After each click, these are swapped.
      var me = $(this);
      var new_text = me.attr('data-toggle-text');
      me.attr('data-toggle-text', me.html());
      me.html(new_text);
      var div = $('#ctask-sample-solution');
      div.css('display',
        div.css('display') == 'inline-block' ? 'none' : 'inline-block');
    });
  });

  window.show_ctask_statistics = function(stats, status_class, empty_class) {
    $('.ctask').each(function() {
      var _this = $(this);
      var count = stats[_this.attr('data-id')];
      _this.attr('class', 'ctask ' + (count ? status_class : empty_class));
      _this.html(count || '');
    });
  };

  // Option for admins to show all translations.
  $(function() {
    var enabled = localStorage.getItem('all-langs');
    var body = $('body');
    if (enabled === '0' || !window.is_admin) {
      if (body.hasClass('all-langs')) {
        body.removeClass('all-langs');
      }
      $('#all-langs').prop('checked', false);
    } else {
      body.addClass('all-langs'); // Default.
    }

    $('#all-langs').click(function() {
      localStorage.setItem('all-langs', this.checked ? '1' : '0');
      $('body').toggleClass('all-langs');
    });
  });

  /* Make the whole chain access row a label for the checkbox. */
  $(function() {
    $('#chain-access-table').on('click', '.chain-access-tr', function() {
      const checkbox = $(this).find('[type=checkbox]');
      checkbox.prop('checked', !checkbox.prop('checked'));
    });
  });
}).call(this);
