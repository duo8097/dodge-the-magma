```cmake
cmake_minimum_required(VERSION 3.15)
project(DodgeTheMagma CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ------------------------------------------------------------
# raylib: use system installation if available, otherwise
# download and build with FetchContent.
# ------------------------------------------------------------
find_package(raylib 6.0 QUIET)

if (NOT raylib_FOUND)
    include(FetchContent)

    set(FETCHCONTENT_QUIET FALSE)

    FetchContent_Declare(
        raylib
        GIT_REPOSITORY https://github.com/raysan5/raylib.git
        GIT_TAG        6.0
        GIT_SHALLOW    TRUE
    )

    # Don't build raylib examples/games.
    set(BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
    set(BUILD_GAMES    OFF CACHE BOOL "" FORCE)

    FetchContent_MakeAvailable(raylib)
endif()


# ------------------------------------------------------------
# Main game
#
# WIN32 is used only on Windows so the game uses the Windows
# GUI subsystem instead of the Console subsystem.
#
# Linux/macOS remain normal executables.
# ------------------------------------------------------------
if (WIN32)
    add_executable(dodge_magma WIN32
        dodge_the_magma_desktop_cpp.cpp
        LanManager.cpp
    )
else()
    add_executable(dodge_magma
        dodge_the_magma_desktop_cpp.cpp
        LanManager.cpp
    )
endif()

target_link_libraries(dodge_magma PRIVATE raylib)


# ------------------------------------------------------------
# Platform-specific libraries
# ------------------------------------------------------------
if (APPLE)

    target_link_libraries(dodge_magma PRIVATE
        "-framework IOKit"
        "-framework Cocoa"
        "-framework OpenGL"
    )

elseif (WIN32)

    target_link_libraries(dodge_magma PRIVATE
        winmm
        gdi32
        opengl32
        ws2_32
    )

elseif (UNIX)

    target_link_libraries(dodge_magma PRIVATE
        GL
        m
        pthread
        dl
        rt
        X11
    )

endif()


# ------------------------------------------------------------
# Put the executable in build/bin
# ------------------------------------------------------------
set_target_properties(dodge_magma PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)


# ─────────────────────────────────────────────────────────────────────────────
# Multiplayer test suite
#
# Build:
#   cd cpp/build
#   cmake .. -DBUILD_TESTS=ON
#   cmake --build . --target test_multiplayer
#
# Run:
#   ./bin/test_multiplayer
#
# The test binary uses only NetworkProvider.h + LanManager.cpp/.h,
# and a raw UDP socket on 127.0.0.1:45678 to simulate a peer.
# No raylib / no EOS credentials are required.
# ─────────────────────────────────────────────────────────────────────────────

option(BUILD_TESTS "Build multiplayer test suite" OFF)

if (BUILD_TESTS)

    add_executable(test_multiplayer
        tests/test_multiplayer.cpp
        LanManager.cpp
    )

    target_compile_options(test_multiplayer PRIVATE
        -O0
        -g
    )

    target_include_directories(test_multiplayer PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}"
    )

    if (WIN32)

        target_link_libraries(test_multiplayer PRIVATE
            ws2_32
        )

    elseif (UNIX)

        target_link_libraries(test_multiplayer PRIVATE
            pthread
        )

    endif()

    set_target_properties(test_multiplayer PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
    )

endif()
```
