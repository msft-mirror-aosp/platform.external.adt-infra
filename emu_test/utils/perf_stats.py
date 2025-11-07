#!/usr/bin/env python
"""
This file contains utility functions to dump perfgate stats.
"""

import json
import os
import platform
import argparse
import itertools

AVD_TYPE = ["New",
            "Existing"]

TAG = ["default",
       "google_apis",
       "google_apis_playstore"]

GPU = ["lavapipe"]

TESTCASE = ["idle",
            "gpu_stress",
            "large_apk"]

METRIC = "{}_AVD_{}_{}_{}"

def create_benchmark(name, value, timestamp):
    """
    Create a benchmark for perfgate json file.

    name: Name of benchmark
    value: List of data points
    timestamp: List of timestamps correspnding to data points

    return: A dictionary object for benchmark which can be dumped as json object
    """
    mean = {"type":"Mean",
            "constTerm":"10.0",
            "meanCoeff":"0.1",
            "stddevCoeff":"1.0"}

    median = {"type":"Median",
              "constTerm":"10.0",
              "medianCoeff":"0.1",
              "madCoeff":"1.0"}

    toleranceParams = [mean,
                       median]

    analyzers = [{"type":"WindowDeviationAnalyzer",
                  "metricAggregate":"MEDIAN",
                  "runInfoQueryLimit":"50",
                  "recentWindowSize":"25",
                  "toleranceParams":toleranceParams}]

    data = dict((int(ts),va) for (ts, va) in zip(timestamp, value))

    benchmark = {"benchmark": name,
                 "project": "Android Studio Emulator",
                 "data": data,
                 "analyzers": analyzers}

    return benchmark


def write_perf_data(metric, benchmark, data, timestamp):
    """
    Write perfgate stats to a json file.

    metric: Name of the metric
    benchmark: Name of the benchmark
    data: List of data points
    timestamp: List of timestamps correspnding to data points
    """
    print("write perf data " + metric + " " + benchmark)
    metric = metric + "_" + platform.system()

    if args.metric_tag:
        metric = metric + "_" + args.metric_tag

    jsonDir = os.path.join(args.log_dir,
                           "test.outputs")
    if not os.path.exists(jsonDir):
        os.makedirs(jsonDir)

    filename = os.path.join(jsonDir, metric + ".json")
    jsonFile = open(filename, "a")

    benchmarks = [create_benchmark(benchmark, data, timestamp)]
    json_data = {"metric": metric,
                 "benchmarks": benchmarks}

    jsonFile.write(json.dumps(json_data, indent=2))
    jsonFile.close()


def get_time(line):
    """
    Extract timestamp from line

    line: Sting containing timestamp

    return: timestamp
    """
    timestamp = int(line.split(" time ")[1].split()[0])
    return timestamp


def get_cpu_usage(cpu_data):
    """
    Calculate CPU usage

    cpu_data: CPU time

    return: CPU usage in %
    """
    return round(((cpu_data[1]+cpu_data[2])/cpu_data[0])*100.0, 2)


def get_cpu_mem_data(line):
    """
    Extract cpu and memory usage from line

    line: String containing cpu and memory usage data

    return: cpu and memory usage
    """
    mem_data = int(line.split(" memory_usage ")[1].split("resident_memory: ")[1].split()[0])
    vcpu_data = line.split(" memory_usage ")[0].split(" main_loop_slice ")[1].split(" vcpu_slices ")
    cpu0 = get_cpu_usage([float(x) for x in vcpu_data[0].split() if x.isdigit()])
    cpu1 = get_cpu_usage([float(x) for x in vcpu_data[1].split() if x.isdigit()])
    cpu2 = get_cpu_usage([float(x) for x in vcpu_data[2].split() if x.isdigit()])
    return cpu0, cpu1, cpu2, mem_data


def get_data_from_log(logFile):
    """
    Find data from test log files along with the timestamp

    marker: A marker to mark start of relevant data in log file
    logFile: Name of log file from which the data can be extracted

    return: A list of CPU and memory usage data with timestamps
    """
    cpu0_data = []
    cpu1_data = []
    cpu2_data = []
    memory_data = []
    timestamp = []
    with open(logFile, 'r') as log_file:
        for line in log_file:
            if "event time" in line:
                timestamp.append(get_time(line))
            elif "emulator_performance_stats" in line:
                cpu0_usage, cpu1_usage, cpu2_usage, memory_usage = get_cpu_mem_data(line)
                cpu0_data.append(cpu0_usage)
                cpu1_data.append(cpu1_usage)
                cpu2_data.append(cpu2_usage)
                memory_data.append(memory_usage)

    return [cpu0_data, cpu1_data, cpu2_data], memory_data, timestamp


def get_boot_time(logFile):
    """
    Get Boot time data

    logFile: Name of log file from which the data can be extracted

    return: List of boot times
    """
    boot_time = []
    with open(logFile, 'r') as log_file:
        for line in log_file:
            if "INFO: boot time" in line:
                boot_time.append(get_time(line))

    return boot_time


def write_boot_time_benchmark(metrics, boot_timestamp):
    """
    Write boot time benchmark

    metric: Dictionary to hold metrics and boot time
    boot_timestamp: Timestamps for each metric
    """
    key = ""
    logFile = os.path.join(args.log_dir, "PerfTestCase.log")
    with open(logFile, 'r') as log_file:
        count = 0
        prefix = "PerfGate Metric for {}: ".format(args.api)
        splitter = "INFO - PerfGate Metric for {}: ".format(args.api)
        for line in log_file:
            if prefix in line and "idle" in line:
                key = line.split(splitter)[1].split()[0]
            elif key and "INFO: boot time" in line:
                metrics[key] = get_time(line)
                key = ""
                count += 1
            if count == len(metrics):
                break

    for metric in metrics:
        write_perf_data("Boot_Time_"+metric,
                        "Boot_Time",
                        [metrics[metric]],
                        [boot_timestamp[metric]])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Pass dir info to configure perf data parsing")
    parser.add_argument("--log_dir", type=str, required=True, help="Directory containing log file to parse for perf stats")
    parser.add_argument("--metric_tag", type=str, default=None, help="Extra tag that can be attached to metric name")
    parser.add_argument("--api", type=str, required=True, help="Process data only for the given api")
    args = parser.parse_args()

    metrics = {}
    boot_timestamp = {}
    for avd_type, tag, gpu, testcase in itertools.product(AVD_TYPE, TAG, GPU, TESTCASE):
        metric = METRIC.format(avd_type, tag, gpu, testcase)

        logFileName = "{}_{}.log".format(args.api, metric)
        logFile = os.path.join(args.log_dir, logFileName)
        if not os.path.isfile(logFile):
            continue;
        cpu_data, memory_data, timestamp = get_data_from_log(logFile)
        if testcase == "large_apk":
            #process large apk metrics
            #find avg cpu usage
            cpu_data = [(a+b+c)/3 for (a,b,c) in zip(cpu_data[0], cpu_data[1], cpu_data[2])]
            #find memory delta
            mem_delta = [(x-memory_data[0]) for x in memory_data]
            #log adb install time
            adbLogFile = os.path.join(args.log_dir, metric+"_adb_install_time.log")
            with open(adbLogFile, 'r') as adb_log:
                install_time = float(adb_log.readline())
            write_perf_data("Install_Time_"+metric,
                            "Install_Time_large_apk",
                            [install_time],
                            [timestamp[0]])
            write_perf_data("CPU_AVG_"+metric,
                            "CPU_Avg",
                            cpu_data,
                            timestamp)
            write_perf_data("Memory_Delta_"+metric,
                            "Memory_Delta",
                            mem_delta,
                            timestamp)
        else:
            if testcase == "idle":
                metrics[metric] = 0
            boot_timestamp[metric] = timestamp[0]
            write_perf_data("CPU0_"+metric,
                            "CPU_Usage",
                            cpu_data[0],
                            timestamp)
            write_perf_data("CPU1_"+metric,
                            "CPU_Usage",
                            cpu_data[1],
                            timestamp)
            write_perf_data("CPU2_"+metric,
                            "CPU_Usage",
                            cpu_data[2],
                            timestamp)
            write_perf_data("Memory_"+metric,
                            "Memory_Usage",
                            memory_data,
                            timestamp)

    # Write boot time benchmark
    if metrics:
        write_boot_time_benchmark(metrics, boot_timestamp)
