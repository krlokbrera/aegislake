"""Arithmetic workload estimate, not a quote. Enter current regional prices explicitly."""

import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument("--runs-per-month", type=int, default=30)
parser.add_argument("--seconds-per-run", type=float, default=300)
parser.add_argument("--cpu", type=float, default=0.5)
parser.add_argument("--memory-gib", type=float, default=1)
parser.add_argument("--remaining-free-vcpu-seconds", type=float, default=0)
parser.add_argument("--remaining-free-gib-seconds", type=float, default=0)
parser.add_argument("--price-per-vcpu-second", type=float, required=True)
parser.add_argument("--price-per-gib-second", type=float, required=True)
args = parser.parse_args()
if any(value < 0 for value in vars(args).values()):
    parser.error("all inputs must be nonnegative")
cpu = args.runs_per_month * args.seconds_per_run * args.cpu
memory = args.runs_per_month * args.seconds_per_run * args.memory_gib
billable_cpu = max(0, cpu - args.remaining_free_vcpu_seconds)
billable_memory = max(0, memory - args.remaining_free_gib_seconds)
print(json.dumps({
    "vcpu_seconds": cpu, "gib_seconds": memory,
    "compute_estimate_in_input_currency": billable_cpu * args.price_per_vcpu_second
        + billable_memory * args.price_per_gib_second,
    "excluded": ["storage", "transactions", "network", "logging", "taxes", "other subscription workloads"],
}, indent=2))
