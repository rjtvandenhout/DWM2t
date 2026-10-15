PYTHON ?= python3
BUILD_DIR := build
ROM := $(BUILD_DIR)/dwm2_cobi.gbc
OBJ := $(BUILD_DIR)/dwm2_cobi.o

.PHONY: all rebuild verify rgbds clean

all: verify

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

rebuild: | $(BUILD_DIR)
	$(PYTHON) tools/rebuild.py --out $(ROM)

verify: rebuild
	$(PYTHON) tools/verify.py $(ROM)

rgbds: | $(BUILD_DIR)
	@command -v rgbasm >/dev/null || (echo "rgbasm not found; install RGBDS first" && exit 1)
	@command -v rgblink >/dev/null || (echo "rgblink not found; install RGBDS first" && exit 1)
	rgbasm -o $(OBJ) src/main.asm
	rgblink -o $(ROM) $(OBJ)
	$(PYTHON) tools/verify.py $(ROM)

clean:
	rm -rf $(BUILD_DIR)
