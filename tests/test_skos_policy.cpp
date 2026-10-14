#include "skos_policy.h"

#include <cstdlib>
#include <iostream>

#define CHECK( ... ) do { if ( !( __VA_ARGS__ ) ) { std::cerr << "Failed line " << __LINE__ << ": " << #__VA_ARGS__ << '\n'; return EXIT_FAILURE; } } while ( false )

int main()
{
    using namespace gamescope;
    CHECK( ParseCustomRefreshRates( "60,60,90,110-112" ) == std::vector<uint32_t>({60,60,90,110,111,112}) );
    CHECK( ParseCustomRefreshRates( " 40 - 42 , 60 " ) == std::vector<uint32_t>({40,41,42,60}) );
    CHECK( ParseCustomRefreshRates( "1-10000" )->size() == 10000 );
    for ( auto input : {"", "0", "-1", "120-60", "60,", ",60", "60,,90", "60Hz", "foo", "1-4294967295", "4294967296", "1-10000,60", "60-90-120"} )
        CHECK( !ParseCustomRefreshRates( input ) );

    CHECK( SteamUIFrameLimit( true, true, 120, 0 ) == std::pair<int, bool>(60, true) );
    CHECK( SteamUIFrameLimit( true, true, 144, 60 ) == std::pair<int, bool>(72, true) );
    CHECK( SteamUIFrameLimit( true, true, 120, 40 ) == std::pair<int, bool>(40, false) );
    CHECK( SteamUIFrameLimit( true, true, 100, 0 ) == std::pair<int, bool>(0, false) );
    CHECK( SteamUIFrameLimit( false, true, 144, 0 ) == std::pair<int, bool>(0, false) );
    CHECK( SteamUIFrameLimit( true, false, 144, 0 ) == std::pair<int, bool>(0, false) );

    CHECK( VerticalFrontPorchNS(1080,1084,1125,60000) == 59259 );
    CHECK( VerticalFrontPorchNS(1080,1084,1125,59940) == 59318 );
    CHECK( VerticalFrontPorchNS(1080,1084,0,60000) == 0 );
    CHECK( VerticalFrontPorchNS(1080,1084,1125,0) == 0 );
    CHECK( VerticalFrontPorchNS(1080,1070,1125,60000) == 0 );
    CHECK( VerticalFrontPorchNS(1080,1200,1125,60000) == 0 );

    CHECK( !DisplayShouldSleep(false, false) );
    CHECK( DisplayShouldSleep(false, true) );
    CHECK( DisplayShouldSleep(true, false) );
    CHECK( DisplayShouldSleep(true, true) );
    std::cout << "SKOS refresh, Steam UI limiter, porch and DPMS policy tests passed\n";
}
