'use strict';

module.exports = function(grunt) {
  var BUILD_DEST = 'build/static';
  grunt.initConfig({
    clean: {
      build: [BUILD_DEST]
    },
    copy: {
      'bootstrap-images': {
        files: [
          {
            expand: true,
            cwd: 'bower_components/bootstrap-sass/vendor/assets/',
            dest: BUILD_DEST,
            src: ['images/glyphicons-halflings*.png']
          }
        ]
      },
      jsfiles: {
        files: [
          {
            expand: true,
            cwd: 'apps',
            dest: BUILD_DEST,
            src: ['**/static/**/*.js']
          }
        ]
      },
      libraries: {
        files: [
          {
            expand: true,
            cwd: 'bower_components',
            dest: BUILD_DEST,
            flatten: true,
            src: [
              'jquery-form/jquery.form.js',
              'jquery-star-rating-plugin/jquery.rating.js',
              'jquery-star-rating-plugin/*.gif',
              'jquery.autocomplete/jquery.autocomplete.js',
              'jquery.autocomplete/jquery.autocomplete.css',
              'jquery.autocomplete/indicator.gif', 'jquery.metadata/jquery.metadata.js',
              'jquery/jquery.min.js',
            ]
          }
        ]
      }
    },
    sass: {
      all: {
        options: {
          'includePaths': [
            './bower_components/bootstrap-sass/vendor/assets/stylesheets',
          ].concat(grunt.file.expand('./apps/**/static/'))
        },
        files: [
          {
            expand: true,
            cwd: 'apps',
            flatten: true,
            src: ['**/*.scss'],
            dest: BUILD_DEST,
            rename: function(dist, src) {
              return dist + '/' + src.replace(/\.scss$/, '.css');
            }
          }
        ]
      }
    },
    watch: {
      sass: {
        files: ['apps/**/*.scss'],
        tasks: ['sass']
      },
      jsfiles: {
        files: ['apps/**/static/**/*.js'],
        tasks: ['copy:jsfiles']
      }
    }
  });
  grunt.loadNpmTasks('grunt-contrib-clean');
  grunt.loadNpmTasks('grunt-contrib-copy');
  grunt.loadNpmTasks('grunt-contrib-watch');
  grunt.loadNpmTasks('grunt-sass');
  grunt.registerTask('build', ['clean', 'copy', 'sass']);
  grunt.registerTask('default', ['build']);
  return grunt.registerTask('dev', ['build', 'watch']);
};
