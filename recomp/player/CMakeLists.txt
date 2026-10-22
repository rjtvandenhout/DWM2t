cmake_minimum_required(VERSION 3.24)

# Independent production entry point. Keep the historical diagnostic executable
# and every retained acceptance gate unchanged in the parent project.
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>" CACHE STRING "Static MSVC runtime")
project(DWM2tPlayer LANGUAGES CXX)
if(NOT WIN32)
    message(FATAL_ERROR "DWM2tPlayer currently targets Windows x64")
endif()
if(NOT CMAKE_SIZEOF_VOID_P EQUAL 8)
    message(FATAL_ERROR "Configure the player for x64, not Win32")
endif()
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(BUILD_TESTING OFF CACHE BOOL "Tests are deferred in the production build" FORCE)
set(DWM2T_ALL_ROMX ON CACHE BOOL "The player requires all 255 ROMX banks" FORCE)
set(DWM2T_SOURCE_REVISION "unknown" CACHE STRING "Pinned source commit recorded by the builder")
if(NOT DWM2T_SOURCE_REVISION STREQUAL "unknown")
    string(LENGTH "${DWM2T_SOURCE_REVISION}" REVISION_LENGTH)
    if(NOT REVISION_LENGTH EQUAL 40 OR NOT DWM2T_SOURCE_REVISION MATCHES "^[0-9a-f]+$")
        message(FATAL_ERROR "DWM2T_SOURCE_REVISION must be a full lowercase Git SHA")
    endif()
endif()
set(CORE_SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/..")
# The core diagnostic target exists, but is not a dependency of DWM2tPlayer.
add_subdirectory("${CORE_SOURCE}" "core" EXCLUDE_FROM_ALL)
find_package(Python3 REQUIRED COMPONENTS Interpreter)
set(PLAYER_BANKS)
set(PLAYER_LIBRARIES dwm2t_bank0 dwm2t_rom_image)
foreach(BANK RANGE 1 255)
    list(APPEND PLAYER_BANKS ${BANK})
    list(APPEND PLAYER_LIBRARIES dwm2t_romx_bank_${BANK})
endforeach()
set(PLAYER_DISPATCH "${CMAKE_CURRENT_BINARY_DIR}/generated/player_romx_dispatch.cpp")
add_custom_command(
    OUTPUT "${PLAYER_DISPATCH}"
    COMMAND "${Python3_EXECUTABLE}" "${CORE_SOURCE}/tools/generate_romx_dispatch.py"
            --banks ${PLAYER_BANKS} --out "${PLAYER_DISPATCH}"
    DEPENDS "${CORE_SOURCE}/tools/generate_romx_dispatch.py"
    COMMENT "Generating the complete native player bank registry"
    COMMAND_EXPAND_LISTS VERBATIM
)
add_executable(DWM2tPlayer
    "${CORE_SOURCE}/src/player_main.cpp"
    "${CORE_SOURCE}/src/apu.cpp"
    "${CORE_SOURCE}/src/memory.cpp"
    "${CORE_SOURCE}/src/runtime.cpp"
    "${CORE_SOURCE}/src/hram_exec.cpp"
    "${CORE_SOURCE}/src/renderer.cpp"
    "${CORE_SOURCE}/src/window.cpp"
    "${PLAYER_DISPATCH}"
)
set_target_properties(DWM2tPlayer PROPERTIES OUTPUT_NAME DWM2tRecomp)
target_include_directories(DWM2tPlayer PRIVATE "${CORE_SOURCE}/include")
target_compile_definitions(DWM2tPlayer PRIVATE NOMINMAX
    DWM2T_SOURCE_REVISION="${DWM2T_SOURCE_REVISION}")
target_link_libraries(DWM2tPlayer PRIVATE ${PLAYER_LIBRARIES} user32 gdi32 winmm)
if(MSVC)
    target_compile_options(DWM2tPlayer PRIVATE /W4 /permissive- /O1 /bigobj /utf-8)
    target_link_options(DWM2tPlayer PRIVATE /STACK:8388608)
else()
    target_compile_options(DWM2tPlayer PRIVATE -Wall -Wextra -Wpedantic -O1)
    target_link_options(DWM2tPlayer PRIVATE -municode)
endif()
message(STATUS "M8 PLAYER: complete AOT; tests NOT RUN; full-game acceptance pending")
