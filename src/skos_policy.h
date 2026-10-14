#pragma once

#include <charconv>
#include <cstdint>
#include <optional>
#include <string_view>
#include <utility>
#include <vector>

namespace gamescope
{
    // Keep the established session syntax (including ordered duplicates), but
    // reject invalid or unbounded ranges instead of wrapping or hanging.
    inline std::optional<std::vector<uint32_t>> ParseCustomRefreshRates( std::string_view value )
    {
        std::vector<uint32_t> rates;
        auto parseRate = []( std::string_view token ) -> std::optional<uint32_t>
        {
            while ( !token.empty() && token.front() == ' ' ) token.remove_prefix( 1 );
            while ( !token.empty() && token.back() == ' ' ) token.remove_suffix( 1 );
            uint32_t rate = 0;
            const auto result = std::from_chars( token.data(), token.data() + token.size(), rate );
            if ( token.empty() || result.ec != std::errc{} || result.ptr != token.data() + token.size() || rate == 0 || rate > 10'000 )
                return std::nullopt;
            return rate;
        };
        if ( value.empty() ) return std::nullopt;
        while ( true )
        {
            const auto comma = value.find( ',' );
            const auto token = value.substr( 0, comma );
            const auto dash = token.find( '-' );
            const auto first = parseRate( token.substr( 0, dash ) );
            const auto last = dash == std::string_view::npos ? first : parseRate( token.substr( dash + 1 ) );
            if ( !first || !last || *last < *first || rates.size() + ( *last - *first + 1 ) > 10'000 )
                return std::nullopt;
            for ( uint32_t rate = *first; rate <= *last; ++rate ) rates.push_back( rate );
            if ( comma == std::string_view::npos ) break;
            value.remove_prefix( comma + 1 );
        }
        return rates;
    }

    inline std::pair<int, bool> SteamUIFrameLimit( bool enabled, bool steamFocused, int refreshHz, int requestedFPS )
    {
        if ( enabled && steamFocused && refreshHz > 100 && ( requestedFPS > 50 || requestedFPS == 0 ) )
            return { refreshHz / 2, true };
        return { requestedFPS, false };
    }

    inline uint64_t VerticalFrontPorchNS( uint32_t vdisplay, uint32_t vsyncStart, uint32_t vtotal, int32_t refreshMilliHz )
    {
        if ( refreshMilliHz <= 0 || vtotal == 0 || vsyncStart < vdisplay || vsyncStart > vtotal )
            return 0;
        return uint64_t( vsyncStart - vdisplay ) * 1'000'000'000'000ull / uint32_t( refreshMilliHz ) / vtotal;
    }

    inline bool DisplayShouldSleep( bool configuredSleep, bool dpms )
    {
        return configuredSleep || dpms;
    }
}
