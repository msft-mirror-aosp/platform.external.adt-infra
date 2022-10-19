# Copyright 2020 The Android Open Source Project
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
import logging
import os
from pathlib import Path

from jinja2 import Environment, PackageLoader


class TemplateWriter:
    """A Template writer uses jinja to render templates to an
       output directory.

       The templates are in the emu.templates package.


    Attributes:
        out_dir (Path): The destination when we write out a template.
    """

    def __init__(self, out_dir: str):
        """Creates a template writer that renders templates to the out_dir

        The out_dir directory will be created if it does not exist.

        Args:
            out_dir (str): The output directory where the template
                           writer will render the results.
        """
        self.env = Environment(loader=PackageLoader("emu", "templates"))
        self.dest = Path(out_dir)

    def write_template(
        self, template_file: str, template_dict: dict[str, str], rename_as=None
    ) -> None:
        """Renders the given template to the destination directory.

        Args:
            template_file (str): The template from the package emu.templates
                                 directory to use
            template_dict (dict[str, str]): Map used to render the template.
            rename_as (_type_, optional): Rename the template_file to this name when writing
                                to the out_dir. Defaults to None, meaning no rename.
        """
        dest_name = rename_as if rename_as else template_file
        return self._write_template_to(
            template_file, os.path.join(self.dest, dest_name), template_dict
        )

    def template_to_dict(
        self, template_ini_file: str, template_dict: dict[str, str]
    ) -> dict[str, str]:
        """Renders the given template ini file, returning it as a dictionary.

        Args:
            template_ini_file (str): The template file to render
            template_dict (dict[str, str]): The dictionary used to render the template.

        Returns:
            dict[str, str]: The parsed ini file, after rendering.
        """
        template = self.env.get_template(template_ini_file)
        ini = template.render(template_dict)
        cfg = {}
        for line in ini.splitlines():
            line = line.strip()
            if line.startswith("#"):
                continue
            key, *value = line.split("=")
            cfg[key] = next(iter(value), None)
        return cfg

    def _write_template_to(self, tmpl_file, dest_file, template_dict):
        """Loads the the given template, writing it to the dest_file

        Note: the template will be written {dest_dir}/{tmpl_file},
        directories will be created if the do not yet exist.
        """
        template = self.env.get_template(tmpl_file)

        dest_dir = os.path.dirname(dest_file)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

        logging.info("Writing: %s -> %s with %s", tmpl_file, dest_file, template_dict)
        with open(dest_file, "w", encoding="utf-8") as dfile:
            dfile.write(template.render(template_dict))
