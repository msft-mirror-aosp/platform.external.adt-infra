# -*- coding: utf-8 -*-
# Copyright 2024 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from _pytest.reports import TestReport
from _pytest.runner import CallInfo
from _pytest.nodes import Item


def pytest_runtest_makereport(item: Item, call: CallInfo) -> TestReport:
    """Adds the 'retries' attribute to the JUnit XML report.

    This hook injects the number of retries performed for a test into the
    JUnit XML report as a custom attribute named "retries".  It leverages
    the `record_xml_attribute` fixture provided by pytest to achieve this.
    The retry count is obtained from the `execution_count` attribute of the
    test item. This count represents the number of times the test has been
    executed, which is equivalent to the number of retries plus one.
    The value is zero-indexed. A value of '0' implies the first attempt and
    a value of '1' implies one retry attempt.


    Args:
        item: The pytest test item object.
        call: The pytest call information object.

    Returns:
        None. The return value is ignored by pytest.
    """

    if call.when == "call":
        record_xml_attribute = item._request.getfixturevalue("record_xml_attribute")
        if record_xml_attribute:
            record_xml_attribute("execution_count", item.execution_count)

    return None
