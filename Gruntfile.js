'use strict';

module.exports = function (grunt) {
    // Load tasks from grunt-* dependencies in package.json
    require('load-grunt-tasks')(grunt);

    // Time how long tasks take
    require('time-grunt')(grunt);

    // Project configuration
    grunt.initConfig({
        exec: {
            emscripten: {
                cmd: function (arch) {
                    if (typeof arch === 'undefined') {
                        return 'python3 build.py build'
                    } else {
                        return 'python3 build.py build ' + arch;
                    }
                }
            }
        },
        concat: {
            dist: {
                src: [
                    'src/libunicorn<%= lib.suffix %>.out.js',
                    'src/libelf-integers.js',
                    'src/unicorn-wrapper.js',
                    'src/unicorn-constants.js',
                ],
                dest: 'dist/unicorn<%= lib.suffix %>.min.js'
            }
        },
        connect: {
            options: {
                port: 9001,
                livereload: 35729,
                hostname: 'localhost'
            },
            livereload: {
                options: {
                    open: true
                }
            }
        },
        copy: {
            main: {
                src: 'src/libunicorn<%= lib.suffix %>.out.wasm',
                dest: 'dist/libunicorn<%= lib.suffix %>.out.wasm'
            }
        },
        watch: {
            livereload: {
                files: [
                    '*.html',
                    '*.css',
                    '*.js',
                    'demos/*.html',
                    'demos/*.css',
                    'demos/*.js',
                    'dist/*.js',
                ],
                options: {
                    livereload: '<%= connect.options.livereload %>'
                }
            },
        }
    });

    // Project tasks
    grunt.registerTask('copyWasmIfExists', function () {
        var suffix = grunt.config.get('lib.suffix') || '';
        var wasmPath = 'src/libunicorn' + suffix + '.out.wasm';
        if (grunt.file.exists(wasmPath)) {
            grunt.task.run('copy');
        } else {
            grunt.log.writeln('Skipping wasm copy, file not found: ' + wasmPath);
        }
    });

    grunt.registerTask('build', 'Build for specific architecture', function (arch) {
        if (typeof arch === 'undefined') {
            grunt.config.set('lib.suffix', '');
            grunt.task.run('exec:emscripten');
        } else {
            grunt.config.set('lib.suffix', '-'+arch);
            grunt.task.run('exec:emscripten:'+arch);
        }
        grunt.task.run('concat');
        grunt.task.run('copyWasmIfExists');
    });
    grunt.registerTask('release', [
        'build',
        'build:aarch64',
        'build:arm',
        'build:mips',
        'build:m68k',
        'build:sparc',
        'build:x86',
    ]);
    grunt.registerTask('serve', [
        'connect',
        'watch',
    ]);
};
