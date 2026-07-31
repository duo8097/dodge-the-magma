cmake_minimum_required(VERSION 3.15)
project(DodgeTheMagma CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ------------------------------------------------------------
# raylib: dùng bản đã cài trong hệ thống nếu có, không thì tự
# tải về và build bằng FetchContent (cần internet lúc configure).
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
    # Không build ví dụ/game mẫu của raylib, chỉ build thư viện
    set(BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
    set(BUILD_GAMES    OFF CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(raylib)
endif()

if (WIN32)
    add_executable(dodge_magma WIN32 "dodge_the_magma_desktop_cpp.cpp")
else()
    add_executable(dodge_magma "dodge_the_magma_desktop_cpp.cpp")
endif()
target_link_libraries(dodge_magma PRIVATE raylib)

# ------------------------------------------------------------
# Flags/link đặc thù theo hệ điều hành
# ------------------------------------------------------------
if (APPLE)
    target_link_libraries(dodge_magma PRIVATE
        "-framework IOKit"
        "-framework Cocoa"
        "-framework OpenGL"
    )
elseif (WIN32)
    target_link_libraries(dodge_magma PRIVATE winmm gdi32 opengl32)
elseif (UNIX)
    target_link_libraries(dodge_magma PRIVATE GL m pthread dl rt X11)
endif()

# Copy save.txt cùng thư mục với exe khi chạy từ IDE (tuỳ chọn)
set_target_properties(dodge_magma PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)
