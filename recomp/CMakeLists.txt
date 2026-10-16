cmake_minimum_required(VERSION 3.24)

project(DWM2tRecomp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

function(configure_native_target TARGET_NAME)
    target_include_directories(${TARGET_NAME} PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/include"
    )
    if(MSVC)
        target_compile_options(${TARGET_NAME} PRIVATE /W4 /permissive- /O1 /bigobj /MP4)
    else()
        target_compile_options(${TARGET_NAME} PRIVATE -Wall -Wextra -Wpedantic -O1)
    endif()
endfunction()

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

add_library(dwm2t_bank0 STATIC ${BANK0_CPP})
configure_native_target(dwm2t_bank0)

# M5 starts with banks known to be on the CGB boot/title path. Missing-bank
# instrumentation in Runtime is authoritative when this set needs to expand.
set(NATIVE_ROMX_BANKS 1 2 4 7 10 15 16 17 18 19 20 22 23 31 37 38 40 52 53 95 96 105 127 132 133 135 161)
set(BANK_FILE_1 "bank_001.asm")
set(BANK_FILE_2 "bank_002.asm")
set(BANK_FILE_4 "bank_004.asm")
set(BANK_FILE_7 "bank_007.asm")
set(BANK_FILE_10 "bank_010.asm")
set(BANK_FILE_15 "bank_015.asm")
set(BANK_FILE_16 "bank_016.asm")
set(BANK_FILE_17 "bank_017.asm")
set(BANK_FILE_18 "bank_018.asm")
set(BANK_FILE_19 "bank_019.asm")
set(BANK_FILE_20 "bank_020.asm")
set(BANK_FILE_22 "bank_022.asm")
set(BANK_FILE_23 "bank_023.asm")
set(BANK_FILE_31 "bank_031.asm")
set(BANK_FILE_37 "bank_037.asm")
set(BANK_FILE_38 "bank_038.asm")
set(BANK_FILE_40 "bank_040.asm")
set(BANK_FILE_52 "bank_052.asm")
set(BANK_FILE_53 "bank_053.asm")
set(BANK_FILE_95 "bank_095.asm")
set(BANK_FILE_96 "bank_096.asm")
set(BANK_FILE_105 "bank_105.asm")
set(BANK_FILE_127 "bank_127.asm")
set(BANK_FILE_132 "bank_132.asm")
set(BANK_FILE_133 "bank_133.asm")
set(BANK_FILE_135 "bank_135.asm")
set(BANK_FILE_161 "bank_161.asm")

set(ROMX_CPP)
set(ROMX_TARGETS)
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

    set(BANK_TARGET "dwm2t_romx_bank_${BANK}")
    add_library(${BANK_TARGET} STATIC ${BANK_OUTPUTS})
    configure_native_target(${BANK_TARGET})

    list(APPEND ROMX_TARGETS ${BANK_TARGET})
    list(APPEND ROMX_CPP ${BANK_OUTPUTS})
endforeach()

# During M6 discovery, compile only the newest required bank before relinking.
set(M6_DISCOVERY_BANK 17)
add_custom_target(m6_discovery_bank)
add_dependencies(m6_discovery_bank dwm2t_romx_bank_${M6_DISCOVERY_BANK})

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

add_library(dwm2t_rom_image STATIC "${ROM_IMAGE_CPP}")
configure_native_target(dwm2t_rom_image)

add_executable(DWM2tRecomp
    src/apu.cpp
    src/main.cpp
    src/m6.cpp
    src/m7.cpp
    src/memory.cpp
    src/runtime.cpp
    src/hram_exec.cpp
    src/renderer.cpp
    src/window.cpp
    "${ROMX_DISPATCH_CPP}"
)

configure_native_target(DWM2tRecomp)

target_link_libraries(DWM2tRecomp PRIVATE
    dwm2t_bank0
    dwm2t_rom_image
    ${ROMX_TARGETS}
)

if(WIN32)
    target_link_libraries(DWM2tRecomp PRIVATE user32 gdi32 winmm)
endif()
