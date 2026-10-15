cmake_minimum_required(VERSION 3.24)

project(DWM2tRecomp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

set(REPO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/..")
set(BANK0_SOURCE "${REPO_ROOT}/src/banks/bank_000.asm")
set(GENERATED_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated")
set(GENERATED_CPP "${GENERATED_DIR}/recompiled_bank0_smoke.cpp")

add_custom_command(
    OUTPUT "${GENERATED_CPP}"
    COMMAND "${CMAKE_COMMAND}" -E make_directory "${GENERATED_DIR}"
    COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tools/recompile_smoke.py"
            --bank "${BANK0_SOURCE}"
            --out "${GENERATED_CPP}"
    DEPENDS
        "${BANK0_SOURCE}"
        "${CMAKE_CURRENT_SOURCE_DIR}/tools/recompile_smoke.py"
    COMMENT "Static-recompiling verified LR35902 Bank 0 routines to C++"
    VERBATIM
)

add_executable(DWM2tRecomp
    src/main.cpp
    src/memory.cpp
    "${GENERATED_CPP}"
)

target_include_directories(DWM2tRecomp PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/include"
)

if(MSVC)
    target_compile_options(DWM2tRecomp PRIVATE /W4 /permissive-)
else()
    target_compile_options(DWM2tRecomp PRIVATE -Wall -Wextra -Wpedantic)
endif()
