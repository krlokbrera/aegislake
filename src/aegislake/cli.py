"""Command-line entry points; errors do not print raw event payloads or credentials."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from aegislake.pipeline import run
from aegislake.review import record_review
from aegislake.synthetic import generate


def main() -> None:
    parser = argparse.ArgumentParser(prog="aegislake")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Generate synthetic data and run the benchmark")
    demo.add_argument("--output", type=Path, default=Path("runs"))
    demo.add_argument("--days", type=int, default=30)
    demo.add_argument("--users", type=int, default=50)
    demo.add_argument("--seed", type=int, default=42)
    benchmark = commands.add_parser("run", help="Evaluate canonical labeled JSONL")
    benchmark.add_argument("--input", type=Path, required=True)
    benchmark.add_argument("--output", type=Path, default=Path("runs"))
    for command in (demo, benchmark):
        command.add_argument("--train-days", type=int, default=18)
        command.add_argument("--validation-days", type=int, default=6)
        command.add_argument("--capacity", type=int, default=25)
    review = commands.add_parser("review", help="Record a human review locally")
    review.add_argument("--run", type=Path, required=True)
    review.add_argument("--alert-id", required=True)
    review.add_argument("--decision", choices=["true_positive", "false_positive", "needs_context"], required=True)
    review.add_argument("--reviewer", required=True)
    review.add_argument("--note", default="")
    adapter = commands.add_parser("adapt-entra", help="Pseudonymize a local Graph JSON export")
    adapter.add_argument("--input", type=Path, required=True)
    adapter.add_argument("--output", type=Path, required=True)
    scoring = commands.add_parser("score", help="Score a future unlabeled batch using an existing run")
    scoring.add_argument("--reference", type=Path, required=True)
    scoring.add_argument("--input", type=Path, required=True)
    scoring.add_argument("--output", type=Path, required=True)
    scoring.add_argument("--allow-domain-shift", action="store_true")
    cloud = commands.add_parser("publish", help="Upload only synthetic reports to private Azure storage")
    cloud.add_argument("--run", type=Path, required=True)
    cloud.add_argument("--account", required=True)
    cloud.add_argument("--container", default="reports")
    web = commands.add_parser("serve", help="Explore completed batches in a local interactive dashboard")
    web.add_argument("--runs", type=Path, default=Path("runs"))
    web.add_argument("--port", type=int, default=8767)
    args = parser.parse_args()
    if args.command in {"demo", "run"}:
        if args.command == "demo":
            source = args.output / "inputs" / f"demo-{args.days}-{args.users}-{args.seed}.jsonl"
            generate(source, days=args.days, users=args.users, seed=args.seed)
        else:
            source = args.input
        destination = run(source, args.output, train_days=args.train_days, validation_days=args.validation_days,
                          capacity=args.capacity, seed=getattr(args, "seed", 42), synthetic=args.command == "demo")
        print(destination.resolve())
    elif args.command == "review":
        record_review(args.run, args.alert_id, args.decision, args.reviewer, args.note)
        print("Review recorded locally")
    elif args.command == "adapt-entra":
        from aegislake.adapters import adapt_entra

        secret = os.environ.get("AEGIS_PSEUDONYM_KEY", "").encode()
        if len(secret) < 32:
            parser.error("set AEGIS_PSEUDONYM_KEY to a private key of at least 32 bytes")
        print(f"Adapted {adapt_entra(args.input, args.output, secret)} events")
    elif args.command == "score":
        from aegislake.scoring import score

        print(score(args.reference, args.input, args.output, allow_domain_shift=args.allow_domain_shift).resolve())
    elif args.command == "publish":
        from aegislake.azure import publish

        print(f"Published {len(publish(args.run, args.account, args.container))} private synthetic report objects")
    elif args.command == "serve":
        from aegislake.dashboard_server import serve

        serve(args.runs, args.port)


if __name__ == "__main__":
    main()
