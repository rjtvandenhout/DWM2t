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
set(NATIVE_ROMX_BANKS 1 2 3 4 5 7 8 9 10 15 16 17 18 19 20 21 22 23 25 26 28 29 30 31 36 37 38 39 40 41 42 47 48 49 50 51 52 53 54 55 57 58 59 61 95 96 105 115 127 132 133 135 137 149 151 152 161 163 226 240)
set(BANK_FILE_1 "bank_001.asm")
set(BANK_FILE_2 "bank_002.asm")
# Reached at 3:$4015 by an original field-menu command after Slash joined.
set(BANK_FILE_3 "bank_003.asm")
set(BANK_FILE_4 "bank_004.asm")
# M8: direct unconditional target 5:$772B from reached dam boss code 226:$5426.
set(BANK_FILE_5 "bank_005.asm")
set(BANK_FILE_7 "bank_007.asm")
# Reached at 8:$4001 by the original Magic Door Use command.
set(BANK_FILE_8 "bank_008.asm")
# Reached at 9:$400F while the original PLAN menu initializes.
set(BANK_FILE_9 "bank_009.asm")
set(BANK_FILE_10 "bank_010.asm")
set(BANK_FILE_15 "bank_015.asm")
set(BANK_FILE_16 "bank_016.asm")
set(BANK_FILE_17 "bank_017.asm")
set(BANK_FILE_18 "bank_018.asm")
set(BANK_FILE_19 "bank_019.asm")
set(BANK_FILE_20 "bank_020.asm")
# Reached at 21:$63B8 by original PLAN > Journal.
set(BANK_FILE_21 "bank_021.asm")
set(BANK_FILE_22 "bank_022.asm")
set(BANK_FILE_23 "bank_023.asm")
# Unconditional battle initialization target 25:$4001 from reached 49:$4001.
set(BANK_FILE_25 "bank_025.asm")
# Reached at 26:$7276 during original Oasis battle initialization.
set(BANK_FILE_26 "bank_026.asm")
# M8: reached at 28:$4075 after the original inn welcome dialogue.
set(BANK_FILE_28 "bank_028.asm")
# Unconditional RST $10 target 29:$6973 from reached Journal entry 21:$63B8.
set(BANK_FILE_29 "bank_029.asm")
# M8: reached at 30:$7163 by original recruitment > send to farm > Info.
set(BANK_FILE_30 "bank_030.asm")
set(BANK_FILE_31 "bank_031.asm")
# M8: reached at 36:$60DB by the original Asiya church service menu.
set(BANK_FILE_36 "bank_036.asm")
set(BANK_FILE_37 "bank_037.asm")
set(BANK_FILE_38 "bank_038.asm")
# M8: reached at 39:$4001 after the original CurseLamp recruitment name offer.
set(BANK_FILE_39 "bank_039.asm")
set(BANK_FILE_40 "bank_040.asm")
# M8: reached at 41:$4001 by P1 conversation with the Oasis town innkeeper.
set(BANK_FILE_41 "bank_041.asm")
# M8: reached at 42:$4001 when facing Warubou after the Oasis return.
set(BANK_FILE_42 "bank_042.asm")
# Reached at 47:$4001 during original Oasis encounter presentation.
set(BANK_FILE_47 "bank_047.asm")
# Reached at 48:$4001 by the genuine battle Fight command through P1.
set(BANK_FILE_48 "bank_048.asm")
# Real original encounter reached via P1 in Oasis: C5DB=4, 49:$4001.
set(BANK_FILE_49 "bank_049.asm")
# Original action path: 49:$43D8 -> 58:$6157 -> 50:$4ADC / 54:$4001.
set(BANK_FILE_50 "bank_050.asm")
# Reached at 51:$4001 by the original PLAN menu after Slash joined.
set(BANK_FILE_51 "bank_051.asm")
set(BANK_FILE_52 "bank_052.asm")
set(BANK_FILE_53 "bank_053.asm")
set(BANK_FILE_54 "bank_054.asm")
# Reached at 55:$4001 by original Journal save dialogue.
set(BANK_FILE_55 "bank_055.asm")
# Reached at 57:$4001 after original battle Fight confirmation.
set(BANK_FILE_57 "bank_057.asm")
set(BANK_FILE_58 "bank_058.asm")
# M8: reached at 59:$40CD in the original Mirage Lake hideout battle.
set(BANK_FILE_59 "bank_059.asm")
# M8: reproduced at 61:$4001 by original battle ITEM > BeefJerky > Enemy.
set(BANK_FILE_61 "bank_061.asm")
set(BANK_FILE_95 "bank_095.asm")
set(BANK_FILE_96 "bank_096.asm")
set(BANK_FILE_105 "bank_105.asm")
# Reached at 115:$77CC by the original town-arrival quest scene via P1.
set(BANK_FILE_115 "bank_115.asm")
set(BANK_FILE_127 "bank_127.asm")
set(BANK_FILE_132 "bank_132.asm")
set(BANK_FILE_133 "bank_133.asm")
set(BANK_FILE_135 "bank_135.asm")
# M8: reached at 137:$4001 during the original Asiya king/circus story scene.
set(BANK_FILE_137 "bank_137.asm")
# M8: reached at 149:$4650 by the original party information menu in Asiya.
set(BANK_FILE_149 "bank_149.asm")
# M8: reached at 151:$4026 by the original Oasis inn dialogue via 41:$4008.
set(BANK_FILE_151 "bank_151.asm")
# M8: reached at 152:$404B in the original post-Oasis home-hub event.
set(BANK_FILE_152 "bank_152.asm")
set(BANK_FILE_161 "bank_161.asm")
# Reached at 163:$4187 after genuine battle Fight confirmation.
set(BANK_FILE_163 "bank_163.asm")
# M8: reached at 240:$4001 inside the original inn party-selection menu.
# M8: reached at 226:$5426 by the original dam-creature boss Fight command.
set(BANK_FILE_226 "bank_226.asm")
set(BANK_FILE_240 "bank_240.asm")

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
    src/m7_p1.cpp
    src/m7_acceptance.cpp
    src/m8.cpp
    src/memory.cpp
    src/runtime.cpp
    src/hram_exec.cpp
    src/renderer.cpp
    src/window.cpp
    "${ROMX_DISPATCH_CPP}"
)

configure_native_target(DWM2tRecomp)
set(DWM2T_OUTPUT_NAME "DWM2tRecomp" CACHE STRING "Executable basename for isolated local development builds")
set_target_properties(DWM2tRecomp PROPERTIES OUTPUT_NAME "${DWM2T_OUTPUT_NAME}")

target_link_libraries(DWM2tRecomp PRIVATE
    dwm2t_bank0
    dwm2t_rom_image
    ${ROMX_TARGETS}
)

if(WIN32)
    target_link_libraries(DWM2tRecomp PRIVATE user32 gdi32 winmm)
endif()


if(MSVC)
    # M7 diagnostic/search harnesses keep several 160x144 renderer snapshots
    # alive in nested scopes. Give the native test executable enough stack
    # without changing any emulated game state or cartridge execution.
    target_link_options(DWM2tRecomp PRIVATE /STACK:8388608)
endif()


if(MSVC)
    # M7 contains a large diagnostic/acceptance harness. Keep the cartridge
    # runtime and generated AOT banks optimized, but compile this orchestration
    # TU without optimizer work so iterative Windows CI stays practical.
    set_source_files_properties(src/m7.cpp PROPERTIES COMPILE_OPTIONS "/Od;/Ob0")
endif()

# The same acceptance gates can run locally when hosted Actions quota is
# exhausted. A diagnostic route replay is not a substitute for battle/save.
include(CTest)
if(BUILD_TESTING)
    set(LOCAL_VALIDATION_DIR "${CMAKE_CURRENT_BINARY_DIR}/local-validation")
    file(MAKE_DIRECTORY "${LOCAL_VALIDATION_DIR}")
    add_test(NAME M1_decoder COMMAND "${Python3_EXECUTABLE}"
        "${CMAKE_CURRENT_SOURCE_DIR}/tools/test_lr35902.py" --bank0 "${BANK0_SOURCE}")
    add_test(NAME M2_bank0_audit COMMAND "${Python3_EXECUTABLE}"
        "${CMAKE_CURRENT_SOURCE_DIR}/tools/recompile_bank0.py" --bank "${BANK0_SOURCE}" --audit-only)
    add_test(NAME M4_renderer COMMAND DWM2tRecomp --self-test --bmp "${LOCAL_VALIDATION_DIR}/m4.bmp")
    add_test(NAME M5_title COMMAND DWM2tRecomp --title-test "${LOCAL_VALIDATION_DIR}/m5.bmp")
    add_test(NAME M6_movement COMMAND DWM2tRecomp --m6-probe "${LOCAL_VALIDATION_DIR}/m6")
    add_test(NAME M6_sram COMMAND DWM2tRecomp --m6-sram-test "${LOCAL_VALIDATION_DIR}/m6.sav")
    add_test(NAME M6_window COMMAND DWM2tRecomp --m6-window-smoke "${LOCAL_VALIDATION_DIR}/m6_window.sav")
    add_test(NAME M7_audio COMMAND DWM2tRecomp --m7-audio-probe)
    add_test(NAME M7_intro_p1 COMMAND DWM2tRecomp --m7-replay-p1
        "${CMAKE_CURRENT_SOURCE_DIR}/tests/m7_intro_p1.txt" "${LOCAL_VALIDATION_DIR}/intro")
    add_test(NAME M7_party_p1 COMMAND DWM2tRecomp --m7-replay-p1
        "${CMAKE_CURRENT_SOURCE_DIR}/tests/m7_party_p1.txt" "${LOCAL_VALIDATION_DIR}/party")
    add_test(NAME M7_battle COMMAND DWM2tRecomp --m7-battle-test "${LOCAL_VALIDATION_DIR}/battle")
    add_test(NAME M7_save_continue COMMAND DWM2tRecomp --m7-save-continue-test
        "${LOCAL_VALIDATION_DIR}/m7_original.sav" "${LOCAL_VALIDATION_DIR}/save_continue")
    get_property(LOCAL_TESTS DIRECTORY PROPERTY TESTS)
    set_tests_properties(${LOCAL_TESTS} PROPERTIES WORKING_DIRECTORY "${REPO_ROOT}" TIMEOUT 600)
    # Headless gates have isolated Runtime instances/files and may run together.
    # Keep the one real desktop-window test exclusive.
    set_tests_properties(M6_window PROPERTIES RUN_SERIAL TRUE)
    add_custom_target(check-m7
        COMMAND "${CMAKE_CTEST_COMMAND}" -R "^M[1-7]_" --parallel 4 --output-on-failure --stop-on-failure -C "$<CONFIG>"
        DEPENDS DWM2tRecomp WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}" USES_TERMINAL)
    # Development checks only: the original ending/credits are not covered yet.
    add_test(NAME M8_trace_contract COMMAND "${Python3_EXECUTABLE}"
        "${CMAKE_CURRENT_SOURCE_DIR}/tools/test_m8_trace.py"
        --exe "$<TARGET_FILE:DWM2tRecomp>" --output "${LOCAL_VALIDATION_DIR}/m8_tools")
    add_test(NAME M8_audio_selection COMMAND DWM2tRecomp --audio-selection-test)
    add_test(NAME M8_audio_presentation COMMAND DWM2tRecomp --audio-presentation-test)
    if(WIN32)
        add_test(NAME M8_audio_playback COMMAND DWM2tRecomp --audio-playback-test)
        set_tests_properties(M8_audio_playback PROPERTIES
            RUN_SERIAL TRUE TIMEOUT 60 SKIP_RETURN_CODE 77)
    endif()
    add_test(NAME M8_oasis_checkpoint COMMAND "${Python3_EXECUTABLE}"
        "${CMAKE_CURRENT_SOURCE_DIR}/tools/test_m8_oasis.py"
        --exe "$<TARGET_FILE:DWM2tRecomp>" --seed "${LOCAL_VALIDATION_DIR}/m7_original.sav"
        --route "${CMAKE_CURRENT_SOURCE_DIR}/tests/m8_oasis_town_p1.txt"
        --inn-route "${CMAKE_CURRENT_SOURCE_DIR}/tests/m8_inn_heal_p1.txt"
        --checkpoint-route "${CMAKE_CURRENT_SOURCE_DIR}/tests/m8_asiya_arrival_p1.txt"
        --checkpoint-route "${CMAKE_CURRENT_SOURCE_DIR}/tests/m8_asiya_king_p1.txt"
        --checkpoint-route "${CMAKE_CURRENT_SOURCE_DIR}/tests/m8_kalka_canal_preparation_p1.txt"
        --checkpoint-route "${CMAKE_CURRENT_SOURCE_DIR}/tests/m8_dam_boss_victory_p1.txt"
        --checkpoint-route "${CMAKE_CURRENT_SOURCE_DIR}/tests/m8_asiya_thieves_report_p1.txt"
        --checkpoint-route "${CMAKE_CURRENT_SOURCE_DIR}/tests/m8_watercall_exchange_p1.txt"
        --checkpoint-route "${CMAKE_CURRENT_SOURCE_DIR}/tests/m8_oasis_curselamp_victory_p1.txt"
        --checkpoint-route "${CMAKE_CURRENT_SOURCE_DIR}/tests/m8_post_oasis_home_p1.txt"
        --feeding-route "${CMAKE_CURRENT_SOURCE_DIR}/tests/m8_enemy_meat_p1.txt"
        --audio-route "${CMAKE_CURRENT_SOURCE_DIR}/tests/m8_hub_audio_p1.txt"
        --output "${LOCAL_VALIDATION_DIR}/m8_oasis")
    set_tests_properties(M7_save_continue PROPERTIES FIXTURES_SETUP M7_original_save)
    set_tests_properties(M8_oasis_checkpoint PROPERTIES FIXTURES_REQUIRED M7_original_save)
    set_tests_properties(M8_trace_contract M8_oasis_checkpoint PROPERTIES
        WORKING_DIRECTORY "${REPO_ROOT}" TIMEOUT 600)
    # The extended original chain now includes the home event and two isolated
    # side branches. Keep a finite budget without truncating valid longer runs.
    set_tests_properties(M8_oasis_checkpoint PROPERTIES TIMEOUT 900)
    add_custom_target(check-m8-development
        COMMAND "${CMAKE_CTEST_COMMAND}" --parallel 4 --output-on-failure --stop-on-failure -C "$<CONFIG>"
        DEPENDS DWM2tRecomp WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}" USES_TERMINAL)
endif()
