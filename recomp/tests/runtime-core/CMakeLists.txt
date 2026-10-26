cmake_minimum_required(VERSION 3.24)
project(DWM2tRuntimeCoreContracts LANGUAGES CXX)

# Independent host hardware contracts. Do not add_subdirectory(recomp): that
# would compile the complete original-ROM AOT executable for these unit checks.
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
get_filename_component(CORE "${CMAKE_CURRENT_SOURCE_DIR}/../.." ABSOLUTE)
find_package(Python3 REQUIRED COMPONENTS Interpreter)

add_executable(DWM2tRuntimeCoreContracts
    runtime_core_contracts.cpp
    stub_dispatch.cpp
    "${CORE}/src/memory.cpp"
    "${CORE}/src/apu.cpp"
    "${CORE}/src/runtime.cpp"
    "${CORE}/src/hram_exec.cpp")

add_executable(DWM2tRendererContracts
    renderer_contracts.cpp
    "${CORE}/src/renderer.cpp"
    "${CORE}/src/memory.cpp"
    "${CORE}/src/apu.cpp")

set(FIXTURE_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated-fixtures")
set(FIXTURE_SOURCES
    "${FIXTURE_DIR}/fixture_bank0_master.cpp"
    "${FIXTURE_DIR}/fixture_bank0_chunks.cpp"
    "${FIXTURE_DIR}/fixture_bank1_master.cpp"
    "${FIXTURE_DIR}/fixture_bank1_chunks.cpp"
    "${FIXTURE_DIR}/fixture_rom_image.cpp"
    "${FIXTURE_DIR}/fixture_romx_dispatch.cpp")
add_custom_command(
    OUTPUT ${FIXTURE_SOURCES} "${FIXTURE_DIR}/fixture-source.json"
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/generate_aot_contract_fixtures.py"
            --output "${FIXTURE_DIR}"
    COMMAND "${Python3_EXECUTABLE}" "${CORE}/tools/generate_romx_dispatch.py"
            --banks 1 --out "${FIXTURE_DIR}/fixture_romx_dispatch.cpp"
    DEPENDS
        "${CMAKE_CURRENT_SOURCE_DIR}/generate_aot_contract_fixtures.py"
        "${CORE}/tools/recompile_bank0.py"
        "${CORE}/tools/recompile_romx_bank.py"
        "${CORE}/tools/generate_romx_dispatch.py"
        "${CORE}/tools/lr35902.py"
    COMMENT "Generating sparse synthetic CPU contracts with production AOT emitters"
    VERBATIM)
add_executable(DWM2tGeneratedAotContracts
    generated_aot_contracts.cpp
    ${FIXTURE_SOURCES}
    "${CORE}/src/memory.cpp"
    "${CORE}/src/apu.cpp"
    "${CORE}/src/runtime.cpp"
    "${CORE}/src/hram_exec.cpp")

foreach(TARGET DWM2tRuntimeCoreContracts DWM2tRendererContracts DWM2tGeneratedAotContracts)
    target_include_directories(${TARGET} PRIVATE "${CORE}/include")
    if(MSVC)
        target_compile_options(${TARGET} PRIVATE /W4 /permissive- /utf-8)
        target_link_options(${TARGET} PRIVATE /STACK:8388608)
    else()
        target_compile_options(${TARGET} PRIVATE -Wall -Wextra -Wpedantic)
    endif()
endforeach()

include(CTest)
foreach(GROUP memory runtime serial)
    add_test(NAME FullROM_${GROUP}_contracts
        COMMAND DWM2tRuntimeCoreContracts "${GROUP}"
                "${CMAKE_CURRENT_BINARY_DIR}/evidence/${GROUP}")
    set_tests_properties(FullROM_${GROUP}_contracts PROPERTIES TIMEOUT 30)
endforeach()
add_test(NAME FullROM_renderer_contracts
    COMMAND DWM2tRendererContracts "${CMAKE_CURRENT_BINARY_DIR}/renderer-evidence")
set_tests_properties(FullROM_renderer_contracts PROPERTIES TIMEOUT 30)
add_test(NAME FullROM_generated_aot_contracts
    COMMAND DWM2tGeneratedAotContracts "${CMAKE_CURRENT_BINARY_DIR}/generated-aot-evidence")
set_tests_properties(FullROM_generated_aot_contracts PROPERTIES TIMEOUT 30)
