#include <catch2/catch_test_macros.hpp>

#include <unordered_map>
#include <poll.h>

#include "waitable.h"

LogScope g_WaitableLog("waitable-test");

timespec nanos_to_timespec( uint64_t nanos )
{
    return timespec{ time_t(nanos / 1'000'000'000), long(nanos % 1'000'000'000) };
}

TEST_CASE("Expired timer functions drain their descriptor", "[waitable]")
{
    int callbacks = 0;
    gamescope::CTimerFunction timer([&] { ++callbacks; });
    timespec now{};
    REQUIRE(clock_gettime(CLOCK_MONOTONIC, &now) == 0);
    timer.ArmTimer(uint64_t(now.tv_sec) * 1'000'000'000 + now.tv_nsec + 1'000'000);
    pollfd event{timer.GetFD(), POLLIN, 0};
    REQUIRE(poll(&event, 1, 1000) == 1);
    timer.OnPollIn();
    REQUIRE(callbacks == 1);
    event.revents = 0;
    REQUIRE(poll(&event, 1, 0) == 0);
    // A repeated dispatch must remain non-blocking after consumption.
    timer.OnPollIn();
    REQUIRE(callbacks == 2);
    REQUIRE(poll(&event, 1, 0) == 0);
}
