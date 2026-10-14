# SKOS Gamescope 3.16.31 compatibility migration

## Fixed baseline and scope

This candidate upgrades `3.16.23.5.sk1` (`7064a0ffe96b2be82980b0093c71179a9b5749a8`)
to Valve's fixed `3.16.31` commit
`6867f509874f9bc52e12d6f4c4596cdf0d5be6b4`, preserving the production
`honjow/gamescope-session` interface at
`c7f5f5256823983fa277ca34b860161d77b83e91`.

The production source is retained in
`backup/sk-gamescope-3.16.23.5.sk1-20261014`. Existing version tags are not moved.
The intended new release is `3.16.31.sk1`; a candidate is not a published package.

The baseline includes upstream compositing rotation, Legion Go 2 display/HDR
and software-backlight handling, and persistent headless output support.
It deliberately does not import the October `VK_EXT_present_timing` and large
frame-scheduling change set. Those changes need a separate migration and
power/frame-pacing qualification. It does include the subsequent pointer-lock
regression revert, final nested touch implementation, keyboard lifecycle fixes,
HDR10 gamut fix and allocation-failure fix listed below.

## Every production downstream feature

| Production commit | Contract | Candidate treatment |
| --- | --- | --- |
| `e1097fc1` | `--custom-refresh-rates`, lists and inclusive ranges | Retained for unknown internal displays; bounded strict parsing prevents malformed/range-overflow hangs. Known Lua profiles retain precedence. |
| `f2997bb0` | Super/Ctrl + 1/2, Steam Overlay/QAM | Retained with `GS_ENABLE_CTRL_12` and root-server routing. Modifier state is initialized and releases remain paired if modifiers are released first. |
| `55f1b466` | Lua `dynamic_refresh_rates` without `dynamic_modegen` | Retained; advertised rates do not require a custom mode generator. |
| `42a7227d` | `GAMESCOPE_STEAMUI_HALFHZ` | Retained, including the existing >100 Hz and requested-limit policy; requested limits are restored when Steam loses focus or the atom is disabled. |
| `a6df6261` | Intel shader rotation | Replaced by upstream final-composition rotation; legacy `--use-rotation-shader VALUE` consumes its required argument exactly as the deployed session expects. |
| `0f325b95` | `GAMESCOPE_WSI_HIDE_PRESENT_WAIT_EXT` | Retained in the WSI layer. |
| `0b3e3d4f` | ASUS Z13 display configuration | Retained. |
| `95dbc551` | Vertical-front-porch scheduling allowance | Retained; nanoseconds use measured mode refresh in mHz and guard invalid porch inputs. |
| `729fcf44` | Legion Go S full refresh range | Retained. |
| `5a953e71` | `GAMESCOPE_DPMS` atom | Retained across direct/composited paths; atom sleep is combined with upstream configured sleep before transition detection. |
| `bee43960` | Drain expired timer descriptors | Retained; the overriding VBlank timer also drains before its already-disarmed early return. |
| `532297f3` | Intel night mode and color adjustments | Retained via persistent composition when LUT/CTM scanout is unavailable. |
| `89c97966` | Internal PQ opt-in | `--hdr-pq-internal-enable` retained for EDID-only internal panels; explicit known-display Lua HDR profiles remain authoritative. |
| `7c224585` | Independent LUT/CTM and blend-transfer capability | Retained with complete property checks; partial hardware capability falls back to composition. |
| `7baadd39` | Content-driven internal HDR | Integrated with upstream HDR state, rather than a duplicate state machine; valid mapped Xwayland/XDG windows are considered and detached/unmapped remnants excluded. |
| `c4c982c5` | No-display startup safety | Superseded by upstream headless stand-in connector and primary-plane fallback. |
| `d07c3ded` | HDR hot-unplug safety | Superseded by guarded upstream HDR connector access and headless connector. |
| `b6b10612` | Avoid generic Zotac Zone misidentification | Broad Zotac display profile remains removed. |
| `b8befef7` | Libinput pointer settings | Tap-to-click, drag, drag-lock and none/touchpad/mouse/all natural scrolling retained. Both `--tap-and-drag` and legacy `--tap-to-drag` work. |
| `49768262` | All-angle rotation, dimensions and touch | Replaced by upstream logical-coordinate input and final output rotation; 0/90/180/270 mappings tested. |
| `fec50764` | VRR overlay callback throttling | Retained at output-refresh cadence. |
| `7064a0ff` | Wayland nested touch | Replaced by final upstream `30b1b1e7`, including per-touch plane snapshots and owned-touch cancellation. |

The existing session Lua directory and `drm_debug_disable_explicit_sync` convar
remain available for `GAMESCOPE_DISABLE_EXPLICIT_SYNC` and custom display scripts.

## Selected upstream follow-up fixes

- `56861b7c`: revert the nested relative-pointer regression in 3.16.29–31.
- `1b17fcc1`: release the correct simulated button after a two-finger tap.
- `aea16083`, `dad1c74d`, `32640af7`: host modifiers, keyboard disappearance,
  and hotkey press/release pairing.
- `e0602ccc`: restore app ID/title after a NULL-buffer unmap.
- `30b1b1e7`: final nested Wayland touch implementation.
- `c70f95e7`: express HDR10 native-gamut blending in the correct output space.
- `2b5cf191`: return allocation failure instead of asserting on flat textures.

## Reproducible software checks

Use the pinned submodules and enable `enable_tests`, PipeWire, WSI, DRM, SDL,
OpenVR and input emulation when configuring the build. Run:

```sh
meson compile -C build
meson test -C build --suite gamescope --print-errorlogs
python3 tests/test_pointer_cli.py build/src/gamescope
python3 tests/test_display_compat.py
python3 tests/test_input_compat.py
```

The CLI test invokes the real built binary and the deployed session combination,
including `--use-rotation-shader 1`, both drag spellings and internal-PQ opt-in.
The display/input harnesses compile actual source handlers against small test
doubles. They supplement the real build and unit tests; they do not establish
working physical displays, input devices or GPU rendering.

Coverage includes actual timerfd consumption, ordered refresh lists/ranges and
invalid inputs, HALFHZ transitions, DPMS policy, four-angle pixel/touch mapping,
128 color-capability combinations, HDR lifecycle policy, natural-scrolling
selection, modifier-first shortcut release and nested touch lifetime/cancel.

## Recorded cloud verification (2026-10-14 UTC)

- Full native Debian 13 / GCC 14.2 build succeeded with PipeWire, WSI, DRM,
  SDL, OpenVR, AVIF screenshots, input emulation and tests enabled.
- All 17 Gamescope Meson test suites passed, with zero skipped, failed or
  timed-out suites. The separate color-test executable also exited successfully.
- The actual binary loaded all 25 candidate and deployed-session Lua scripts;
  the session's explicit-sync compatibility script changed the convar from
  false to true when requested.
- Staged installation was verified separately from a real Arch package build.
  Cloud binaries include local dependency paths and are validation artifacts,
  not redistributable Arch package payloads.
- GPU startup remains blocked by the software driver's missing mandatory
  external-semaphore extension, as described below.

## Build and package compatibility

Pinned wlroots is now 0.20.2. Its minimum dependencies include Wayland 1.24,
wayland-protocols 1.47, libdrm 2.4.129, libxkbcommon 1.8 and pixman 0.46.
The package keeps the name `gamescope-sk`, PipeWire support, pinned fallback
submodules and the existing `cap_sys_nice=eip` install/upgrade hook. It adds
the required libei/Catch2 dependencies and runs the Gamescope test suite.

Publication must still follow the normal source tag → `honjow/sk-pkgbuild`
recipe → AUR → `SkorionOS/skorion-packages` build/repository chain. Generate
the Git source BLAKE2 checksum from the final tag's `git archive --format=tar`;
never publish a placeholder checksum or silently use a moving branch.

## Hardware acceptance still required

The cloud test machine has no DRM render device. Its software Vulkan driver
does not provide `VK_KHR_external_semaphore_fd`, so headless startup reaches
device selection and then fails the required-extension check. No render,
display, power-consumption or physical-input pass is claimed.

Before declaring device-level parity, check:

- Intel handheld rotation at all orientations, touch corners, screenshots,
  scaling, docking/undocking and persistent night/color adjustments.
- AMD LUT-only and full blend-transfer hardware, overlays, SDR/HDR transitions,
  Legion Go 2 software brightness and unknown-panel PQ opt-in.
- Steam UI HALFHZ enable/disable, return to games, 30/40/60/72 FPS limits,
  high-refresh/VRR overlays and idle power.
- DPMS sleep/wake, cold headless boot and repeated HDR hotplug.
- NVIDIA startup with the present-wait compatibility environment variable.
- Touchpad click/drag/lock/natural scroll and nested two-finger/touch-cancel
  behavior under the actual session.

The already-built 56-6 images remain on `3.16.23.5.sk1-1`; this candidate must
not be substituted into those existing image artifacts.
