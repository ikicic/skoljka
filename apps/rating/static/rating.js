(function() {
  window.jquery_rating_submit = function(name, url, read_only) {
    return $(function() {
      return $('.' + name + '-star').rating({
        readOnly: read_only,
        callback: function(value, link) {
          var data;
          data = {};
          data[name] = value || 0;
          return $.post(url, data, function(x) {
            return $('#' + name + '-value').html(x);
          });
        }
      });
    });
  };
}).call(this);
