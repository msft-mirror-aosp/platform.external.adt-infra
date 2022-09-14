echo "Using Python ${PY_VER}"

write_local_pip_conf() {
    cat <<EOF >.venv/pip.conf
[global]
index-url = http://localhost:3141/packages/staging

[search]
index = http://localhost:3141/package/staging


EOF

    cat <<EOF >.venv/.pypirc
[distutils]
index-servers =
    devpi-stable
    devpi-staging

[devpi-stable]
repository = http://localhost:3141/packages/stable/
username = packages
password = packages

[devpi-staging]
repository = http://localhost:3141/packages/staging/
username = packages
password = packages
EOF
}

if [ ! -f "./venv/bin/activate" ]; then
  python3 -m venv .venv
fi

if [ -e ./.venv/bin/activate ]; then
  . ./.venv/bin/activate
  write_local_pip_conf
fi


echo "You can now launch the devpi-server, with the config below:"
cat << EOF
[global]
index-url = http://localhost:3141/root/pypi/+simple/

[search]
index = http://localhost:3141/root/pypi/
EOF
