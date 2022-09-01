TOX Python dependencies
=======================

In this directory you will find all the required python dependencies
to run the embedded emulator tests.

If you are seeing errors during install you will need to build a wheel
of the missing package locally.

This can be done as follows:

Say the missing package is foo:

1. Start the virtual environment

        source venv/bin/activate

2. Download the missing package

        pip download foo

3. You will now see as set of .whl, or tar.gz files

    - foo.tar.gz    <--- this is a source package. **BAD**
    - bar.whl       <--- a ready to go wheel. **EXCELLENT!**

4. If you have a wheel you can just move it to the dist directory
   force add it with git and upload it. We do not want source 
   packages as they can require compilation, which in turn can depend
   on having the right toolchain configuration.

5. For a source package:

        pip3 install wheel
        tar xzvf foo.tar.gz
        cd foo
        python3 setup.py bdist_wheel

This will produce a binary wheel that you can distribute. You can discover the
actual wheel by running:

        find . -name '*whl'