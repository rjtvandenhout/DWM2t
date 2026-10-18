#pragma once
#include <filesystem>
namespace dwm2t {
int run_m8_session(const std::filesystem::path& save,
                   const std::filesystem::path& output,
                   const std::filesystem::path& trace = {});
int run_m8_replay(const std::filesystem::path& save,
                  const std::filesystem::path& route,
                  const std::filesystem::path& output);
int run_m8_checkpoint_test(const std::filesystem::path& seed,
                           const std::filesystem::path& route,
                           const std::filesystem::path& output);
int run_m8_oasis_test(const std::filesystem::path& seed,
                      const std::filesystem::path& route,
                      const std::filesystem::path& output);
int run_m8_inn_test(const std::filesystem::path& seed,
                    const std::filesystem::path& route,
                    const std::filesystem::path& output);
}
