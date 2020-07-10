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
PYTHON := python
PY_VERSION := $(shell $(PYTHON) -c "import sys;sys.stdout.write(str(sys.version_info[0]))")
MAKEFILE_PATH := $(abspath $(lastword $(MAKEFILE_LIST)))
CURRENT_DIR :=  $(abspath $(MAKEFILE_PATH)/..)
OUTPUT_DIR :=  $(if $(SESSION_DIR),$(SESSION_DIR)/embedded_test,$(CURRENT_DIR)/.tox)
QEMU_ROOT := $(abspath $(MAKEFILE_PATH)/../../../../qemu)
AEMU_ROOT := $(abspath $(QEMU_ROOT)/android/android-grpc/python)
WHEEL_DIR := $(abspath $(OUTPUT_DIR)/wheels)
WHEEL := $(WHEEL_DIR)/aemu_grpc-0.0.1-py$(PY_VERSION)-none-any.whl

$(info Python: $(PY_VERSION) Output: $(OUTPUT_DIR), Qemu: $(QEMU_ROOT))
$(WHEEL_DIR):
	mkdir -p $(WHEEL_DIR)

$(WHEEL): $(WHEEL_DIR)
	make -C $(AEMU_ROOT) DIST=$(WHEEL_DIR)

deps:  $(WHEEL)
	$(PYTHON) -m pip install -q --upgrade -r$(CURRENT_DIR)/requirements.txt $(WHEEL)

clean:
	rm -rf $(WHEEL_DIR)

check: deps
	tox --workdir $(OUTPUT_DIR) -- --emulator=$(EMULATOR)

.DEFAULT_GOAL := check