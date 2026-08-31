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
    add_executable(dodge_magma WIN32 "dodge_the_magma_desktop_cpp.cpp" "EOSManager.cpp" "LanManager.cpp")
else()
    add_executable(dodge_magma "dodge_the_magma_desktop_cpp.cpp" "EOSManager.cpp" "LanManager.cpp")
endif()

# Setup EOS SDK Paths
set(EOS_SDK_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../third-party-api/eos-sdk/SDK")
target_include_directories(dodge_magma PRIVATE "${EOS_SDK_DIR}/Include")

if (WIN32)
    target_link_libraries(dodge_magma PRIVATE raylib "${EOS_SDK_DIR}/Lib/EOSSDK-Win64-Shipping.lib")
elseif(APPLE)
    target_link_libraries(dodge_magma PRIVATE raylib "${EOS_SDK_DIR}/Bin/libEOSSDK-Mac-Shipping.dylib")
else()
    target_link_libraries(dodge_magma PRIVATE raylib "${EOS_SDK_DIR}/Bin/libEOSSDK-Linux-Shipping.so")
endif()

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
    target_link_libraries(dodge_magma PRIVATE winmm gdi32 opengl32 ws2_32)
elseif (UNIX)
    target_link_libraries(dodge_magma PRIVATE GL m pthread dl rt X11)
endif()

# Copy save.txt cùng thư mục với exe khi chạy từ IDE (tuỳ chọn)
set_target_properties(dodge_magma PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)

# Copy EOS SDK binaries to output directory so the executable can find them
if (WIN32)
    add_custom_command(TARGET dodge_magma POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${EOS_SDK_DIR}/Bin/EOSSDK-Win64-Shipping.dll"
        $<TARGET_FILE_DIR:dodge_magma>
    )
elseif(APPLE)
    add_custom_command(TARGET dodge_magma POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${EOS_SDK_DIR}/Bin/libEOSSDK-Mac-Shipping.dylib"
        $<TARGET_FILE_DIR:dodge_magma>
    )
else()
    add_custom_command(TARGET dodge_magma POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${EOS_SDK_DIR}/Bin/libEOSSDK-Linux-Shipping.so"
        $<TARGET_FILE_DIR:dodge_magma>
    )
endif()
