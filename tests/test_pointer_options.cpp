#include <catch2/catch_test_macros.hpp>

#include "main.hpp"

TEST_CASE("Both tap-and-drag spellings reach the same handler", "[pointer_options]") {
    REQUIRE( IsTapAndDragOption( "tap-and-drag" ) );
    REQUIRE( IsTapAndDragOption( "tap-to-drag" ) );
    REQUIRE_FALSE( IsTapAndDragOption( "tap-to-click" ) );
    REQUIRE_FALSE( IsTapAndDragOption( "drag-lock" ) );
}

TEST_CASE("Natural scrolling preserves the session's four device selectors", "[pointer_options]") {
    REQUIRE( ParseSelectedPointerType( "none" ) == SelectedPointerType::NONE );
    REQUIRE( ParseSelectedPointerType( "touchpad" ) == SelectedPointerType::TOUCHPAD );
    REQUIRE( ParseSelectedPointerType( "mouse" ) == SelectedPointerType::MOUSE );
    REQUIRE( ParseSelectedPointerType( "all" ) == SelectedPointerType::ALL );
    REQUIRE( ParseSelectedPointerType( "" ) == SelectedPointerType::NONE );
    REQUIRE( ParseSelectedPointerType( "unknown" ) == SelectedPointerType::NONE );
}

TEST_CASE("Natural scrolling applies only to the selected pointer devices", "[pointer_options]") {
    for ( bool bIsTouchpad : { false, true } ) {
        REQUIRE_FALSE( NaturalScrollingEnabled( SelectedPointerType::NONE, bIsTouchpad ) );
        REQUIRE( NaturalScrollingEnabled( SelectedPointerType::ALL, bIsTouchpad ) );
        REQUIRE( NaturalScrollingEnabled( SelectedPointerType::TOUCHPAD, bIsTouchpad ) == bIsTouchpad );
        REQUIRE( NaturalScrollingEnabled( SelectedPointerType::MOUSE, bIsTouchpad ) == !bIsTouchpad );
    }
}
