"""Manual ETL commands. No real source is downloaded without an explicit flag."""

import argparse
import json
import os
import stat
import sys
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings
from app.db import create_database_engine
from app.etl.download import downloaded
from app.etl.errors import ETLError
from app.etl.service import Pipeline
from app.etl.source import SOURCES


def require_raw_tmpfs():
    path = Path("/etl-private")
    if not path.is_dir() or path.stat().st_uid != os.getuid():
        raise ETLError("raw_tmpfs_required")
    if stat.S_IMODE(path.stat().st_mode) != 0o700:
        raise ETLError("raw_tmpfs_required")
    mounts = Path("/proc/mounts").read_text().splitlines()
    if not any(line.split()[1:3] == ["/etl-private", "tmpfs"] for line in mounts):
        raise ETLError("raw_tmpfs_required")


def main(argv=None):
    parser = argparse.ArgumentParser(description="CompanyWatch ETL (manual approval required)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("sources")
    ingest = commands.add_parser("ingest")
    ingest.add_argument("--edition", choices=SOURCES, required=True)
    ingest.add_argument("--allow-real-download", action="store_true")
    ingest.add_argument("--expected-sha256")
    report = commands.add_parser("report")
    report.add_argument("version")
    approve = commands.add_parser("approve")
    approve.add_argument("version")
    approve.add_argument("--report-hash", required=True)
    publish = commands.add_parser("publish")
    publish.add_argument("version")
    publish.add_argument("--approval", required=True)
    diff = commands.add_parser("diff")
    diff.add_argument("old_version")
    diff.add_argument("new_version")
    quality_compare = commands.add_parser("quality-compare")
    quality_compare.add_argument("old_version")
    quality_compare.add_argument("new_version")
    args = parser.parse_args(argv)
    if args.command == "sources":
        print(
            json.dumps(
                {
                    edition: {"url": source.url, "size": source.size, "license": "CC-BY-4.0"}
                    for edition, source in SOURCES.items()
                }
            )
        )
        return 0
    if args.command == "ingest" and not args.allow_real_download:
        print("real_download_requires_explicit_consent", file=sys.stderr)
        return 2
    if args.command == "ingest":
        try:
            require_raw_tmpfs()
        except (ETLError, OSError):
            print("raw_tmpfs_required", file=sys.stderr)
            return 2
    engine = None
    try:
        engine = create_database_engine(Settings.from_env())
        pipeline = Pipeline(engine)
        if args.command == "ingest":
            source = SOURCES[args.edition]
            with downloaded(
                source, Path("/etl-private"), expected_sha256=args.expected_sha256
            ) as artifact:
                version = pipeline.ingest(
                    artifact.path,
                    source,
                    transfer={
                        "final_url": artifact.final_url,
                        "etag": artifact.etag,
                        "sha256": artifact.sha256,
                        "observed_bytes": artifact.size,
                    },
                )
                result = pipeline.report(version)
        elif args.command == "report":
            result = pipeline.report(args.version)
        elif args.command == "approve":
            result = {"approval": pipeline.approve(args.version, args.report_hash)}
        elif args.command == "publish":
            pipeline.publish(args.version, args.approval)
            result = {"version": args.version, "state": "published"}
        elif args.command == "quality-compare":
            result = pipeline.quality_compare(args.old_version, args.new_version)
        else:
            result = pipeline.diff(args.old_version, args.new_version)
        print(json.dumps(result, sort_keys=True, ensure_ascii=False))
        return 0
    except ETLError as error:
        print(str(error), file=sys.stderr)
        return 2
    except SQLAlchemyError:
        print("database_error", file=sys.stderr)
        return 2
    except (OSError, ValueError):
        print("configuration_or_artifact_error", file=sys.stderr)
        return 2
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
