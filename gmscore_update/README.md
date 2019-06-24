# gmscore_update
A script that will move GmsCore APKs from x20 to emulator system image and bump
sdk versions accordingly. The script will download relevant projects locally, commit
the changes then upload to Gerrit server with different topics for each API level.

## Getting Started
To auto-generate CLs, you can invoke the script as follows:
```sh
python gmscore_update.py --x20_candidate_dir=releases/v25/gmscore_prod_20190207.00_RC13 --version_code=16.0.89 --bug=134409472 --rapid_candidate_id=gmscore_prod_20190207.00/gmscore_prod_20190207.00_RC13
```

The commandline parameters mean the following
- `--rapid_candidate_id "gmscore_prod_20190207.00/gmscore_prod_20190207.00_RC13"` Indicates that the APK was built in go/gmscore-rapid/{rapid_candidate_id}. E.g. "gmscore_prod_20190207.00/gmscore_prod_20190207.00_RC13" (for a pre-integration build will be something like "gmscore_apks_20180118.01/gmscore_apks_20180118.01_RC00")
- `--x20_candidate_dir "releases/v25/gmscore_prod_20190207.00_RC13"` Indicates the directory look up for the APK files in X20. To find out, go to go/gmscore-apks; E.g. "releases/v25/gmscore_prod_20190207.00_RC13" (for a pre-integration build, will be something like 'daily/gmscore_apks_20180118.01_RC00')
- `--version_code "16.0.89"` Set GmsCore APK version number
- `--bug_number "74248480"`  Set bug number. reference bug:  b/74248480.


Optional flags
- `dry_run`   the script will only generate CL in local.
- `git {git binaries path}` the path to git binaries.
