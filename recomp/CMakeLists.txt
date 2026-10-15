cmake_minimum_required(VERSION 3.24)

project(DWM2tRecomp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

set(REPO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/..")
set(BANKS_DIR "${REPO_ROOT}/src/banks")
set(BANK0_SOURCE "${BANKS_DIR}/bank_000.asm")
set(BANK2_SOURCE "${BANKS_DIR}/bank_002.asm")
set(GENERATED_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated")

file(GLOB BANK_SOURCES CONFIGURE_DEPENDS "${BANKS_DIR}/bank_*.asm")

set(BANK0_CPP
    "${GENERATED_DIR}/bank0_master.cpp"
    "${GENERATED_DIR}/bank0_chunk_0.cpp"
    "${GENERATED_DIR}/bank0_chunk_1.cpp"
    "${GENERATED_DIR}/bank0_chunk_2.cpp"
    "${GENERATED_DIR}/bank0_chunk_3.cpp"
)

set(BANK2_CPP
    "${GENERATED_DIR}/romx_bank_2_master.cpp"
    "${GENERATED_DIR}/romx_bank_2_chunk_0.cpp"
    "${GENERATED_DIR}/romx_bank_2_chunk_1.cpp"
    "${GENERATED_DIR}/romx_bank_2_chunk_2.cpp"
    "${GENERATED_DIR}/romx_bank_2_chunk_3.cpp"
)

set(ROM_IMAGE_CPP "${GENERATED_DIR}/rom_image.cpp")

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

add_custom_command(
    OUTPUT ${BANK2_CPP}
    COMMAND "${CMAKE_COMMAND}" -E make_directory "${GENERATED_DIR}"
    COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tools/recompile_romx_bank.py"
            --bank "${BANK2_SOURCE}"
            --bank-number 2
            --out-dir "${GENERATED_DIR}"
    DEPENDS
        "${BANK2_SOURCE}"
        "${CMAKE_CURRENT_SOURCE_DIR}/tools/lr35902.py"
        "${CMAKE_CURRENT_SOURCE_DIR}/tools/recompile_romx_bank.py"
    COMMENT "Static-recompiling switchable ROM Bank 2"
    VERBATIM
)

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
    src/memory.cpp
    src/runtime.cpp
    src/renderer.cpp
    src/window.cpp
    ${BANK0_CPP}
    ${BANK2_CPP}
    "${ROM_IMAGE_CPP}"
)

target_include_directories(DWM2tRecomp PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/include"
)

if(MSVC)
    target_compile_options(DWM2tRecomp PRIVATE /W4 /permissive- /O1 /bigobj)
else()
    target_compile_options(DWM2tRecomp PRIVATE -Wall -Wextra -Wpedantic -O1)
endif()

if(WIN32)
    target_link_libraries(DWM2tRecomp PRIVATE user32 gdi32)
endif()
