#!/usr/bin/env python3
"""Compile actual input handlers against mock events; supplementary to compositor tests."""
from pathlib import Path
import subprocess
import os

import tempfile

root = Path(__file__).resolve().parents[1]
_tmp = tempfile.TemporaryDirectory(prefix='gamescope-input-compat-')
out = Path(_tmp.name)
main = (root/'src/main.cpp').read_text()
wl = (root/'src/wlserver.cpp').read_text()
wayland = (root/'src/Backends/WaylandBackend.cpp').read_text()


def build(name, content):
    path = out/f'{name}.cpp'
    path.write_text(content)
    subprocess.run(['c++', '-std=gnu++20', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter', '-Wno-missing-field-initializers', '-I'+str(root/'src'), str(path), '-o', str(out/name)], check=True)

# The production option table and dispatch block are copied verbatim. Only the
# compositor startup is replaced by printing the resulting pointer settings.
options = main[main.index('const struct option *gamescope_options ='):main.index('\nconst char usage[]')]
handler = main[main.index('} else if (strcmp(opt_name, "tap-to-click")'):main.index('} else if (strcmp(opt_name, "virtual-connector-strategy")')]
handler = handler.removeprefix('} else ') + '}'
build('pointer_cli_harness', '#include "main.hpp"\n#include <cstring>\n#include <iostream>\n' + options + r'''
bool g_tapToClick = false;
bool g_tapAndDrag = false;
bool g_dragLock = false;
SelectedPointerType g_naturalScrolling = SelectedPointerType::NONE;
int main(int argc, char **argv) {
    int option_index = -1;
    int result;
    while ((result = getopt_long(argc, argv, "", gamescope_options, &option_index)) != -1) {
        if (result != 0) return 1;
        const char *opt_name = gamescope_options[option_index].name;
''' + handler + r'''
    }
    std::cout << g_tapToClick << ' ' << g_tapAndDrag << ' ' << g_dragLock << ' ' << static_cast<int>(g_naturalScrolling) << '\n';
}
''')
count = 0
for spelling in ['--tap-and-drag', '--tap-to-drag']:
    for name, enum in [('none', 0), ('touchpad', 1), ('mouse', 2), ('all', 3), ('unknown', 0)]:
        for args in [['--natural-scrolling', name], ['--natural-scrolling='+name]]:
            actual = subprocess.check_output([str(out/'pointer_cli_harness'), '--tap-to-click', spelling, '--drag-lock', *args], text=True).strip()
            assert actual == f'1 1 1 {enum}', (spelling, name, actual)
            count += 1
assert subprocess.check_output([str(out/'pointer_cli_harness')], text=True).strip() == '0 0 0 0'
for args in [['--natural-scrolling'], ['--tap-and-drag=invalid'], ['--tap-to-drag=invalid']]:
    assert subprocess.run([str(out/'pointer_cli_harness'), *args], capture_output=True).returncode != 0
    count += 1
print(f'PASS: production pointer option table/handler, {count + 1} CLI cases')

build('pointer_policy', r'''
#include "main.hpp"
#include <cassert>
int main() {
    assert(IsTapAndDragOption("tap-and-drag"));
    assert(IsTapAndDragOption("tap-to-drag"));
    assert(!IsTapAndDragOption("tap-to-click"));
    assert(!IsTapAndDragOption("drag-lock"));
    assert(ParseSelectedPointerType("none") == SelectedPointerType::NONE);
    assert(ParseSelectedPointerType("touchpad") == SelectedPointerType::TOUCHPAD);
    assert(ParseSelectedPointerType("mouse") == SelectedPointerType::MOUSE);
    assert(ParseSelectedPointerType("all") == SelectedPointerType::ALL);
    assert(ParseSelectedPointerType("") == SelectedPointerType::NONE);
    assert(ParseSelectedPointerType("unknown") == SelectedPointerType::NONE);
    for (bool touchpad : {false, true}) {
        assert(!NaturalScrollingEnabled(SelectedPointerType::NONE, touchpad));
        assert(NaturalScrollingEnabled(SelectedPointerType::ALL, touchpad));
        assert(NaturalScrollingEnabled(SelectedPointerType::TOUCHPAD, touchpad) == touchpad);
        assert(NaturalScrollingEnabled(SelectedPointerType::MOUSE, touchpad) == !touchpad);
    }
}
''')
subprocess.run([str(out/'pointer_policy')], check=True)
print('PASS: production pointer helpers, 18 policy checks')

key_handler = wl[wl.index('static const bool env_gs_enable_ctrl_12'):wl.index('static void wlserver_perform_rel_pointer_motion')]
build('overlay_harness', r'''
#include <cstdint>
#include <cstdlib>
#include <cassert>
#include <vector>
#include <map>
#include <unordered_set>
using xkb_keycode_t = uint32_t;
using xkb_keysym_t = uint32_t;
constexpr uint32_t WLR_MODIFIER_CTRL = 4, WLR_MODIFIER_LOGO = 64;
constexpr uint32_t XKB_KEY_1 = 49, XKB_KEY_2 = 50;
constexpr uint32_t XKB_KEY_XF86AudioLowerVolume = 100, XKB_KEY_XF86AudioRaiseVolume = 101, XKB_KEY_XF86PowerOff = 102;
constexpr uint32_t WL_KEYBOARD_KEY_STATE_RELEASED = 0, WL_KEYBOARD_KEY_STATE_PRESSED = 1;
struct wl_listener {};
struct wlr_surface {};
struct wlr_keyboard_modifiers { uint32_t depressed, latched, locked, group; };
struct wlr_keyboard { int *xkb_state = nullptr; wlr_keyboard_modifiers modifiers{}; };
struct wlr_keyboard_key_event { uint32_t time_msec, keycode, state; };
struct keyboard_group { wlr_keyboard keyboard; };
keyboard_group group;
wlr_surface game, steam;
bool steam_exists = true;
struct {
    struct keyboard_group *keyboard_group = &group;
    wlr_surface *kb_focus_surface = &game;
    struct { void *seat = nullptr; } wlr;
    std::map<std::pair<wlr_keyboard *, uint32_t>, uint32_t> mapPressedHotkeyKeys;
} wlserver;
uint32_t sym;
uint32_t xkb_state_key_get_one_sym(int *, uint32_t) { return sym; }
wlr_surface *steamcompmgr_get_server_input_surface(int) { return steam_exists ? &steam : nullptr; }
void wlserver_keyboardfocus(wlr_surface *surface, bool) { wlserver.kb_focus_surface = surface; }
void wlr_seat_set_keyboard(void *, wlr_keyboard *) {}
struct Event { wlr_surface *surface; uint32_t key, state; wlr_keyboard_modifiers mods; };
wlr_keyboard_modifiers current_mods{};
std::vector<Event> keys;
std::vector<wlr_keyboard_modifiers> modifiers;
void wlr_seat_keyboard_notify_modifiers(void *, wlr_keyboard_modifiers *mods) { current_mods = *mods; modifiers.push_back(*mods); }
void wlr_seat_keyboard_notify_key(void *, uint32_t, uint32_t key, uint32_t state) { keys.push_back({wlserver.kb_focus_surface, key, state, current_mods}); }
bool wlserver_process_hotkeys(wlr_keyboard *, uint32_t, bool) { return false; }
void bump_input_counter() {}
''' + key_handler + r'''
void send(uint32_t key, bool pressed, uint32_t mods) {
    sym = key;
    group.keyboard.modifiers = {.depressed = mods, .group = 1};
    wlr_keyboard_key_event event{0, key, uint32_t(pressed)};
    wlserver_handle_key(nullptr, &event);
}
void expectSteamPair(uint32_t key, uint32_t mods) {
    keys.clear(); modifiers.clear();
    send(key, true, mods);
    send(key, false, 0); // modifier lifted before the number
    assert(keys.size() == 2);
    for (const auto &event : keys) {
        assert(event.surface == &steam);
        assert(event.mods.depressed == WLR_MODIFIER_CTRL);
        assert(event.mods.latched == 0 && event.mods.locked == 0);
        assert(event.mods.group == 1);
    }
    assert(keys[0].state == 1 && keys[1].state == 0);
    assert(wlserver.kb_focus_surface == &game);
    assert(modifiers.back().depressed == 0);
}
int main() {
    expectSteamPair(XKB_KEY_1, WLR_MODIFIER_LOGO);
    expectSteamPair(XKB_KEY_2, WLR_MODIFIER_LOGO);
    if (env_gs_enable_ctrl_12) {
        expectSteamPair(XKB_KEY_1, WLR_MODIFIER_CTRL);
        expectSteamPair(XKB_KEY_2, WLR_MODIFIER_CTRL);
    } else {
        keys.clear(); send(XKB_KEY_1, true, WLR_MODIFIER_CTRL); send(XKB_KEY_1, false, 0);
        assert(keys.size() == 2 && keys[0].surface == &game && keys[1].surface == &game);
    }
    // Pressing Ctrl after a normal number press cannot steal its release.
    keys.clear(); send(XKB_KEY_1, true, 0); send(XKB_KEY_1, false, WLR_MODIFIER_CTRL);
    assert(keys.size() == 2 && keys[0].surface == &game && keys[1].surface == &game);
    // Unrelated keys remain in the game.
    keys.clear(); send(65, true, WLR_MODIFIER_LOGO); send(65, false, 0);
    assert(keys.size() == 2 && keys[0].surface == &game && keys[1].surface == &game);
    // Steam disappearing must not leak an unmatched release into the game.
    keys.clear(); send(XKB_KEY_2, true, WLR_MODIFIER_LOGO); steam_exists = false; send(XKB_KEY_2, false, 0);
    assert(keys.size() == 1 && keys[0].surface == &steam);
    // No Steam target means the initial shortcut press is not swallowed.
    keys.clear(); send(XKB_KEY_2, true, WLR_MODIFIER_LOGO); send(XKB_KEY_2, false, 0);
    assert(keys.size() == 2 && keys[0].surface == &game && keys[1].surface == &game);
    steam_exists = true;
    // System keys keep the upstream root-only route.
    keys.clear(); send(XKB_KEY_XF86AudioRaiseVolume, true, 0); send(XKB_KEY_XF86AudioRaiseVolume, false, 0);
    assert(keys.size() == 2 && keys[0].surface == &steam && keys[1].surface == &steam);
}
''')
for value in [None, '0', '1']:
    env = dict(os.environ)
    if value is None:
        env.pop('GS_ENABLE_CTRL_12', None)
    else:
        env['GS_ENABLE_CTRL_12'] = value
    subprocess.run([str(out/'overlay_harness')], env=env, check=True)
print('PASS: production physical-key handler, Super/Ctrl routing, paired releases, modifiers, missing Steam; GS_ENABLE_CTRL_12 unset/0/1')

touch = wayland[wayland.index('    static std::pair<double, double> TouchToOutput'):wayland.index('    /////////////////////////\n    // Backend Instantiator')]
build('touch_harness', r'''
#include <cstdint>
#include <cassert>
#include <cmath>
#include <optional>
#include <utility>
#include <unordered_map>
#include <vector>
using wl_fixed_t = int32_t;
struct wl_touch {};
struct wl_surface { void *data; bool toplevel = true; };
struct WaylandPlaneState { uint32_t uFractionalScale; int32_t nDestX, nDestY; };
struct CWaylandPlane {
    std::optional<WaylandPlaneState> state;
    auto GetCurrentState() { return state; }
};
bool IsGamescopeToplevel(wl_surface *surface) { return surface && surface->toplevel; }
void *wl_surface_get_user_data(wl_surface *surface) { return surface->data; }
double wl_fixed_to_double(wl_fixed_t value) { return value / 256.0; }
uint32_t g_nOutputWidth = 1920, g_nOutputHeight = 1080;
int locked = 0;
void wlserver_lock() { ++locked; }
void wlserver_unlock() { --locked; }
struct Event { char kind; double x, y; int id; uint32_t time; };
std::vector<Event> events;
void wlserver_touchdown(double x, double y, int id, uint32_t time) { assert(locked); events.push_back({'d', x, y, id, time}); }
void wlserver_touchmotion(double x, double y, int id, uint32_t time) { assert(locked); events.push_back({'m', x, y, id, time}); }
void wlserver_touchup(int id, uint32_t time) { assert(locked); events.push_back({'u', 0, 0, id, time}); }
struct CWaylandInputThread {
    uint32_t m_uFakeTimestamp = 0;
    std::unordered_map<int32_t, WaylandPlaneState> m_TouchPlaneStates;
    void Wayland_Touch_Down(wl_touch *, uint32_t, uint32_t, wl_surface *, int32_t, wl_fixed_t, wl_fixed_t);
    void Wayland_Touch_Up(wl_touch *, uint32_t, uint32_t, int32_t);
    void Wayland_Touch_Motion(wl_touch *, uint32_t, int32_t, wl_fixed_t, wl_fixed_t);
    void Wayland_Touch_Cancel(wl_touch *);
};
''' + touch + r'''
bool near(double a, double b) { return std::abs(a-b) < 1e-10; }
int main() {
    CWaylandInputThread input;
    CWaylandPlane plane{WaylandPlaneState{180, 120, 60}};
    wl_surface surface{&plane};
    input.Wayland_Touch_Down(nullptr, 0, 0, &surface, 3, 256*200, 256*100);
    assert(events.size() == 1 && events[0].kind == 'd');
    assert(near(events[0].x, 420.0/1920) && near(events[0].y, 210.0/1080));
    // Motion must use the touchdown snapshot, even after the surface disappears.
    surface.data = nullptr; plane.state = WaylandPlaneState{120, 0, 0};
    input.Wayland_Touch_Motion(nullptr, 0, 3, 256*220, 256*120);
    assert(events.size() == 2 && events[1].kind == 'm');
    assert(near(events[1].x, 450.0/1920) && near(events[1].y, 240.0/1080));
    input.Wayland_Touch_Up(nullptr, 0, 0, 999);
    input.Wayland_Touch_Motion(nullptr, 0, 999, 0, 0);
    assert(events.size() == 2);
    input.Wayland_Touch_Up(nullptr, 0, 0, 3);
    input.Wayland_Touch_Up(nullptr, 0, 0, 3);
    assert(events.size() == 3 && events.back().kind == 'u');
    assert(input.m_TouchPlaneStates.empty());
    // Missing states and non-Gamescope surfaces must be ignored.
    input.Wayland_Touch_Down(nullptr, 0, 0, &surface, 9, 0, 0);
    surface.data = &plane; plane.state.reset();
    input.Wayland_Touch_Down(nullptr, 0, 0, &surface, 9, 0, 0);
    plane.state = WaylandPlaneState{120, 0, 0}; surface.toplevel = false;
    input.Wayland_Touch_Down(nullptr, 0, 0, &surface, 9, 0, 0);
    assert(events.size() == 3);
    surface.toplevel = true;
    input.Wayland_Touch_Down(nullptr, 0, 0, &surface, 4, 0, 0);
    input.Wayland_Touch_Down(nullptr, 0, 0, &surface, 5, 256*1920, 256*1080);
    assert(near(events.back().x, 1.0) && near(events.back().y, 1.0));
    input.Wayland_Touch_Cancel(nullptr);
    assert(events.size() == 7 && events[5].kind == 'u' && events[6].kind == 'u');
    assert(events[5].id != events[6].id);
    assert(input.m_TouchPlaneStates.empty() && !locked);
    input.Wayland_Touch_Cancel(nullptr);
    assert(events.size() == 7);
    for (size_t i = 0; i < events.size(); ++i) assert(events[i].time == i+1);
}
''')
subprocess.run([str(out/'touch_harness')], check=True)
print('PASS: production nested-touch handlers, fractional scale/offsets, destroyed surface snapshots, ignored IDs, multi-touch cancellation and monotonic timestamps')
