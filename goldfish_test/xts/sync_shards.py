import os
import glob

def sync():
    files = glob.glob("shards/*.txt")
    shards = {}

    for f in files:
        is_shard_file = f.endswith("_shard.txt")
        default_module_name = os.path.basename(f).replace("_shard.txt", "") if is_shard_file else None

        with open(f, 'r') as txt:
            for line in txt:
                line = line.strip()
                # Skip empty lines or comments
                if not line or line.startswith('#'):
                    continue

                parts = line.split(None, 1)

                if len(parts) == 1:
                    if default_module_name:
                        mod = default_module_name
                        submod = parts[0]
                    else:
                        print(f"Warning: Ignoring single-word line in non-shard file {f}: {line}")
                        continue
                else:
                    mod = parts[0]
                    submod = parts[1]

                if mod not in shards:
                    shards[mod] = []
                # Merge logic: if a module_name submodule appears at both places, merge them into one shard
                if submod not in shards[mod]:
                    shards[mod].append(submod)

    with open("xts_sharded.bzl", "w") as out:
        out.write('load("//xts:xts.bzl", "module_subtests")\n\n')
        out.write('# GENERATED FILE. To update from txt files, run python3 sync_shards.py\n\n')
        out.write('SHARDS = {\n')
        # Sort modules to ensure deterministic generation
        for mod in sorted(shards.keys()):
            out.write(f'    "{mod}": [\n')
            for sm in shards[mod]:
                out.write(f'        "{sm}",\n')
            out.write('    ],\n')
        out.write('}\n\n')
        out.write('def xts_sharded_tests():\n')
        out.write('    all_test_targets = []\n')
        out.write('    for module_name, submodules in SHARDS.items():\n')
        out.write('        suite = "gts" if module_name.startswith("Gts") else "cts"\n')
        out.write('        target_name = module_name + ".shard"\n')
        out.write('        module_subtests(\n')
        out.write('            name = target_name,\n')
        out.write('            module_name = module_name,\n')
        out.write('            submodules = submodules,\n')
        out.write('            suite = suite,\n')
        out.write('        )\n')
        out.write('        all_test_targets.append(":" + target_name)\n')
        out.write('\n')
        out.write('    native.test_suite(\n')
        out.write('        name = "all_shards",\n')
        out.write('        tests = all_test_targets,\n')
        out.write('    )\n')

if __name__ == "__main__":
    sync()
