# Copyright (C) 2019 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
PYTHON := python3
PY_VERSION := $(shell $(PYTHON) -c "import sys;sys.stdout.write(str(sys.version_info[0]))")
MAKEFILE_PATH := $(abspath $(lastword $(MAKEFILE_LIST)))
CURRENT_DIR :=  $(abspath $(MAKEFILE_PATH)/..)
OUTPUT_DIR :=  $(if $(SESSION_DIR),$(SESSION_DIR)/embedded_test,$(CURRENT_DIR)/.tox)
QEMU_ROOT := $(abspath $(MAKEFILE_PATH)/../../../../qemu)
AEMU_ROOT := $(abspath $(QEMU_ROOT)/android/android-grpc/python)
SNAP_ROOT := $(abspath $(QEMU_ROOT)/android/android-grpc/docs/python/snaptool)
WHEEL_DIR := $(abspath $(OUTPUT_DIR)/wheels)
WHEEL := $(WHEEL_DIR)/aemu_grpc-0.0.1-py$(PY_VERSION)-none-any.whl
SNAP  := $(WHEEL_DIR)/emu_snap-1.0-py$(PY_VERSION)-none-any.whl

$(info Python: $(PY_VERSION) Output: $(OUTPUT_DIR), Qemu: $(QEMU_ROOT))
$(WHEEL_DIR):
	mkdir -p $(WHEEL_DIR)

$(WHEEL): $(WHEEL_DIR)
	make -C $(AEMU_ROOT) DIST=$(WHEEL_DIR)

AnimateBox/app/build/outputs/apk/debug/app-debug.apk:
	cd AnimateBox && ./gradlew assembleDebug

src/emu/apk/app-debug.apk: AnimateBox/app/build/outputs/apk/debug/app-debug.apk
	cp AnimateBox/app/build/outputs/apk/debug/app-debug.apk src/emu/apk/app-debug.apk

$(SNAP): $(WHEEL)
	make -C $(SNAP_ROOT) DIST=$(WHEEL_DIR)

deps:  $(WHEEL) $(SNAP) src/emu/apk/app-debug.apk
	$(PYTHON) -m pip install -q  --no-index --find-links=$(CURRENT_DIR)/local_repo/dist  -r$(CURRENT_DIR)/requirements.txt $(WHEEL) $(SNAP)

clean:
	rm -rf $(WHEEL_DIR)
	rm -f AnimateBox/app/build/outputs/apk/debug/app-debug.apk

check: deps
	tox --workdir $(OUTPUT_DIR) -- -x --emulator=$(EMULATOR)

.DEFAULT_GOAL := check
