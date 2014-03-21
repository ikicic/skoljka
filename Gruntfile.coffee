'use strict'

module.exports = (grunt) ->
  BUILD_DEST = 'build/static'
  grunt.initConfig
    clean:
      build: [BUILD_DEST]

    coffee:
      all:
        files: [
          expand: true
          cwd: 'apps'
          src: ['**/*.coffee']
          dest: BUILD_DEST
          rename: (dest, src) -> dest + '/' + src.replace(/\.coffee$/, '.js')
        ]

    copy:
      'bootstrap-images':
        files: [
          expand: true
          cwd: 'bower_components/bootstrap-sass/vendor/assets/'
          dest: BUILD_DEST
          src: [
            'images/glyphicons-halflings*.png'
          ]
        ]
      jsfiles:
        files: [
          expand: true
          cwd: 'apps'
          dest: BUILD_DEST
          src: [
            '**/static/**/*.js'
          ]
        ]
      libraries:
        files: [
          expand: true
          cwd: 'bower_components'
          dest: BUILD_DEST
          flatten: yes
          src: [
            'jquery-form/jquery.form.js'
            'jquery-star-rating-plugin/jquery.rating.js'
            'jquery-star-rating-plugin/*.gif'
            'jquery.autocomplete/jquery.autocomplete.min.js'
            'jquery.metadata/jquery.metadata.js'
            'jquery/jquery.min.js'
          ]
        ]

    sass:
      all:
        options: {
          # Include Bootstrap and static/ folders for all apps.
          'includePaths': [
            './bower_components/bootstrap-sass/vendor/assets/stylesheets'
          ].concat grunt.file.expand './apps/**/static/'
        }
        files: [
          expand: true
          cwd: 'apps'
          flatten: true
          src: ['**/*.scss']
          dest: BUILD_DEST
          rename: (dist, src) -> dist + '/' + src.replace(/\.scss$/, '.css')
        ]

    watch:
      coffee:
        files: ['apps/**/*.coffee']
        tasks: ['coffee']
      sass:
        files: ['apps/**/*.scss']
        tasks: ['sass']

  grunt.loadNpmTasks 'grunt-contrib-clean'
  grunt.loadNpmTasks 'grunt-contrib-coffee'
  grunt.loadNpmTasks 'grunt-contrib-copy'
  grunt.loadNpmTasks 'grunt-contrib-watch'
  grunt.loadNpmTasks 'grunt-sass'

  grunt.registerTask 'build', ['clean', 'coffee', 'copy', 'sass']
  grunt.registerTask 'default', ['build']
  grunt.registerTask 'dev', ['build', 'watch']
