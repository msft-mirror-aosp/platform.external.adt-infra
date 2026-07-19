# Sharding Process

This document describes how to manage and run test shards. Large lists of module subtests have been extracted from `BUILD.bazel` into individual text files under the `shards/` directory, improving maintainability. A macro `xts_sharded_tests()` is generated from these files to automatically instantiate the test targets.

## How to Manage Shards

There are two ways to define shards:

### 1. Single Module Shard Files
- **To add a shard:** Create or edit a `shards/{ModuleName}_shard.txt` file and add one submodule name per line.
- **Example:** `shards/CtsWidgetTestCases_shard.txt`

### 2. Multi-Module Mapping Files
- **To add a shard:** You can create any `.txt` file in the `shards/` directory (e.g., `shards/my_mixed_tests.txt`) and add lines containing two space-separated words: `<ModuleName> <SubModuleName>`.
- **Example:**
  ```text
  CtsWidgetTestCases android.widget.cts.ButtonTest*
  GtsExoPlayerTestCases com.google.android.exoplayer.gts.DashDownloadTest
  ```

After modifying any shard files, **always run `python3 sync_shards.py`** to regenerate the Bazel macros. The script parses both types of files and merges the submodules into their respective module targets.

## Running Tests

- **To run one shard:**
  `bazel test :<ModuleName>.shard.<SubModuleName>`
  *(e.g., `bazel test :CtsWidgetTestCases.shard.android.widget.cts.AbsListViewTest*`)*

- **To run all shards in a module:**
  `bazel test :<ModuleName>.shard`
  *(e.g., `bazel test :CtsWidgetTestCases.shard`)*

- **To run all shards across all modules:**
  `bazel test :all_shards`
  *(The `sync_shards.py` script automatically aggregates all generated shard targets into a single native.test_suite called `all_shards`)*