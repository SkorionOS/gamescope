#pragma once

#include <getopt.h>

#include <atomic>
#include <optional>
#include <string_view>
#include <utility>

#include "gamescope_shared.h"
#include <vector>

extern const char *gamescope_optstring;
extern const struct option *gamescope_options;

extern std::atomic< bool > g_bRun;

extern int g_nNestedWidth;
extern int g_nNestedHeight;
extern int g_nNestedRefresh; // mHz
extern int g_nNestedUnfocusedRefresh; // mHz
extern int g_nNestedDisplayIndex;

extern uint32_t g_nOutputWidth;
extern uint32_t g_nOutputHeight;
extern bool g_bForceRelativeMouse;
extern int g_nOutputRefresh; // mHz
extern long g_nsVsync;       // ns
extern bool g_bOutputHDREnabled;
extern bool g_bEnableInternalPq;
extern bool g_bForceInternal;

extern bool g_bForceCompositionRotation;
extern uint32_t g_uOutputRotation;

extern bool g_bFullscreen;

extern bool g_bGrabbed;

extern float g_mouseSensitivity;
extern const char *g_sOutputName;
extern std::vector<uint32_t> g_customRefreshRates;

enum class GamescopeUpscaleFilter : uint32_t
{
    LINEAR = 0,
    NEAREST,
    FSR,
    NIS,
    PIXEL,
    SGSR,

    FROM_VIEW = 0xF, // internal
};

static constexpr bool UpscaleFilterUsesSharpness( GamescopeUpscaleFilter eFilter )
{
    return eFilter == GamescopeUpscaleFilter::FSR ||
           eFilter == GamescopeUpscaleFilter::NIS ||
           eFilter == GamescopeUpscaleFilter::SGSR;
}

// cs_sgsr reads the plain sampler slot, not the YCbCr one, and thresholds in 8-bit SDR units.
static constexpr bool SgsrSupportsInput( GamescopeAppTextureColorspace eColorspace, bool bYcbcr )
{
    return !bYcbcr && ( eColorspace == GAMESCOPE_APP_TEXTURE_COLORSPACE_LINEAR || eColorspace == GAMESCOPE_APP_TEXTURE_COLORSPACE_SRGB );
}

// Sharp ran FSR before SGSR existed, so HDR keeps that rather than losing the sharpening. Neither pre-pass reads the YCbCr slot.
static constexpr GamescopeUpscaleFilter ResolveUpscaleFilter( GamescopeUpscaleFilter eFilter, GamescopeAppTextureColorspace eColorspace, bool bYcbcr )
{
    if ( eFilter != GamescopeUpscaleFilter::SGSR || SgsrSupportsInput( eColorspace, bYcbcr ) )
        return eFilter;
    return bYcbcr ? GamescopeUpscaleFilter::LINEAR : GamescopeUpscaleFilter::FSR;
}

static constexpr bool DoesHardwareSupportUpscaleFilter( GamescopeUpscaleFilter eFilter )
{
    // Could do nearest someday... AMDGPU DC supports custom tap placement to an extent.

    return eFilter == GamescopeUpscaleFilter::LINEAR;
}

enum class GamescopeUpscaleScaler : uint32_t
{
    AUTO,
    INTEGER,
    FIT,
    FILL,
    STRETCH,
};

struct UpscaleSettings_t
{
    GamescopeUpscaleFilter eFilter{};
    GamescopeUpscaleScaler eScaler{};
    int nSharpness{};
};

// XXX(misyl): This is bad! We shouldnt change the upscaler like this at all!!!
// We should move this to business logic in paint_window or something!
static constexpr UpscaleSettings_t GetUpscaleSettings(
    bool bFocusIsSteam,
    GamescopeUpscaleFilter eWantedFilter,
    GamescopeUpscaleScaler eWantedScaler,
    int nWantedSharpness )
{
    if ( bFocusIsSteam )
        return UpscaleSettings_t{ GamescopeUpscaleFilter::LINEAR, GamescopeUpscaleScaler::FIT, nWantedSharpness };

    return UpscaleSettings_t{ eWantedFilter, eWantedScaler, nWantedSharpness };
}

// One name table for the --filter option and the scaling_filter command, so the two cannot drift.
inline std::optional<GamescopeUpscaleFilter> ParseUpscaleFilter( std::string_view svName )
{
    static constexpr std::pair<std::string_view, GamescopeUpscaleFilter> k_Filters[] =
    {
        { "linear",  GamescopeUpscaleFilter::LINEAR },
        { "nearest", GamescopeUpscaleFilter::NEAREST },
        { "fsr",     GamescopeUpscaleFilter::FSR },
        { "nis",     GamescopeUpscaleFilter::NIS },
        { "pixel",   GamescopeUpscaleFilter::PIXEL },
        { "sgsr",    GamescopeUpscaleFilter::SGSR },
    };
    for ( const auto &[svFilterName, eFilter] : k_Filters )
    {
        if ( svFilterName == svName )
            return eFilter;
    }
    return std::nullopt;
}

extern GamescopeUpscaleFilter g_wantedUpscaleFilter;
extern GamescopeUpscaleScaler g_wantedUpscaleScaler;
extern int g_upscaleFilterSharpness;

extern bool g_bBorderlessOutputWindow;

extern bool g_bExposeWayland;

extern bool g_bRt;

extern int g_nXWaylandCount;
extern bool g_bNoTouchPointerEmulation;

extern uint32_t g_preferVendorID;
extern uint32_t g_preferDeviceID;

enum class SelectedPointerType : uint32_t
{
    NONE,
    TOUCHPAD,
    MOUSE,
    ALL,
};

extern bool g_tapToClick;
extern bool g_tapAndDrag;
extern bool g_dragLock;
extern SelectedPointerType g_naturalScrolling;

// Keep both the session's spelling and the spelling shipped by older builds.
inline bool IsTapAndDragOption( std::string_view svName )
{
    return svName == "tap-and-drag" || svName == "tap-to-drag";
}

inline SelectedPointerType ParseSelectedPointerType( std::string_view svName )
{
    if ( svName == "all" )
        return SelectedPointerType::ALL;
    if ( svName == "touchpad" )
        return SelectedPointerType::TOUCHPAD;
    if ( svName == "mouse" )
        return SelectedPointerType::MOUSE;
    // Preserve the existing fallback for "none" and unrecognized values.
    return SelectedPointerType::NONE;
}

inline bool NaturalScrollingEnabled( SelectedPointerType eType, bool bIsTouchpad )
{
    return eType == SelectedPointerType::ALL ||
        ( eType == SelectedPointerType::TOUCHPAD && bIsTouchpad ) ||
        ( eType == SelectedPointerType::MOUSE && !bIsTouchpad );
}
