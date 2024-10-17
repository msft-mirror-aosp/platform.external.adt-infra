# Our Local Python Repository

This repository manages a collection of Python wheels for use on our buildbots. These pre-built wheels ensure consistent and efficient execution of Python scripts across different platforms.

## Quick Start

1. **Launch the devpi server:**
    If you haven't already, start the local devpi server:

    ```bash
    ./launch-devpi.sh
    ```

2. **Obtain the latest version of a package:**
    To obtain the latest version of the `requests` package:

    ```bash
    ./pm.sh -d "requests"
    ```

    - You can get specific versions using standard pip syntax. For example, `./pm.sh -d "requests>=2.32.1"` will install version 2.32.1 or greater.
    - If a package with the given name already exists, you must remove it first:

        ```bash
        ./pm.sh -e "requests"
        ```

    This downloads the `requests` package for all supported platforms. Next, commit the changes.

## Managing Wheels

### Adding New Wheels

To add new wheels:

1. **Launch the devpi server:**
    If you haven't already, start the local devpi server:

    ```bash
    ./launch-devpi.sh
    ```

2. **Obtain wheels for all supported platforms:**
    Ensure you have the wheel files for each of the following platforms:

    - macOS (x86\_64 and arm64)
    - Linux (x86\_64)
    - Windows (amd64)

    **Example:**

    If you have a package named `my_package` and need to support macOS and Linux, you should have `my_package-1.0.0-cp39-cp39-macosx_10_9_x86_64.whl` and `my_package-1.0.0-cp39-cp39-manylinux_2_17_x86_64.whl` .

3. **Upload the wheels:**
    Use the `pm.sh` script to upload the wheel files. You can upload them individually or provide a directory containing all the wheels.

    **Examples:**

    - To upload a single wheel:

        ```bash
        ./pm.sh -f "path/to/my_package-1.0.0-cp39-cp39-macosx_10_9_x86_64.whl"
        ```

    - To upload all wheels in a directory:

        ```bash
        ./pm.sh -r "path/to/wheels_directory"
        ```

4. **Commit the changes:**
    After uploading, commit the changes to the repository:

    ```bash
    git add .
    git commit -m "Added my_package wheels"
    ```

### Removing Packages

To remove a package from the repository and the devpi server, use the `-e` option with `pm.sh` .

**Example:**

To remove the `my_package` package:

```bash
./pm.sh -e "my_package"
```

This will remove all versions and platform-specific wheels of my_package from the repository and the devpi server. Remember to commit the changes after removing a package.

## Important Notes

- Make sure the devpi server is running before uploading or downloading packages.
- Always commit your changes to the repository after adding, removing, or downloading packages.
- This repository uses twine, devpi-client, and pip2pi for package management. Ensure these tools are installed. You can install them using pip:
 `pip install twine devpi-client pip2pi`

- This repository also uses symlinks. You can install it using:
 `apt install symlinks`

By following these instructions, you can effectively manage the wheels in this repository and ensure that our buildbots have access to the necessary Python packages.
