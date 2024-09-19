$(function() {
  $('.collapse-button').each(function() {
    // Add toggle icon.
    var target_id = $(this).attr('data-target');
    $(this).html(
      $('#' + target_id).is(':hidden')
          ? '<i class="icon-chevron-down"></i>'
          : '<i class="icon-chevron-up"></i>'
    );
  });

  $('.collapse-button').click(function(event) {
    event.preventDefault();
    var target_id = $(this).attr('data-target');
    var icon = $(this).children('i');
    if (icon.attr('class') === 'icon-chevron-up')
      icon.attr('class', 'icon-chevron-down');
    else
      icon.attr('class', 'icon-chevron-up');
    $('#' + target_id).toggle();
  });

  $('.auto-toggler').click(function(event) {
    event.preventDefault();
    var target_id = $(this).attr('data-target');
    $('#' + target_id).toggle();
  });

  $('#history-select').change(function() {
    var index = parseInt($(this).val());
    $('#history-view').text(history_array[index]);
  });
});

var THEMES = {
  'skoljka-classic': {
    name: 'Školjka Classic',
    identifier: 'skoljka-classic',
    author: 'Ivica Kičić',
    href: 'https://github.com/ikicic/',
    div: null,
    properties: {
      '--theme-paintbrush-icon-color': '#323232',
      '--header-background': '-webkit-gradient(linear, left top, left bottom, from(#dfe8eb), to(#d6e2e5))',
      '--skoljka-logo-text-color': '#000000',
      '--skoljka-logo-text-color-hover': '#000000',
      '--skoljka-logo-text-shadow': '1px 1px 1px #b6b6b6',
      '--body-bg': '#feffff',
      '--header-box-shadow': '0 1px 4px #666',
      '--outset-bg': '#fafcfc',
      '--outset-box-shadow': '0 2px 4px rgba(128, 128, 128, 0.55)',
      '--outset-border': 'none',
      '--outdiv-bg': '-webkit-gradient(linear, left top, left bottom, from(#f6f8fa), to(#edf2f8))',
      '--outdiv-box-shadow': '0 1px 2px rgba(128, 128, 128, 0.35)',
      '--div-border': 'none',
      '--content-bg-color': '#f6faf9',
      '--sidebar-bg-color': '#f0f5f4',
      '--content-border': 'none',
      '--sidebar-border': 'none',
      '--content-box-shadow': '0 1px 4px #666',
      '--sidebar-box-shadow': '0 1px 4px #666',
      '--text-color': '#333',
      '--activity-day-text-color': '#666',
      '--homepage-info-text-color': '#444',
      '--comp-category-text-color': '#555',
      '--post-info-text-color': '#888',
      '--caction-info-text-color': 'gray',
      '--task-file-info-text-color': 'gray',
      '--comp-my-team-td-bg-color': '#dff0d8',
      '--nav-anchor-bg-color-hover': '#eee',
      '--blue-anchor-color': '#0088cc',
      '--blue-anchor-color-hover': '#005580',
      '--red-anchor-color-hover': 'red',
      '--profile-task-submitted-anchor': '#13F',
      '--striped-table-header-bg-color': '#f4f7f6',
      '--striped-table-odd-row-bg-color': '#f4f7f6',
      '--icon-filter': 'none',
      '--image-filter': 'none',
      '--solution-unhide-box-bg-color': '#FEFEFE',
      '--solution-unhide-box-bg-color-hover': '#F4F4F4',
      '--mathcontent-background': '#fff',
      '--mathcontent-text-color': '#555',
      '--mathcontent-border': '1px solid #ccc',
      '--textarea-background': '#FAFAFA',
      '--textarea-text-color': '#753A88',
      '--textarea-border': '1px solid #ccc',
      '--textarea-box-shadow': 'inset 0 1px 1px rgba(0, 0, 0, 0.075), 0 0 8px rgba(82, 168, 236, 0.6);',
      '--mc-quote-background': '#FAFAFA',
      '--mc-quote-border-left': '1px solid #95C5F8',
      '--mc-quote-text-color': '#753A88',
      '--bootstrap-btn-text-shadow': '0 1px 1px rgba(255, 255, 255, 0.75)',
      '--bootstrap-btn-background': '-webkit-linear-gradient(top, #fff, #e6e6e6) repeat-x',
      '--bootstrap-btn-text-color': '#333',
      '--input-bg-color': '#ffffff',
      '--input-text-color': '#555',
      '--input-border': '1px solid #ccc',
      '--alert-bg-color': '#fcf8e3',
      '--alert-text-shadow': '0 1px 0 rgba(255, 255, 255, 0.5)',
      '--alert-border': '1px solid #fbeed5',
      '--alert-text-color': '#c09853',
      '--tag-tooltip-bg': 'rgb(239, 241, 228)',
      '--tag-tooltip-border': '1px solid #CCC',
      '--tag-tooltip-box-shadow': '1px 1px 3px #c9c9c9',
      '--pagination-anchor-border': '1px solid #ddd',
      '--pagination-anchor-bg-color-hover': '#f5f5f5',
      '--comp-chain-unfinished-hover': 'mix(blue, #f0f5f4, 5%)',
      '--outset-code-bg-color': '#f7f7f9',
      '--outset-code-border': '1px solid #e1e1e8',
      '--profile-distribution-column-outline': 'none',
      '--profile-distribution-column-bg-color': '#EEE',
      '--profile-distribution-column-fg-color': '#CCC'
    }
  },
  'skoljka-dark': {
    name: 'Školjka Dark',
    identifier: 'skoljka-dark',
    author: 'Dario Vuksan',
    href: 'https://github.com/IamMusavaRibica/',
    div: null,
    properties: {
      '--theme-paintbrush-icon-color': '#f2f2f2',
      '--header-background': '#1b1d1e',
      '--skoljka-logo-text-color': '#ffffff',
      '--skoljka-logo-text-color-hover': '#ffffff',
      '--skoljka-logo-text-shadow': '1px 1px 1px #b6b6b6',
      '--body-bg': '#2a2c2f',
      '--header-box-shadow': '0 1px 4px #252e3a',
      '--outset-bg': '#40444c',
      '--outset-box-shadow': '0 2px 4px rgb(64, 64, 100)',
      '--outset-border': 'none',
      '--outdiv-bg': '#363a40',
      '--outdiv-box-shadow': '0 1px 2px rgb(64, 64, 100)',
      '--outdiv-border': 'none',
      '--content-bg-color': '#1f1f1f',
      '--sidebar-bg-color': '#1f1f1f',
      '--content-border': 'none',
      '--sidebar-border': 'none',
      '--content-box-shadow': '0 1px 4px #303d4e',
      '--sidebar-box-shadow': '0 1px 4px #303d4e',
      '--text-color': '#e6e6e6',
      '--activity-day-text-color': '#dddddd',
      '--homepage-info-text-color': '#dcdcdc',
      '--comp-category-text-color': '#dcdcdc',
      '--post-info-text-color': '#dedede',
      '--caction-info-text-color': '#dedede',
      '--task-file-info-text-color': '#dedede',
      '--comp-my-team-td-bg-color': '#314f25',
      '--nav-anchor-bg-color-hover': '#2b2f36',
      '--blue-anchor-color': '#2da3e5',
      '--blue-anchor-color-hover': '#3dbeff',
      '--red-anchor-color-hover': '#ff0000',
      '--profile-task-submitted-anchor': '#116cff',
      '--striped-table-header-bg-color': '#47474f',
      '--striped-table-odd-row-bg-color': '#2b2c2d',
      '--icon-filter': 'invert(180) contrast(150%)',
      '--image-filter': 'invert(180) contrast(150%)',
      '--solution-unhide-box-bg-color': 'inherit',
      '--solution-unhide-box-bg-color-hover': 'rgba(82, 86, 100, 0.45)',
      '--mathcontent-background': '#171717',
      '--mathcontent-text-color': '#eeeeee',
      '--mathcontent-border': 'none',
      '--textarea-background': '#171717',
      '--textarea-text-color': '#eeeeee',
      '--textarea-border': 'none',
      '--textarea-box-shadow': 'inset 0 1px 1px rgba(0, 0, 0, 0.075), 0 0 8px rgba(231, 231, 231, 0.6)',
      '--mc-quote-background': '#363b46',
      '--mc-quote-border-left': '1px solid #419dff',
      '--mc-quote-text-color': '#b5b5b5',
      '--bootstrap-btn-text-shadow': 'none',
      '--bootstrap-btn-background': '#3d3d3d',
      '--bootstrap-btn-text-color': '#eeeeee',
      '--input-bg-color': '#171717',
      '--input-text-color': '#eeeeee',
      '--input-border': '1px solid #444',
      '--alert-bg-color': '#36342a',
      '--alert-text-shadow': 'none',
      '--alert-border': '1px solid #b67800',
      '--alert-text-color': '#f6ead4',
      '--tag-tooltip-bg': '#171717',
      '--tag-tooltip-border': '1px solid #000',
      '--tag-tooltip-box-shadow': '1px 1px 3px #0c5b92',
      '--pagination-anchor-border': '1px solid #444',
      '--pagination-anchor-bg-color-hover': '#2f2f2f',
      '--comp-chain-unfinished-hover': '#2d2d36',
      '--outset-code-bg-color': '#31343c',
      '--outset-code-border': '1px solid #0e0e0e',
      '--profile-distribution-column-outline': '1px solid #2f2f2f',
      '--profile-distribution-column-bg-color': '#4f4f4f',
      '--profile-distribution-column-fg-color': '#363636'
    }
  }
};


// Thanks, Babel!

/*
function applyTheme(theme) {
  if (typeof theme === 'string') {
    theme = THEMES[theme];
  }
  if (theme.div === null) {
    return;
  }
  window.localStorage.setItem('skoljka-theme', theme.identifier);
  for (let t of Object.values(THEMES)) {
    t.div?.classList.remove('selected-theme');
  }
  theme.div.classList.add('selected-theme');
  for (const [property, value] of Object.entries(theme.properties)) {
      document.documentElement.style.setProperty(property, value);
  }
}

document.addEventListener('DOMContentLoaded', function() {
  // console.log("DOM loaded - vanilla (base.js)");
  var b = document.querySelector('#hbar-theme');
  var dropdown = document.querySelector('#theme-picker');
  b.addEventListener('click', function () {
    b.setAttribute('opened', '' + b.getAttribute('opened') !== 'true');
  });
  // generated stylesheet for styling individual themes in the picker
  var tpcss = document.createElement('style');

  for ([themeClassName, theme] of Object.entries(THEMES)) {
    var a1 = 'x-' + themeClassName + '-anchor';
    tpcss.innerText += `
    .${a1} {
        color: ${theme.properties['--blue-anchor-color']};
    }
    .${a1}:hover {
        color: ${theme.properties['--blue-anchor-color-hover']};
    }
    `;
    var themeDiv = document.createElement('div');
    themeDiv.classList.add('listed-theme', themeClassName);
    themeDiv.innerHTML = `
      <span>${theme.name}</span>
      <div>
        Autor: <a class="${a1}" href=${theme.href} target="_blank">${theme.author}</a>
      </div>
    `;
    themeDiv.theme = theme;
    themeDiv.addEventListener('click', function () {
      applyTheme(this.theme);
    });
    themeDiv.style.setProperty('background', theme.properties['--body-bg']);
    themeDiv.style.setProperty('color', theme.properties['--text-color']);
    theme.div = themeDiv;
    dropdown.appendChild(themeDiv);
  }
  document.head.appendChild(tpcss);

  var selectedTheme = window.localStorage.getItem('skoljka-theme') || 'skoljka-classic';
  applyTheme(THEMES[selectedTheme]);
});
*/

function _slicedToArray(r, e) { return _arrayWithHoles(r) || _iterableToArrayLimit(r, e) || _unsupportedIterableToArray(r, e) || _nonIterableRest(); }
function _nonIterableRest() { throw new TypeError("Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method."); }
function _unsupportedIterableToArray(r, a) { if (r) { if ("string" == typeof r) return _arrayLikeToArray(r, a); var t = {}.toString.call(r).slice(8, -1); return "Object" === t && r.constructor && (t = r.constructor.name), "Map" === t || "Set" === t ? Array.from(r) : "Arguments" === t || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(t) ? _arrayLikeToArray(r, a) : void 0; } }
function _arrayLikeToArray(r, a) { (null == a || a > r.length) && (a = r.length); for (var e = 0, n = Array(a); e < a; e++) n[e] = r[e]; return n; }
function _iterableToArrayLimit(r, l) { var t = null == r ? null : "undefined" != typeof Symbol && r[Symbol.iterator] || r["@@iterator"]; if (null != t) { var e, n, i, u, a = [], f = !0, o = !1; try { if (i = (t = t.call(r)).next, 0 === l) { if (Object(t) !== t) return; f = !1; } else for (; !(f = (e = i.call(t)).done) && (a.push(e.value), a.length !== l); f = !0); } catch (r) { o = !0, n = r; } finally { try { if (!f && null != t["return"] && (u = t["return"](), Object(u) !== u)) return; } finally { if (o) throw n; } } return a; } }
function _arrayWithHoles(r) { if (Array.isArray(r)) return r; }
function applyTheme(theme) {
  if (typeof theme === 'string') {
    theme = THEMES[theme];
  }
  if (theme.div === null) {
    return;
  }
  window.localStorage.setItem('skoljka-theme', theme.identifier);
  for (var _i = 0, _Object$values = Object.values(THEMES); _i < _Object$values.length; _i++) {
    var _t$div;
    var t = _Object$values[_i];
    (_t$div = t.div) === null || _t$div === void 0 || _t$div.classList.remove('selected-theme');
  }
  theme.div.classList.add('selected-theme');
  for (var _i2 = 0, _Object$entries = Object.entries(theme.properties); _i2 < _Object$entries.length; _i2++) {
    var _Object$entries$_i = _slicedToArray(_Object$entries[_i2], 2),
        property = _Object$entries$_i[0],
        value = _Object$entries$_i[1];
    document.documentElement.style.setProperty(property, value);
  }
}
document.addEventListener('DOMContentLoaded', function () {
  // console.log("DOM loaded - vanilla (base.js)");
  var b = document.querySelector('#hbar-theme');
  var dropdown = document.querySelector('#theme-picker');
  b.addEventListener('click', function () {
    b.setAttribute('opened', '' + b.getAttribute('opened') !== 'true');
  });
  // generated stylesheet for styling individual themes in the picker
  var tpcss = document.createElement('style');
  for (var _i3 = 0, _Object$entries2 = Object.entries(THEMES); _i3 < _Object$entries2.length; _i3++) {
    var _Object$entries2$_i = _slicedToArray(_Object$entries2[_i3], 2);
    themeClassName = _Object$entries2$_i[0];
    theme = _Object$entries2$_i[1];
    var a1 = 'x-' + themeClassName + '-anchor';
    tpcss.innerText += "\n    .".concat(a1, " {\n        color: ").concat(theme.properties['--blue-anchor-color'], ";\n    }\n    .").concat(a1, ":hover {\n        color: ").concat(theme.properties['--blue-anchor-color-hover'], ";\n    }\n    ");
    var themeDiv = document.createElement('div');
    themeDiv.classList.add('listed-theme', themeClassName);
    themeDiv.innerHTML = "\n      <span>".concat(theme.name, "</span>\n      <div>\n        Autor: <a class=\"").concat(a1, "\" href=").concat(theme.href, " target=\"_blank\">").concat(theme.author, "</a>\n      </div>\n    ");
    themeDiv.theme = theme;
    themeDiv.addEventListener('click', function () {
      applyTheme(this.theme);
    });
    themeDiv.style.setProperty('background', theme.properties['--body-bg']);
    themeDiv.style.setProperty('color', theme.properties['--text-color']);
    theme.div = themeDiv;
    dropdown.appendChild(themeDiv);
  }
  document.head.appendChild(tpcss);
  var selectedTheme = window.localStorage.getItem('skoljka-theme') || 'skoljka-classic';
  // applyTheme(THEMES[selectedTheme]);
});