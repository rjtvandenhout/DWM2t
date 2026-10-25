cmake_minimum_required(VERSION 3.24)
project(DWM2tSaveIoContracts LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
get_filename_component(CORE "${CMAKE_CURRENT_SOURCE_DIR}/../.." ABSOLUTE)
add_executable(DWM2tSaveIoContracts
    "${CORE}/tests/save_io_contracts.cpp"
    "${CORE}/src/memory.cpp"
    "${CORE}/src/apu.cpp")
add_executable(DWM2tSaveIoFaultContracts
    "${CORE}/tests/save_io_fault_contracts.cpp"
    "${CORE}/src/apu.cpp")
foreach(TARGET DWM2tSaveIoContracts DWM2tSaveIoFaultContracts)
    target_include_directories(${TARGET} PRIVATE "${CORE}/include")
    if(MSVC)
        target_compile_options(${TARGET} PRIVATE /W4 /permissive- /utf-8)
    else()
        target_compile_options(${TARGET} PRIVATE -Wall -Wextra -Wpedantic)
    endif()
endforeach()
include(CTest)
add_test(NAME M8_save_io_contracts COMMAND DWM2tSaveIoContracts "${CMAKE_CURRENT_BINARY_DIR}/evidence")
set_tests_properties(M8_save_io_contracts PROPERTIES TIMEOUT 30)
add_test(NAME M8_save_io_fault_contracts COMMAND DWM2tSaveIoFaultContracts "${CMAKE_CURRENT_BINARY_DIR}/evidence")
set_tests_properties(M8_save_io_fault_contracts PROPERTIES TIMEOUT 30)
