#!/usr/bin/env python3
"""Dependency-light display policy regressions, using the production C++/GLSL.

Run with python3 tests/test_display_compat.py. A C++20 compiler is required.
The selected production functions/blocks are compiled against small test doubles;
this does not replace a full Gamescope build, shader compilation or hardware QA.
"""

import os
import shlex
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "src/main.cpp").read_text()
DRM = (ROOT / "src/Backends/DRMBackend.cpp").read_text()
STEAM = (ROOT / "src/steamcompmgr.cpp").read_text()
WLSERVER = (ROOT / "src/wlserver.cpp").read_text()
SHADER = (ROOT / "src/shaders/composite.h").read_text()


def block(source, signature):
    """Extract the specified definition, including its balanced brace body."""
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


def between(source, start, end):
    return source.split(start, 1)[1].split(end, 1)[0]


class DisplayCompatibilityTests(unittest.TestCase):
    def compile_and_run(self, code):
        with tempfile.TemporaryDirectory(prefix="gamescope-display-test-") as temp:
            source = Path(temp) / "test.cpp"
            binary = Path(temp) / "test"
            source.write_text(
                '#include <cassert>\n#include <cmath>\n#include <cstring>\n'
                '#include <cstdio>\n#include <cstdlib>\n#include <optional>\n'
                '#include <vector>\n#include <memory>\n#include <getopt.h>\n'
                '#include "gamescope_shared.h"\n' + code
            )
            subprocess.run(
                shlex.split(os.environ.get("CXX", "c++")) + ["-std=c++20", "-Wall", "-Wextra",
                 "-Wno-missing-field-initializers", "-I", str(ROOT / "src"),
                 str(source), "-o", str(binary)], check=True,
            )
            subprocess.run([str(binary)], check=True)

    def test_session_flags_and_all_rotation_touch_mappings(self):
        options = block(MAIN, "const struct option *gamescope_options") + ";"
        orientation = block(MAIN, "static GamescopePanelOrientation force_orientation")
        touch = block(WLSERVER, "static void apply_touchscreen_orientation")
        shader = block(SHADER, "uvec2 outputLogicalSize") + "\n" + block(SHADER, "ivec2 rotateOutputCoord")
        mode = between(block(DRM, "bool drm_set_mode( struct drm_t *drm, const drmModeModeInfo *mode )\n{"), "// 90/270 transpose", "\n\treturn true;")
        mode = mode[mode.index("\n"):]
        self.assertRegex(MAIN, r'"force-composition-rotation"\) == 0 \|\|\s*strcmp\(opt_name, "use-rotation-shader"\) == 0\) \{\s*g_bForceCompositionRotation = true;')
        self.assertRegex(MAIN, r'"hdr-pq-internal-enable"\) == 0\) \{\s*g_bEnableInternalPq = true;')
        self.compile_and_run(options + orientation + touch + r'''
using uint = unsigned;
struct uvec2 { uint x, y; uvec2(uint x_, uint y_): x(x_), y(y_) {} };
using ivec2 = uvec2;
uvec2 dst(0, 0);
uvec2 imageSize(uvec2 value) { return value; }
''' + shader + r'''
constexpr unsigned DRM_MODE_ROTATE_90 = 1 << 1;
constexpr unsigned DRM_MODE_ROTATE_180 = 1 << 2;
constexpr unsigned DRM_MODE_ROTATE_270 = 1 << 3;
struct Connector {
    GamescopePanelOrientation orientation;
    auto GetCurrentOrientation() { return orientation; }
};
struct Plane { uint64_t supported = 0; };
struct drm_t { Connector *pConnector; Plane *pPrimaryPlane; };
struct Mode { uint hdisplay, vdisplay; };
uint g_nOutputWidth, g_nOutputHeight, g_uOutputRotation;
bool g_bRotated, g_bForceCompositionRotation;
uint64_t drm_plane_supported_rotations(drm_t *, Plane *plane) { return plane->supported; }
void set_mode(drm_t *drm, Mode *mode) {
''' + mode + r'''
}
int main() {
    const char *args[] = {"gamescope", "--use-rotation-shader", "1", "--force-orientation", "left",
                          "--hdr-pq-internal-enable", "--", "game", nullptr};
    int index = 0;
    assert(getopt_long(8, const_cast<char **>(args), "", gamescope_options, &index) == 0);
    assert(!strcmp(gamescope_options[index].name, "use-rotation-shader") && !strcmp(optarg, "1"));
    assert(getopt_long(8, const_cast<char **>(args), "", gamescope_options, &index) == 0);
    assert(!strcmp(gamescope_options[index].name, "force-orientation") && !strcmp(optarg, "left"));
    assert(getopt_long(8, const_cast<char **>(args), "", gamescope_options, &index) == 0);
    assert(!strcmp(gamescope_options[index].name, "hdr-pq-internal-enable") && !optarg);
    assert(getopt_long(8, const_cast<char **>(args), "", gamescope_options, &index) == -1 && optind == 7);
    const char *names[] = {"normal", "left", "upsidedown", "right"};
    const GamescopePanelOrientation orientations[] = {GAMESCOPE_PANEL_ORIENTATION_0,
        GAMESCOPE_PANEL_ORIENTATION_90, GAMESCOPE_PANEL_ORIENTATION_180, GAMESCOPE_PANEL_ORIENTATION_270};
    Mode mode{7, 11};
    Plane plane{};
    Connector connector{};
    drm_t drm{&connector, &plane};
    for (uint rotation = 0; rotation < 4; ++rotation) {
        connector.orientation = force_orientation(names[rotation]);
        assert(connector.orientation == orientations[rotation]);
        for (bool force : {false, true}) {
            for (bool supported : {false, true}) {
                g_bForceCompositionRotation = force;
                plane.supported = supported ? 15 : 0;
                set_mode(&drm, &mode);
                assert(g_bRotated == bool(rotation & 1));
                assert(g_nOutputWidth == ((rotation & 1) ? mode.vdisplay : mode.hdisplay));
                assert(g_nOutputHeight == ((rotation & 1) ? mode.hdisplay : mode.vdisplay));
                assert(g_uOutputRotation == ((force || !supported) ? rotation : 0));
            }
        }
        dst = uvec2(mode.hdisplay, mode.vdisplay);
        const auto logical = outputLogicalSize(rotation);
        assert(logical.x == g_nOutputWidth && logical.y == g_nOutputHeight);
        std::vector<bool> visited(dst.x * dst.y, false);
        for (uint x = 0; x < logical.x; ++x) for (uint y = 0; y < logical.y; ++y) {
            auto physical = rotateOutputCoord(uvec2(x, y), rotation);
            assert(physical.x < dst.x && physical.y < dst.y);
            assert(!visited[physical.y * dst.x + physical.x]);
            visited[physical.y * dst.x + physical.x] = true;
            double tx = (physical.x + 0.5) / dst.x, ty = (physical.y + 0.5) / dst.y;
            apply_touchscreen_orientation(connector.orientation, &tx, &ty);
            assert(std::abs(tx * logical.x - (x + 0.5)) < 1e-9);
            assert(std::abs(ty * logical.y - (y + 0.5)) < 1e-9);
        }
        for (bool value : visited) assert(value);
    }
}
''')

    def test_partial_color_properties_and_missing_crtc(self):
        functions = block(DRM, "bool drm_supports_color_mgmt(struct drm_t *drm)\n{")
        functions += block(DRM, "bool drm_supports_srgb_to_pq(struct drm_t *drm)\n{")
        self.compile_and_run(r'''
struct Properties {
    std::optional<int> AMD_PLANE_CTM, AMD_PLANE_SHAPER_LUT, AMD_PLANE_SHAPER_TF,
        AMD_PLANE_LUT3D, AMD_PLANE_DEGAMMA_TF, AMD_PLANE_BLEND_TF, AMD_CRTC_REGAMMA_TF;
};
struct Object { Properties properties; auto &GetProperties() { return properties; } };
struct drm_t { Object *pPrimaryPlane = nullptr, *pCRTC = nullptr; };
bool g_bForceDisableColorMgmt = false;
''' + functions + r'''
int main() {
    drm_t drm;
    assert(!drm_supports_color_mgmt(&drm) && !drm_supports_srgb_to_pq(&drm));
    Object plane, crtc;
    drm.pPrimaryPlane = &plane;
    drm.pCRTC = &crtc;
    for (unsigned mask = 0; mask < 128; ++mask) {
        auto present = [&](unsigned bit) { return mask & (1u << bit) ? std::optional<int>{0} : std::nullopt; };
        plane.properties = {present(0), present(1), present(2), present(3), present(4), present(5), {}};
        crtc.properties.AMD_CRTC_REGAMMA_TF = present(6);
        assert(drm_supports_color_mgmt(&drm) == ((mask & 31) == 31));
        assert(drm_supports_srgb_to_pq(&drm) == (mask == 127));
    }
    drm.pCRTC = nullptr;
    assert(drm_supports_color_mgmt(&drm) && !drm_supports_srgb_to_pq(&drm));
    g_bForceDisableColorMgmt = true;
    assert(!drm_supports_color_mgmt(&drm) && !drm_supports_srgb_to_pq(&drm));
}
''')

    def test_persistent_color_adjustments_and_hdr_compositing(self):
        decision = between(DRM, "bNeedsFullComposite |= !g_reshade_effect.empty();", "\n\t\t\tbNeedsFullComposite |= !!(g_uCompositeDebug")
        self.compile_and_run(r'''
enum EOTF { EOTF_Gamma22, EOTF_PQ };
struct ColorState {
    bool enabled = true;
    struct Night { float amount = 0; } nightmode;
    struct White { float x = 0.3127f, y = 0.3290f; } outputVirtualWhite;
    float sdrGamutWideness = 0.5f, flBacklightLutGain = 1.0f;
};
struct ColorMgmt { ColorState pending, current; } g_ColorMgmt;
bool color_support = false, blend_support = false;
bool SupportsColorManagement() { return color_support; }
bool SupportsSRGBtoPQ() { return blend_support; }
bool g_bOutputHDREnabled = false, g_bHDRItmEnable = false;
struct Frame {
    struct Layers {
        struct Layer { GamescopeAppTextureColorspace colorspace = GAMESCOPE_APP_TEXTURE_COLORSPACE_SRGB; } base;
        int size = 1;
        int count() { return size; }
        Layer &get(int) { return base; }
    } layers;
    EOTF outputEncodingEOTF = EOTF_Gamma22;
};
bool needs_composite(Frame *pFrameInfo) {
    bool bNeedsFullComposite = false;
''' + decision + r'''
    return bNeedsFullComposite;
}
int main() {
    Frame frame;
    assert(!needs_composite(&frame));
    g_ColorMgmt.pending.nightmode.amount = 0.5f;
    assert(needs_composite(&frame));
    g_ColorMgmt.pending.enabled = false;
    assert(!needs_composite(&frame));
    g_ColorMgmt.pending = {};
    g_ColorMgmt.pending.outputVirtualWhite.x += 0.01f;
    assert(needs_composite(&frame));
    g_ColorMgmt.pending = {};
    g_ColorMgmt.pending.outputVirtualWhite.y += 0.01f;
    assert(needs_composite(&frame));
    g_ColorMgmt.pending = {};
    g_ColorMgmt.pending.sdrGamutWideness = 0.8f;
    assert(needs_composite(&frame));
    color_support = true; // Newer AMD: LUTs but no blend TF still apply color.
    assert(!needs_composite(&frame));
    g_ColorMgmt.pending = {};
    frame.layers.base.colorspace = GAMESCOPE_APP_TEXTURE_COLORSPACE_SCRGB;
    assert(needs_composite(&frame)); // HDR -> SDR without blend support.
    g_bOutputHDREnabled = true;
    frame.layers.base.colorspace = GAMESCOPE_APP_TEXTURE_COLORSPACE_HDR10_PQ;
    assert(needs_composite(&frame)); // PQ input cannot pass through a Gamma 2.2 panel.
    frame.outputEncodingEOTF = EOTF_PQ;
    assert(!needs_composite(&frame));
    frame.layers.size = 2;
    assert(needs_composite(&frame));
    blend_support = true;
    assert(!needs_composite(&frame));
    g_bHDRItmEnable = true;
    assert(needs_composite(&frame));
    g_bHDRItmEnable = false;
    frame.layers.size = 1;
    color_support = blend_support = false;
    assert(!needs_composite(&frame));
    g_ColorMgmt.current.flBacklightLutGain = 0.5f;
    assert(needs_composite(&frame)); // Keep upstream Go 2 software brightness.
}
''')

    def test_internal_hdr_policy_and_all_live_windows(self):
        active = between(STEAM, "gamescope::IBackendConnector *pConn = GetBackend()->GetCurrentConnector();\n\t\t\tconst bool bContentDriven", "\n\t\t\tg_bOutputHDREnabled = bOutputHDRActive;")
        active = "const bool bContentDriven" + active
        pq = between(DRM, "// Explicit known-display profiles remain authoritative above.", "\n\t\t\t\t}")
        pq = pq[pq.index("m_Mutable.HDR.eOutputEncodingEOTF"):]
        self.assertIn("bool g_bEnableInternalPq = false;", MAIN)
        self.compile_and_run(r'''
enum EOTF { EOTF_Gamma22, EOTF_PQ };
namespace gamescope {
struct IBackendConnector {
    GamescopeScreenType type = GAMESCOPE_SCREEN_TYPE_INTERNAL;
    struct HDR { bool bContentDrivenHDR = false; } hdr;
    auto GetScreenType() { return type; }
    auto &GetHDRInfo() { return hdr; }
};
}
using namespace gamescope;
struct commit_t { GamescopeAppTextureColorspace color; auto colorspace() { return color; } };
constexpr int IsViewable = 2, InputOutput = 1;
enum class steamcompmgr_win_type_t { XWAYLAND, XDG };
struct steamcompmgr_win_t {
    commit_t *commit = nullptr;
    struct XWayland {
        steamcompmgr_win_t *next = nullptr;
        struct Attributes { int map_state = IsViewable, c_class = InputOutput; } a;
    } x11;
    struct Xdg { struct Surface { bool mapped = true; } surface; } xdg_win;
    steamcompmgr_win_type_t type = steamcompmgr_win_type_t::XWAYLAND;
    bool has_surface = true;
    auto &xwayland() { return x11; }
    auto &xdg() { return xdg_win; }
    void *current_surface() { return has_surface ? this : nullptr; }
};
commit_t *get_window_last_done_commit_peek(steamcompmgr_win_t *win) { return win->commit; }
struct Context { steamcompmgr_win_t *list = nullptr; };
struct gamescope_xwayland_server_t { Context *ctx; };
std::vector<gamescope_xwayland_server_t> servers;
auto wlserver_get_xwayland_server(size_t index) { return index < servers.size() ? &servers[index] : nullptr; }
std::vector<std::shared_ptr<steamcompmgr_win_t>> g_steamcompmgr_xdg_wins;
bool cv_hdr_content_driven = false, g_bForceHDR10OutputDebug = false, g_bOutputHDREnabled = false;
struct Log { void infof(const char *, const char *, const char *) {} } xwm_log;
bool active_hdr(IBackendConnector *pConn, bool bOutputHDRCapable) {
''' + active + r'''
    return bOutputHDRActive;
}
struct Panel {
    struct Mutable { struct HDR { EOTF eOutputEncodingEOTF; } HDR; } m_Mutable;
    GamescopeScreenType type;
    auto GetScreenType() { return type; }
    EOTF detect(bool g_bEnableInternalPq) {
''' + pq + r'''
        return m_Mutable.HDR.eOutputEncodingEOTF;
    }
};
int main() {
    IBackendConnector internal, external;
    external.type = GAMESCOPE_SCREEN_TYPE_EXTERNAL;
    assert(!active_hdr(&internal, false));
    assert(!active_hdr(&internal, true));
    assert(active_hdr(&external, true));
    assert(active_hdr(nullptr, true)); // hot unplug: no connector dereference
    assert(!active_hdr(nullptr, false));
    commit_t hdr{GAMESCOPE_APP_TEXTURE_COLORSPACE_HDR10_PQ}, sdr{GAMESCOPE_APP_TEXTURE_COLORSPACE_SRGB};
    steamcompmgr_win_t first{}, background{&hdr};
    first.x11.next = &background;
    Context first_context{}, second_context{&first};
    servers = {{&first_context}, {&second_context}};
    assert(active_hdr(&internal, true));
    background.x11.a.map_state = 0;
    assert(!active_hdr(&internal, true));
    background.x11.a.map_state = IsViewable;
    background.has_surface = false;
    assert(!active_hdr(&internal, true));
    background.has_surface = true;
    background.commit = &sdr;
    assert(!active_hdr(&internal, true));
    auto xdg = std::make_shared<steamcompmgr_win_t>();
    xdg->commit = &hdr;
    xdg->type = steamcompmgr_win_type_t::XDG;
    g_steamcompmgr_xdg_wins.push_back(xdg);
    assert(active_hdr(&internal, true));
    xdg->xdg_win.surface.mapped = false;
    assert(!active_hdr(&internal, true));
    xdg->xdg_win.surface.mapped = true;
    assert(!active_hdr(&internal, false));
    g_steamcompmgr_xdg_wins.clear();
    assert(!active_hdr(&internal, true));
    cv_hdr_content_driven = true;
    assert(!active_hdr(&external, true));
    assert(!active_hdr(nullptr, true));
    g_bForceHDR10OutputDebug = true;
    assert(active_hdr(&internal, true));
    for (auto screen : {GAMESCOPE_SCREEN_TYPE_INTERNAL, GAMESCOPE_SCREEN_TYPE_EXTERNAL}) {
        Panel panel{{}, screen};
        assert(panel.detect(false) == (screen == GAMESCOPE_SCREEN_TYPE_INTERNAL ? EOTF_Gamma22 : EOTF_PQ));
        assert(panel.detect(true) == EOTF_PQ);
    }
}
''')


if __name__ == "__main__":
    unittest.main()
