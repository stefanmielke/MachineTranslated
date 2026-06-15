import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from check_translated_files import compare_files
from create_index_file_per_serie import create_index
from generate_rss_feed import add_new_items_to_rss
from merge_chapters import merge_files


ROOT_DIR = Path(__file__).resolve().parents[2]
TRANSLATIONS_DIR = ROOT_DIR / "docs" / "translations"
OPENAI_API_BASE = "https://api.openai.com/v1"
OPENAI_BATCH_JOBS_PATH = TRANSLATIONS_DIR / "openai_batch_jobs.json"
TERMINAL_FAILURE_STATUSES = {"failed", "expired", "cancelled"}


def load_env_file(path):
    if not path.exists():
        return {}

    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value

    return values


ENV_VALUES = load_env_file(ROOT_DIR / ".env")


def env_value(name):
    return os.getenv(name) or ENV_VALUES.get(name)


class Progress:
    def __init__(self, steps):
        self.steps = steps
        self.total = len(steps)
        self.current = 0

    def start(self, label):
        self.current += 1
        remaining = self.total - self.current
        width = 28
        filled = int(width * (self.current - 1) / self.total)
        bar = "#" * filled + "-" * (width - filled)
        print(f"\n[{bar}] Step {self.current}/{self.total}: {label}")
        print(f"Remaining after this step: {remaining}")

    def finish(self, label):
        width = 28
        filled = int(width * self.current / self.total)
        bar = "#" * filled + "-" * (width - filled)
        print(f"[{bar}] Finished: {label}")


def openai_headers(api_key, project=None):
    headers = {"Authorization": f"Bearer {api_key}"}
    if project:
        headers["OpenAI-Project"] = project
    return headers


def openai_get_json(path, api_key, project=None):
    request = Request(f"{OPENAI_API_BASE}{path}", headers=openai_headers(api_key, project=project), method="GET")
    try:
        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API request failed with HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"OpenAI API request failed: {exc.reason}") from exc


def openai_get_bytes(path, api_key, project=None):
    request = Request(f"{OPENAI_API_BASE}{path}", headers=openai_headers(api_key, project=project), method="GET")
    try:
        with urlopen(request) as response:
            return response.read()
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API request failed with HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"OpenAI API request failed: {exc.reason}") from exc


def read_submission(series_dir):
    submission_path = series_dir / "openai_batch_submission.json"
    if not submission_path.exists():
        return {}, submission_path

    return json.loads(submission_path.read_text(encoding="utf-8")), submission_path


def write_submission(submission_path, submission):
    submission_path.write_text(json.dumps(submission, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")


def read_openai_batch_jobs():
    if not OPENAI_BATCH_JOBS_PATH.exists():
        return {"jobs": []}

    return json.loads(OPENAI_BATCH_JOBS_PATH.read_text(encoding="utf-8"))


def write_openai_batch_jobs(registry):
    OPENAI_BATCH_JOBS_PATH.parent.mkdir(parents=True, exist_ok=True)
    OPENAI_BATCH_JOBS_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")


def waiting_jobs(registry):
    return [
        job for job in registry.get("jobs", [])
        if job.get("workflow_status") == "waiting"
    ]


def update_registry_job(registry, batch_id, **updates):
    for job in registry.get("jobs", []):
        if job.get("batch_id") == batch_id:
            job.update(updates)
            return


def get_batch_id(args, series_dir):
    if args.batch_id:
        return args.batch_id

    submission, _ = read_submission(series_dir)
    batch_id = submission.get("batch", {}).get("id")
    if not batch_id:
        raise RuntimeError(
            f"No batch id found. Pass --batch-id or run setup_syosetu_series.py with --submit-openai-batch first."
        )

    return batch_id


def save_batch_status(series_dir, batch):
    submission, submission_path = read_submission(series_dir)
    submission["batch"] = batch
    write_submission(submission_path, submission)
    print(f"Saved latest batch status: {submission_path}")


def save_batch_status_for_job(series_dir, batch, registry=None):
    save_batch_status(series_dir, batch)
    if registry is not None:
        update_registry_job(
            registry,
            batch["id"],
            openai_status=batch.get("status"),
            output_file_id=batch.get("output_file_id"),
            updated_at=batch.get("created_at"),
        )


def download_batch_output(series_dir, batch, api_key, project=None):
    output_file_id = batch.get("output_file_id")
    if not output_file_id:
        raise RuntimeError("The batch is completed, but OpenAI did not return an output_file_id.")

    output_path = series_dir / "en" / "batch_output.jsonl"
    output_path.write_bytes(openai_get_bytes(f"/files/{output_file_id}/content", api_key, project=project))
    print(f"Downloaded OpenAI batch output: {output_path}")
    return output_path


def unpack_batch_output(output_path):
    output_folder = output_path.parent
    created = 0

    with output_path.open("r", encoding="utf-8-sig") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                result = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"Warning: error decoding JSON at line {line_number}: {exc}")
                continue

            custom_id = result.get("custom_id")
            message = result.get("response", {}).get("body", {}).get("choices", [{}])[0].get("message", {})
            content = message.get("content")

            if not custom_id:
                print(f"Warning: missing custom_id at line {line_number}")
                continue
            if content is None:
                print(f"Warning: missing translated content for {custom_id}")
                continue

            (output_folder / custom_id).write_text(content, encoding="utf-8")
            created += 1

    print(f"Unpacked translated files: {created}")


def merge_output(series_dir):
    merge_files(str(series_dir / "jp"), str(series_dir / "en"), str(series_dir / "out"))
    print("Merged translated files into markdown output.")


def run_step(progress, label, func):
    progress.start(label)
    result = func()
    progress.finish(label)
    return result


def parse_args():
    parser = argparse.ArgumentParser(
        description="Check an OpenAI Batch API translation job and finalize site files when it is completed."
    )
    parser.add_argument("series_id", nargs="?", help="Series id under docs/translations, for example n1234ab.")
    parser.add_argument("--all", action="store_true", help="Check every waiting job in docs/translations/openai_batch_jobs.json.")
    parser.add_argument("--batch-id", help="Override the batch id saved in openai_batch_submission.json.")
    parser.add_argument("--openai-api-key", default=env_value("OPENAI_API_KEY"), help="OpenAI API key. Defaults to OPENAI_API_KEY from the environment or .env.")
    parser.add_argument("--openai-project", default=env_value("OPENAI_PROJECT"), help="Optional OpenAI project id from the environment, .env, or CLI.")
    parser.add_argument("--fix-line-counts", action="store_true", help="Run check_translated_files.py before merging output.")
    return parser.parse_args()


def finalize_one(args, series_id, batch_id=None, registry=None):
    series_dir = TRANSLATIONS_DIR / series_id
    if not series_dir.exists():
        raise RuntimeError(f"Series folder does not exist: {series_dir}")

    if batch_id is None:
        batch_id = get_batch_id(args, series_dir)

    status_progress = Progress(["Retrieve OpenAI batch status"])
    batch = run_step(
        status_progress,
        "Retrieve OpenAI batch status",
        lambda: openai_get_json(f"/batches/{batch_id}", args.openai_api_key, args.openai_project),
    )
    save_batch_status_for_job(series_dir, batch, registry=registry)

    status = batch.get("status")
    print(f"OpenAI batch status: {status}")

    if status != "completed":
        if status in TERMINAL_FAILURE_STATUSES:
            if registry is not None:
                update_registry_job(registry, batch_id, workflow_status="failed", openai_status=status)
            raise RuntimeError(f"OpenAI batch ended with status '{status}'. Check openai_batch_submission.json.")
        print("Batch is not completed yet. Run this script again later.")
        return "waiting"

    steps = ["Download batch output", "Unpack translated files"]
    if args.fix_line_counts:
        steps.append("Fix line count mismatches")
    steps.extend(["Merge chapter output", "Create series indexes", "Update RSS feed"])
    progress = Progress(steps)

    output_path = run_step(
        progress,
        "Download batch output",
        lambda: download_batch_output(series_dir, batch, args.openai_api_key, args.openai_project),
    )
    run_step(progress, "Unpack translated files", lambda: unpack_batch_output(output_path))

    next_step = 2
    if args.fix_line_counts:
        run_step(progress, "Fix line count mismatches", lambda: compare_files(str(series_dir / "en"), str(series_dir / "jp")))
        next_step += 1

    run_step(progress, steps[next_step], lambda: merge_output(series_dir))
    run_step(progress, steps[next_step + 1], lambda: create_index(str(TRANSLATIONS_DIR)))
    run_step(progress, steps[next_step + 2], lambda: add_new_items_to_rss(str(TRANSLATIONS_DIR)))

    print(f"\nDone. Finalized translated output for: {series_dir}")
    if registry is not None:
        update_registry_job(registry, batch_id, workflow_status="completed", openai_status=status)
    return "completed"


def finalize_all(args):
    registry = read_openai_batch_jobs()
    jobs = waiting_jobs(registry)
    if not jobs:
        print(f"No waiting OpenAI batch jobs found in {OPENAI_BATCH_JOBS_PATH}.")
        return

    print(f"Found {len(jobs)} waiting OpenAI batch job(s).")
    completed = 0
    still_waiting = 0
    failed = 0

    for index, job in enumerate(jobs, start=1):
        series_id = job.get("series_id")
        batch_id = job.get("batch_id")
        print(f"\n=== Job {index}/{len(jobs)}: {series_id} ({batch_id}) ===")

        try:
            result = finalize_one(args, series_id, batch_id=batch_id, registry=registry)
        except Exception as exc:
            if job.get("workflow_status") == "failed":
                failed += 1
            else:
                still_waiting += 1
            update_registry_job(registry, batch_id, last_error=str(exc))
            print(f"Job failed: {exc}")
            continue

        if result == "completed":
            completed += 1
        else:
            still_waiting += 1

    write_openai_batch_jobs(registry)
    print(
        f"\nChecked {len(jobs)} job(s): {completed} completed, "
        f"{still_waiting} still waiting, {failed} failed."
    )


def main():
    args = parse_args()
    if not args.openai_api_key:
        raise RuntimeError("Missing OpenAI API key. Set OPENAI_API_KEY in .env or pass --openai-api-key.")
    if args.all and args.batch_id:
        raise RuntimeError("--batch-id can only be used when checking a single series.")
    if not args.all and not args.series_id:
        raise RuntimeError("Pass a series_id or use --all to check every waiting job.")

    if args.all:
        finalize_all(args)
        return

    registry = read_openai_batch_jobs()
    finalize_one(args, args.series_id, registry=registry)
    write_openai_batch_jobs(registry)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        sys.exit(1)
