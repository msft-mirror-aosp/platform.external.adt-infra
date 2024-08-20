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
import base64
import datetime
import json
import logging
import re
import shutil
import zlib
from functools import lru_cache
from typing import Dict
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

        return stdout.decode("utf-8").strip()


class GrpcDecoder(object):
    """Parses a grpc service file, translating every method into the corresponding
    crc32 hash that is used by the gRPC engine when recording metrics.
    """

    GRPC_PHASE = {
        "<": "Incoming server call",
        ">": "Outgoing client call",
        "!": "PRE_SEND_INITIAL_METADATA",
        "@": "PRE_SEND_MESSAGE",
        "#": "POST_SEND_MESSAGE",
        "$": "PRE_SEND_STATUS",
        "%": "PRE_SEND_CLOSE",
        "^": "PRE_RECV_INITIAL_METADATA",
        "&": "PRE_RECV_MESSAGE",
        "*": "PRE_RECV_STATUS",
        "(": "POST_RECV_INITIAL_METADATA",
        ")": "POST_RECV_MESSAGE",
        "_": "POST_RECV_STATUS",
        "-": "POST_RECV_CLOSE",
        "+": "PRE_SEND_CANCEL (uncertain)",
        "|": "End of call",
    }

    RPC_RE = re.compile(r".*rpc (\w+)\(.*\) returns")
    RPC_RE_DEL = re.compile(r".*rpc (\w+) \((\d+\/\d+\/\d+)\)")
    SERVICE_RE = re.compile(r"service (\w+)")
    PACKAGE_RE = re.compile(r"package (.*);")

    def __init__(self, expired=360):
        # We interpret deleted metrics for 180 days.
        self.keep_after_date = datetime.datetime.now() - datetime.timedelta(
            days=expired
        )
        self.methods = {}  # crc32 -> method name
        self.full_methods = {}  # crc32 -> complete name
        self.deprecated = {}

    def add_grpc_file(self, grpc_proto_file):
        package, service, discovered, deleted = self._parse_grpc_file(
            grpc_proto_file, self.keep_after_date
        )

        if service is None or package is None:
            raise Exception("No service or package definition found.")

        for name in discovered:
            method = self.url(package, service, name)
            crc = str(zlib.crc32(bytearray(method, "utf-8")))
            self.methods[crc] = name
            self.full_methods[crc] = method

        for name in deleted:
            method = self.url(package, service, name)
            crc = str(zlib.crc32(bytearray(method, "utf-8")))
            self.deprecated[crc] = name

    def _parse_grpc_file(self, fname, keep_after_date):
        """Parses the service file, returning the package, service and discovered method names."""
        package = ""
        service = ""
        discovered = []
        deprecated = []
        logging.info("Parsing %s", fname)
        with open(fname, "r") as pfile:
            for line in pfile.readlines():
                m = GrpcDecoder.PACKAGE_RE.match(line)
                if m:
                    if package:
                        raise Exception(f"Already found a package defintion: {package}")
                    package = m.group(1)

                m = GrpcDecoder.SERVICE_RE.match(line)
                if m:
                    if service:
                        logging.warning(
                            "Already found a service defintion: %s in %s, ignoring",
                            service,
                            fname,
                        )
                        continue
                    service = m.group(1)
                m = GrpcDecoder.RPC_RE.match(line)
                if m:
                    discovered.append(m.group(1))

                m = GrpcDecoder.RPC_RE_DEL.match(line)
                if m:
                    date = datetime.datetime.strptime(m.group(2), "%m/%d/%y")
                    if date > keep_after_date:
                        deprecated.append(m.group(1))

        return package, service, discovered, deprecated

    def url(self, package, service, method):
        """The actual url for the given method, used to derive crc32."""
        return f"/{package}.{service}/{method}"

    def url_from_crc32(self, crc32):
        if crc32 in self.methods:
            return self.url(self.methods[crc32])
        return self.url(self.deprecated.get(crc32, "__unknown__"))

    def decode_snippet(self, encoded_string):
        """
        Decodes a Base64 encoded log line.

        Args:
            encoded_string: The Base64 encoded log line.

        Returns:
            A tuple containing the start character, CRC value, and timestamp.
        """
        # Decode the Base64 string.
        try:
            decoded_data = base64.b64decode(encoded_string + "===")

            # Extract the start character.
            start = chr(decoded_data[0])

            # Extract the CRC value.
            crc = int.from_bytes(decoded_data[1:5], byteorder="little")

            # Extract the timestamp.
            timestamp = int.from_bytes(decoded_data[5:13], byteorder="little")
            return (
                self.GRPC_PHASE.get(start, start),
                self.full_methods.get(str(crc), f"{crc}"),
                datetime.datetime.fromtimestamp(timestamp),
            )
        except Exception as e:
            logging.error("Error decoding log line: %s", e)
            return ('?', "?Failed to decode", datetime.datetime.now())



    def __str__(self):
        return "\n".join(
            ["{} : {}".format(k, self.url_from_crc32(k)) for k in self.methods.keys()]
            + [
                "{} : {}_deprecated".format(k, self.url_from_crc32(k))
                for k in self.deprecated.keys()
            ]
        )

    @staticmethod
    @lru_cache(maxsize=None)
    def from_directory(start_dir: Path):
        s = GrpcDecoder(3600)
        for path in Path(start_dir).glob("**/*.proto"):
            if path.is_file():
                s.add_grpc_file(path)

        return s


class CrashReporter:
    def __init__(self, emulator_directory: Path, symbol_path: Path, aosp: Path):
        self.crashreporter = shutil.which("crashreport", path=emulator_directory)
        self.symbol_path = symbol_path if symbol_path else ""
        self.aosp = aosp
        logging.debug(
            "Crashreporter configured with reporter: %s, "
            "symbol path: %s, gRPC service search directory: %s",
            self.crashreporter,
            self.symbol_path,
            self.aosp,
        )

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

    async def analyze_annnotations(self, dump) -> Dict[str, str]:
        decoded = {}
        if not self.aosp:
            logging.info("No aosp available, skipping annotations")
            return decoded

        try:
            decoder = GrpcDecoder.from_directory(self.aosp)
            look_for = ["Module annotations:", "==================="]
            lines = dump.splitlines()
            lines = lines[lines.index(look_for[0]) + 2 :]
            modules = json.loads("\n".join(lines))
            for module in modules:
                if "annotation_objects" in module:
                    annotations = module["annotation_objects"]
                    logging.info("Found %d annotations", len(annotations))
                    for annotation in annotations:
                        name = annotation["name"]
                        if name == "grpc" or re.match(r"\d+", name):
                            values = annotation["value"]
                            for value in values.split(" "):
                                phase, method, timestamp = decoder.decode_snippet(
                                    value.strip()
                                )
                                call_info = f'{timestamp.strftime("%Y-%m-%d %H:%M:%S")} {phase} {method}'
                                decoded.get(name, []).append(call_info)
                                logging.info("Found %s -> %s", name, call_info)
        except Exception as err:
            logging.info("No module annotations found due to: %s", err)

        return decoded

    async def list_crashes(self):
        """This lists and reports any crashes that we encountered during the running of tests."""
        reports: str = await self.report(["-l"])
        if reports == "":
            logging.info("No crashes reported.")

        for report in reports.splitlines():
            logging.critical("=-=-=-=-=-=-=-=-= report: %s =-=-=-=-=-=-=-=-=", report)
            dump = await self.report(["-d", report, self.symbol_path])
            logging.critical(dump)
            annotations = await self.analyze_annnotations(dump)
            logging.critical(annotations)

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
            logging.critical(
                "Writing crash report %s to %s", report, dest.with_suffix(".log")
            )
            annotations = await self.analyze_annnotations(dump)
            annotations_str = json.dumps(annotations, indent=4)
            with open(dest.with_suffix(".log"), "w", encoding="utf-8") as dmp:
                dmp.write(dump)
                dmp.write("\n")
                dmp.write(annotations_str)

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
