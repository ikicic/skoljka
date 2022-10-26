(function() {
  // Tag list, put vote count next ot the tag.
  var refresh_tag_votes = function(tag) {
    // tag-vote-count MUST be next to the tag. (?)
    var votes = parseInt(tag.attr('data-votes'));
    var span = tag.next('.tag-votes');
    if (span.length) {
      span.html(votes || "");
    } else if (votes) {
      tag.after('<sup class="tag-votes">' + votes + '</sup>');
    }
  };

  var new_tag_link = function(tag) {
    return '<a href="/search/?q=' + tag + '" data-votes="0">' + tag + '</a>';
  };

  $(function() {
    if (!is_authenticated || !$('.tag-list-tooltip').length)
      return;

    var VOTE_WRONG = -1;

    $('.tag-list-tooltip a').each(function(index) {
      refresh_tag_votes($(this));
    });
    $('body').append(
        '<div id="tag-tooltip" class="tag-tooltip">\n' +
          '<a id="tt-plus" href="#" title="Valjan">' +
            '<img src="/static/images/plus_circle.png">' +
          '</a>\n' +
          '<a id="tt-minus" href="#" title="Nevaljan">' +
            '<img src="/static/images/minus_circle.png">' +
          '</a>\n' +
          '<a id="tt-delete-vote" href="#" title="Izbriši moju ocjenu">' +
            '<img src="/static/images/cross.png">' +
          '</a>\n' +
          '<span id="tt-info"></span><br>\n' +
        '</div>'
    );

    var tt_info = $('#tt-info');
    var tooltip_options = {
      tip: '#tag-tooltip',
      position: 'bottom center',
      onBeforeShow: function() {
        var tag = this.getTrigger();
        tt_info.html("");
        tt_info.data('tag', tag);
        tt_info.data('tooltip', this);
      }
    };

    var vote_func = function(event, value) {
      event.preventDefault();
      var tag = tt_info.data('tag');
      tt_info.html("...");
      $.post('/ajax/tag/vote/', {
        value: value,
        tag: tag.html(),
        task: tag.parent().attr('data-object-id')
      }, function(vote_count) {
        tag.attr('data-votes', vote_count);
        tt_info.html("");
        tag.toggleClass('tag-wrong', parseInt(vote_count) <= VOTE_WRONG);
        refresh_tag_votes(tag);
      }).fail(function() {
        tt_info.html("Greška!");
      });
    };

    $('#tt-plus').click(function(event) { vote_func(event, 1); });
    $('#tt-minus').click(function(event) { vote_func(event, -1); });
    $('#tt-delete-vote').click(function(event) { vote_func(event, 0); });

    $('.tag-list-tooltip a').tooltip(tooltip_options);
  });
}).call(this);
