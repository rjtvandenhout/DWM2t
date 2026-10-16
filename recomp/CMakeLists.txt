cmake_minimum_required(VERSION 3.24)

project(DWM2tRecomp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

set(REPO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/..")
set(BANKS_DIR "${REPO_ROOT}/src/banks")
set(BANK0_SOURCE "${BANKS_DIR}/bank_000.asm")
set(GENERATED_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated")

file(GLOB BANK_SOURCES CONFIGURE_DEPENDS "${BANKS_DIR}/bank_*.asm")

set(BANK0_CPP
    "${GENERATED_DIR}/bank0_master.cpp"
    "${GENERATED_DIR}/bank0_chunk_0.cpp"
    "${GENERATED_DIR}/bank0_chunk_1.cpp"
    "${GENERATED_DIR}/bank0_chunk_2.cpp"
    "${GENERATED_DIR}/bank0_chunk_3.cpp"
)

add_custom_command(
    OUTPUT ${BANK0_CPP}
    COMMAND "${CMAKE_COMMAND}" -E make_directory "${GENERATED_DIR}"
    COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tools/recompile_bank0.py"
            --bank "${BANK0_SOURCE}"
            --out-dir "${GENERATED_DIR}"
    DEPENDS
        "${BANK0_SOURCE}"
        "${CMAKE_CURRENT_SOURCE_DIR}/tools/lr35902.py"
        "${CMAKE_CURRENT_SOURCE_DIR}/tools/recompile_bank0.py"
    COMMENT "Static-recompiling all 16,384 fixed Bank 0 entry addresses"
    VERBATIM
)

# M5 starts with banks known to be on the CGB boot/title path. Missing-bank
# instrumentation in Runtime is authoritative when this set needs to expand.
set(NATIVE_ROMX_BANKS 1 2 4 7 18 20 22 23 31 52 53 96 127 132)
set(BANK_FILE_1 "bank_001.asm")
set(BANK_FILE_2 "bank_002.asm")
set(BANK_FILE_4 "bank_004.asm")
set(BANK_FILE_7 "bank_007.asm")
set(BANK_FILE_18 "bank_018.asm")
set(BANK_FILE_20 "bank_020.asm")
set(BANK_FILE_22 "bank_022.asm")
set(BANK_FILE_23 "bank_023.asm")
set(BANK_FILE_31 "bank_031.asm")
set(BANK_FILE_52 "bank_052.asm")
set(BANK_FILE_53 "bank_053.asm")
set(BANK_FILE_96 "bank_096.asm")
set(BANK_FILE_127 "bank_127.asm")
set(BANK_FILE_132 "bank_132.asm")

set(ROMX_CPP)
foreach(BANK IN LISTS NATIVE_ROMX_BANKS)
    set(BANK_SOURCE "${BANKS_DIR}/${BANK_FILE_${BANK}}")
    set(BANK_OUTPUTS
        "${GENERATED_DIR}/romx_bank_${BANK}_master.cpp"
        "${GENERATED_DIR}/romx_bank_${BANK}_chunk_0.cpp"
        "${GENERATED_DIR}/romx_bank_${BANK}_chunk_1.cpp"
        "${GENERATED_DIR}/romx_bank_${BANK}_chunk_2.cpp"
        "${GENERATED_DIR}/romx_bank_${BANK}_chunk_3.cpp"
    )

    add_custom_command(
        OUTPUT ${BANK_OUTPUTS}
        COMMAND "${CMAKE_COMMAND}" -E make_directory "${GENERATED_DIR}"
        COMMAND "${Python3_EXECUTABLE}"
                "${CMAKE_CURRENT_SOURCE_DIR}/tools/recompile_romx_bank.py"
                --bank "${BANK_SOURCE}"
                --bank-number "${BANK}"
                --out-dir "${GENERATED_DIR}"
        DEPENDS
            "${BANK_SOURCE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tools/lr35902.py"
            "${CMAKE_CURRENT_SOURCE_DIR}/tools/recompile_romx_bank.py"
        COMMENT "Static-recompiling switchable ROM Bank ${BANK}"
        VERBATIM
    )
    list(APPEND ROMX_CPP ${BANK_OUTPUTS})
endforeach()

set(ROMX_DISPATCH_CPP "${GENERATED_DIR}/romx_dispatch.cpp")
add_custom_command(
    OUTPUT "${ROMX_DISPATCH_CPP}"
    COMMAND "${CMAKE_COMMAND}" -E make_directory "${GENERATED_DIR}"
    COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tools/generate_romx_dispatch.py"
            --banks ${NATIVE_ROMX_BANKS}
            --out "${ROMX_DISPATCH_CPP}"
    DEPENDS
        ${ROMX_CPP}
        "${CMAKE_CURRENT_SOURCE_DIR}/tools/generate_romx_dispatch.py"
    COMMENT "Generating native ROMX bank registry"
    COMMAND_EXPAND_LISTS
    VERBATIM
)

set(ROM_IMAGE_CPP "${GENERATED_DIR}/rom_image.cpp")
add_custom_command(
    OUTPUT "${ROM_IMAGE_CPP}"
    COMMAND "${CMAKE_COMMAND}" -E make_directory "${GENERATED_DIR}"
    COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tools/generate_rom_image.py"
            --banks-dir "${BANKS_DIR}"
            --out "${ROM_IMAGE_CPP}"
    DEPENDS
        ${BANK_SOURCES}
        "${CMAKE_CURRENT_SOURCE_DIR}/tools/generate_rom_image.py"
    COMMENT "Embedding the exact 4 MiB matching ROM image from source banks"
    VERBATIM
)

add_executable(DWM2tRecomp
    src/main.cpp
    src/m6.cpp
    src/memory.cpp
    src/runtime.cpp
    src/hram_exec.cpp
    src/renderer.cpp
    src/window.cpp
    ${BANK0_CPP}
    ${ROMX_CPP}
    "${ROMX_DISPATCH_CPP}"
    "${ROM_IMAGE_CPP}"
)

target_include_directories(DWM2tRecomp PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/include"
)

if(MSVC)
    target_compile_options(DWM2tRecomp PRIVATE /W4 /permissive- /O1 /bigobj /MP4)
else()
    target_compile_options(DWM2tRecomp PRIVATE -Wall -Wextra -Wpedantic -O1)
endif()

if(WIN32)
    target_link_libraries(DWM2tRecomp PRIVATE user32 gdi32)
endif()
