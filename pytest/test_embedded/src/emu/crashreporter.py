# Copyright 2023 - The Android Open Source Project
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
import asyncio
import logging
import shutil
from pathlib import Path

# Hack attack..
try:
    from emu.process.command import Command

    async def check_run(params):
        cmd = Command(params)
        status, result = await cmd.run_until_finished()
        return "\n".join(result)

except:

    async def check_run(params):
        proc = await asyncio.create_subprocess_exec(
            *params, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        status = await proc.wait()
        if status != 0:
            raise ValueError("Failed to execute %s", " ".join(params))

        return stdout.strip()


class CrashReporter:
    def __init__(self, emulator_directory: Path, symbol_path: Path):
        self.crashreporter = shutil.which("crashreport", path=emulator_directory)
        self.symbol_path = symbol_path if symbol_path else ""

    async def report(self, params: [str]) -> str:
        """Run the crash reporter with the given set of parameters.

        Note: This will only execute the reporter if it is available, otherwise
        it returns ""

        Args:
            params ([str]): Set of parameters to pass to the reporter.

        Returns:
            str: The output of the invocation.
        """
        if not self.crashreporter:
            return ""

        params = [str(x) for x in params]
        logging.info(
            "Running crashreporter: %s %s", self.crashreporter, " ".join(params)
        )

        return await check_run([self.crashreporter] + params)

    def available(self) -> bool:
        """True if the crash reporter binary is available."""
        return self.crashreporter is not None

    async def has_symbols(self) -> bool:
        return self.symbol_path is not None

    async def crashes(self) -> [str]:
        report = await self.report(["-l"])
        return report.splitlines()

    async def dump_crash(self, report_id: str) -> str:
        return await self.report(["-d", report_id, self.symbol_path])

    async def list_crashes(self):
        """This lists and reports any crashes that we encountered during the running of tests."""
        reports: str = await self.report(["-l"])
        if reports == "":
            logging.info("No crashes reported.")

        for report in reports.splitlines():
            logging.critical("=-=-=-=-=-=-=-=-= report: %s =-=-=-=-=-=-=-=-=", report)
            dump = await self.report(["-d", report, self.symbol_path])
            logging.critical(dump)

    async def write_reports_to_disk(self, dest_dir: Path):
        """Write all the crash report to the given directory.

        Args:
            dest_dir (Path): Directory to write the crash reports to.
        """
        reports: str = await self.report(["-l"])
        if reports == "":
            logging.info("No crashes reported.")

        for report in reports.splitlines():
            dest = dest_dir / Path(report).name
            dump = await self.report(["-d", report, self.symbol_path])
            with open(dest.with_suffix(".log"), "w", encoding="utf-8") as dmp:
                dmp.write(dump)

    async def report_crashes(self):
        """Reports all crash reports to the remote server."""
        reports = await self.report(["-u"])
        for report in reports.splitlines():
            logging.info("%s", report)

    async def clear(self):
        """Erase all recorded crash reports"""
        reports = await self.report(["-e"])
        for report in reports.splitlines():
            logging.info("%s", report)
