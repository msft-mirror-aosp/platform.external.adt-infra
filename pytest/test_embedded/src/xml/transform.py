# Copyright 2020 - The Android Open Source Project
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
import argparse
import sys

import lxml.etree as ET


def transform(xml, xsl, out):
    """Transform the given xml file using the provided xsl file

    Args:
        xml (str): A path to a valid XML file
        xsl (str): A path to a valid XSL file
        out (file): A file like object where to write the transformed xml to
    """
    parser = ET.XMLParser(huge_tree=True)
    dom = ET.parse(xml, parser=parser)
    xslt = ET.parse(xsl, parser=parser)
    transformer = ET.XSLT(xslt)
    out.write(transformer(dom))
    out.flush()


def launch():
    """Parse the command line arguments and launch the transformation."""
    parser = argparse.ArgumentParser(
        description="Transform an xml file by applying an xsl stylesheet."
    )
    parser.add_argument(
        "--xsl",
        help="The xsl stylesheet that is to be applied",
    )
    parser.add_argument(
        "--out", help="The (optional) output file where the result will be written to"
    )
    parser.add_argument("--xml", help="The input xml file that is to be transformed")

    args = parser.parse_args()

    out = sys.stdout.buffer
    if args.out:
        out = open(args.out, "wb")

    transform(args.xml, args.xsl, out)


if __name__ == "__main__":
    launch()
