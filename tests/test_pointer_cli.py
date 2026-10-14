#!/usr/bin/env python3
"""Exercise the real option table without starting a display or a Vulkan device."""

import subprocess
import sys


def check(binary, args, success=True):
    result = subprocess.run(
        [binary, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10
    )
    if (result.returncode == 0) != success:
        raise AssertionError(
            f"{args!r}: exit {result.returncode}\n{result.stdout}{result.stderr}"
        )
    output = result.stdout + result.stderr
    if success and "--help" in args and "usage: gamescope" not in output:
        raise AssertionError(f"{args!r}: --help was not reached\n{output}")
    return output


def main():
    binary = sys.argv[1]
    help_text = check(binary, ["--help"])
    for option in (
        "tap-to-click", "tap-and-drag", "tap-to-drag", "drag-lock", "natural-scrolling"
    ):
        if f"--{option}" not in help_text:
            raise AssertionError(f"--{option} is missing from --help")

    # Put --help last: putting it first would skip parsing the options under test.
    for drag_option in ("--tap-and-drag", "--tap-to-drag"):
        check(binary, [drag_option, "--help"])
        for selector in ("none", "touchpad", "mouse", "all"):
            for scrolling_args in (
                ["--natural-scrolling", selector],
                [f"--natural-scrolling={selector}"],
            ):
                check(binary, ["--tap-to-click", drag_option, "--drag-lock", *scrolling_args, "--help"])

    check(binary, ["--tap-and-drag", "--tap-to-drag", "--help"])

    # honjow/gamescope-session c7f5f5256823983fa277ca34b860161d77b83e91
    # emits the rotation value as a separate argument. Also test the joined
    # spelling to reject accidentally declaring rotation as a no-argument flag.
    check(binary, [
        "--use-rotation-shader", "1", "--force-orientation", "left",
        "--custom-refresh-rates", "60,144", "--tap-to-click", "--tap-and-drag",
        "--drag-lock", "--natural-scrolling", "touchpad",
        "--hdr-pq-internal-enable", "--help",
    ])
    check(binary, ["--use-rotation-shader=1", "--help"])
    check(binary, ["--use-rotation-shader=0", "--help"])
    check(binary, ["--natural-scrolling"], success=False)
    check(binary, ["--tap-and-drag=invalid", "--help"], success=False)
    check(binary, ["--tap-to-drag=invalid", "--help"], success=False)


if __name__ == "__main__":
    main()
