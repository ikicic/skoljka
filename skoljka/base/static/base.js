$(function() {
  console.log("DOM loaded - jquery (base.js)");
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
  'theme-classic': {
    name: 'Školjka Classic',
    author: 'Ivica Kičić',
    properties: {
      '--theme-paintbrush-icon-color': '#323232',
      '--header-background': '-webkit-gradient(linear, left top, left bottom, from(#dfe8eb), to(#d6e2e5))',
      '--skoljka-logo-text-color': '#000000',
      '--skoljka-logo-text-color-hover': '#000000',
      '--body-bg': '#feffff',
      '--header-box-shadow': '0 1px 4px #666',
      '--outset-bg': '#fafcfc',
      '--outset-box-shadow': '0 2px 4px rgba(128, 128, 128, 0.55)',
      '--outdiv-bg': '-webkit-gradient(linear, left top, left bottom, from(#f6f8fa), to(#edf2f8))',
      '--outdiv-box-shadow': '0 1px 2px rgba(128, 128, 128, 0.35)',
      '--content-bg-color': '#f6faf9',
      '--sidebar-bg-color': '#f0f5f4',
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
  'theme-dark': {
    name: 'Školjka Dark',
    author: 'Dario Vuksan',
    properties: {
      '--theme-paintbrush-icon-color': '#f2f2f2',
      '--header-background': '#1b1d1e',
      '--skoljka-logo-text-color': '#ffffff',
      '--skoljka-logo-text-color-hover': '#ffffff',
      '--body-bg': '#2a2c2f',
      '--header-box-shadow': '0 1px 4px #252e3a',
      '--outset-bg': '#40444c',
      '--outset-box-shadow': '0 2px 4px rgb(64, 64, 100)',
      '--outdiv-bg': '#363a40',
      '--outdiv-box-shadow': '0 1px 2px rgb(64, 64, 100)',
      '--content-bg-color': '#1f1f1f',
      '--sidebar-bg-color': '#1f1f1f',
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

document.addEventListener('DOMContentLoaded', function() {
  console.log("DOM loaded - vanilla (base.js)");
  var b = document.querySelector('#hbar-theme');
  var dropdown = document.querySelector('#theme-picker');
  b.addEventListener('click', function () {
    b.setAttribute('opened', '' + b.getAttribute('opened') !== 'true');
  });
});