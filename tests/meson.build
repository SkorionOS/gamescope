catch2_dep = dependency('catch2-with-main', required: true)

srcdir = '../src'
unittest_src = []
foreach src : gamescope_core_src + ['Script/Script.cpp', 'convar_script.cpp']
	unittest_src += srcdir / src
endforeach

gamescope_tests = executable(
	'gamescope_tests',
	unittest_src + ['../src/color_helpers.cpp', 'test_color_helpers.cpp', 'test_waitable.cpp', 'test_convar.cpp', 'test_focus_placement.cpp', 'test_mangoapp_config.cpp', 'test_mangoapp_control.cpp', 'test_mode_list.cpp', 'test_process.cpp', 'test_pointer_options.cpp', 'test_upscale.cpp', 'test_utils_parsers.cpp', 'test_utils_string.cpp', 'test_vrclient_detect.cpp'],
	include_directories: [srcdir, sol2_include],
	dependencies: [catch2_dep, luajit_dep, cap_dep, drm_dep, glm_dep, wlroots_dep],
	cpp_args: gamescope_cpp_args,
)

reaper_test_helper = executable('reaper_test_helper', 'reaper_test_helper.cpp')

test('convar', gamescope_tests, args: ['[convar]'])
test('color_helpers', gamescope_tests, args: ['[color_helpers]'])
test('focus_placement', gamescope_tests, args: ['[focus_placement]'])
test('mangoapp_config', gamescope_tests, args: ['[mangoapp_config]'])
test('mangoapp_control', gamescope_tests, args: ['[mangoapp_control]'])
test('mode_list', gamescope_tests, args: ['[mode_list]'])
test('upscale', gamescope_tests, args: ['[upscale]'])
test('utils/parsers', gamescope_tests, args: ['[parsers]'])
test('utils/process', gamescope_tests, args: ['[process]'], depends: [reaper_test_helper])
test('utils/string', gamescope_tests, args: ['[string]'])
test('vrclient_detect', gamescope_tests, args: ['[vrclient_detect]'])

# Pure policy tests can also be compiled directly without a GPU or compositor.
skos_policy_tests = executable('gamescope_skos_policy_tests', 'test_skos_policy.cpp', include_directories: [srcdir])
test('skos_policy', skos_policy_tests)

test('waitable', gamescope_tests, args: ['[waitable]'])
test('pointer_options', gamescope_tests, args: ['[pointer_options]'])
python3 = import('python').find_installation('python3')
test('pointer_cli', python3, args: [files('test_pointer_cli.py'), gamescope_executable])

test('display_compat', python3, args: [files('test_display_compat.py')])
test('input_compat', python3, args: [files('test_input_compat.py')])
