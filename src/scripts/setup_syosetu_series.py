import argparse
import json
import os
import re
import shutil
import sys
import uuid
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT_DIR = Path(__file__).resolve().parents[2]
TRANSLATIONS_DIR = ROOT_DIR / "docs" / "translations"
CONFIG_PATH = ROOT_DIR / "docs" / "_config.yml"
OPENAI_API_BASE = "https://api.openai.com/v1"
OPENAI_BATCH_JOBS_PATH = TRANSLATIONS_DIR / "openai_batch_jobs.json"


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


def parse_series_id(url):
    path_parts = [part for part in urlparse(url).path.split("/") if part]
    for part in path_parts:
        if re.fullmatch(r"n[0-9a-z]+", part.lower()):
            return part.lower()

    match = re.search(r"(n[0-9a-z]+)", url, re.IGNORECASE)
    if match:
        return match.group(1).lower()

    raise ValueError("Could not find a Syosetsu/Ncode series id in the URL.")


def normalize_syosetu_url(url, series_id):
    parsed = urlparse(url)
    if not parsed.scheme:
        return f"https://ncode.syosetu.com/{series_id}/"
    return f"{parsed.scheme}://{parsed.netloc}/{series_id}/"


def ensure_structure(series_dir):
    for folder in ("jp", "en", "out"):
        path = series_dir / folder
        path.mkdir(parents=True, exist_ok=True)
        print(f"Ready: {path}")


def write_metadata(series_dir, args, source_url):
    data_path = series_dir / "data.json"
    existing = {}
    if data_path.exists() and data_path.read_text(encoding="utf-8").strip():
        try:
            existing = json.loads(data_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"Warning: replacing invalid JSON in {data_path}")

    data = {
        "name": args.name or existing.get("name") or args.series_id,
        "novel-updates-link": args.novel_updates_link or existing.get("novel-updates-link", ""),
        "source-link": source_url,
        "ml-used": args.ml_used or existing.get("ml-used") or "Not translated yet",
    }

    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    print(f"Updated: {data_path}")


def ensure_config_excludes(series_id):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        lines = CONFIG_PATH.read_text(encoding="utf-8").splitlines()
    else:
        lines = ["remote_theme: pages-themes/midnight@v0.2.0", "plugins:", "- jekyll-remote-theme", "exclude:"]

    if "exclude:" not in lines:
        lines.append("exclude:")

    wanted = [
        f"- docs/translations/{series_id}/data.json",
        f"- docs/translations/{series_id}/en",
        f"- docs/translations/{series_id}/jp",
    ]

    changed = False
    for entry in wanted:
        if entry not in lines:
            lines.append(entry)
            changed = True

    if changed:
        CONFIG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Updated: {CONFIG_PATH}")
    else:
        print(f"Already up to date: {CONFIG_PATH}")


def copy_jp_to_en(series_dir, overwrite=False):
    jp_dir = series_dir / "jp"
    en_dir = series_dir / "en"
    copied = 0
    skipped = 0

    for source in sorted(jp_dir.glob("chapter_*.txt")):
        target = en_dir / source.name
        if target.exists() and not overwrite:
            skipped += 1
            continue
        shutil.copy2(source, target)
        copied += 1

    print(f"Seeded English folder: {copied} copied, {skipped} skipped.")


def create_openai_batch_request(series_dir, model, overwrite=False):
    en_dir = series_dir / "en"
    batch_file = en_dir / "batch_requests.jsonl"
    if batch_file.exists() and not overwrite:
        print(f"OpenAI batch request file already exists: {batch_file}")
        return

    from translate_files_openai_batch import prepare_batch_files

    prepare_batch_files(str(en_dir), model=model)


def openai_headers(api_key, project=None, content_type=None):
    headers = {"Authorization": f"Bearer {api_key}"}
    if project:
        headers["OpenAI-Project"] = project
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def openai_request(url, headers, data):
    request = Request(url, data=data, headers=headers, method="POST")
    try:
        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API request failed with HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"OpenAI API request failed: {exc.reason}") from exc


def encode_multipart_form(fields, files):
    boundary = f"----codex-{uuid.uuid4().hex}"
    body = bytearray()

    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")

    for name, file_path in files.items():
        path = Path(file_path)
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            f'Content-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'.encode("utf-8")
        )
        body.extend(b"Content-Type: application/jsonl\r\n\r\n")
        body.extend(path.read_bytes())
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    return bytes(body), f"multipart/form-data; boundary={boundary}"


def submit_openai_batch(series_dir, api_key, project=None):
    if not api_key:
        raise RuntimeError("Missing OpenAI API key. Set OPENAI_API_KEY or pass --openai-api-key.")

    batch_file = series_dir / "en" / "batch_requests.jsonl"
    if not batch_file.exists():
        raise RuntimeError(f"OpenAI batch request file does not exist: {batch_file}")

    print(f"Uploading OpenAI batch request file: {batch_file}")
    file_body, file_content_type = encode_multipart_form(
        fields={"purpose": "batch"},
        files={"file": batch_file},
    )
    uploaded_file = openai_request(
        f"{OPENAI_API_BASE}/files",
        openai_headers(api_key, project=project, content_type=file_content_type),
        file_body,
    )

    print(f"Creating OpenAI batch for uploaded file: {uploaded_file['id']}")
    batch_body = json.dumps(
        {
            "input_file_id": uploaded_file["id"],
            "endpoint": "/v1/chat/completions",
            "completion_window": "24h",
            "metadata": {
                "series_id": series_dir.name,
                "source": "MachineTranslated setup_syosetu_series.py",
            },
        }
    ).encode("utf-8")
    batch = openai_request(
        f"{OPENAI_API_BASE}/batches",
        openai_headers(api_key, project=project, content_type="application/json"),
        batch_body,
    )

    submission_path = series_dir / "openai_batch_submission.json"
    submission = {
        "input_jsonl": str(batch_file),
        "uploaded_file": uploaded_file,
        "batch": batch,
    }
    submission_path.write_text(json.dumps(submission, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")

    print(f"OpenAI batch submitted: {batch['id']} ({batch['status']})")
    print(f"Saved submission details: {submission_path}")
    record_openai_batch_job(series_dir, submission_path, batch)


def read_openai_batch_jobs():
    if not OPENAI_BATCH_JOBS_PATH.exists():
        return {"jobs": []}

    return json.loads(OPENAI_BATCH_JOBS_PATH.read_text(encoding="utf-8"))


def write_openai_batch_jobs(registry):
    OPENAI_BATCH_JOBS_PATH.parent.mkdir(parents=True, exist_ok=True)
    OPENAI_BATCH_JOBS_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")


def record_openai_batch_job(series_dir, submission_path, batch):
    registry = read_openai_batch_jobs()
    jobs = registry.setdefault("jobs", [])
    batch_id = batch["id"]
    job = {
        "series_id": series_dir.name,
        "batch_id": batch_id,
        "submission_path": str(submission_path),
        "openai_status": batch.get("status"),
        "workflow_status": "waiting",
        "output_file_id": batch.get("output_file_id"),
        "created_at": batch.get("created_at"),
        "updated_at": batch.get("created_at"),
    }

    for index, existing in enumerate(jobs):
        if existing.get("batch_id") == batch_id:
            jobs[index] = {**existing, **job}
            break
    else:
        jobs.append(job)

    write_openai_batch_jobs(registry)
    print(f"Recorded waiting OpenAI batch job: {OPENAI_BATCH_JOBS_PATH}")


def download_syosetu_chapters(source_url, output_dir, skip_existing):
    try:
        from get_chapter_links_from_syosetu import main as download_chapters
    except ModuleNotFoundError as exc:
        missing = exc.name
        raise RuntimeError(
            f"Missing Python dependency '{missing}'. Install the existing downloader dependencies "
            "before running the download step."
        ) from exc

    download_chapters(source_url, str(output_dir), skip_existing)


def run_step(progress, label, func):
    progress.start(label)
    func()
    progress.finish(label)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a Syosetsu series folder and run every non-translation setup step."
    )
    parser.add_argument("url", help="Syosetsu/Ncode series URL, for example https://ncode.syosetu.com/n1234ab/")
    parser.add_argument("--series-id", help="Override the series id parsed from the URL.")
    parser.add_argument("--name", help="Series display name for data.json.")
    parser.add_argument("--novel-updates-link", default="", help="Novel Updates URL for data.json.")
    parser.add_argument("--ml-used", default="", help="Machine translation label for data.json.")
    parser.add_argument("--skip-existing", action="store_true", help="Do not re-download existing jp chapter files.")
    parser.add_argument("--overwrite-en", action="store_true", help="Overwrite existing en chapter files when seeding from jp.")
    parser.add_argument("--skip-openai-batch", action="store_true", help="Skip creating en/batch_requests.jsonl for OpenAI batch upload.")
    parser.add_argument("--overwrite-openai-batch", action="store_true", help="Recreate an existing OpenAI batch request file.")
    parser.add_argument("--model", default="gpt-5-mini", help="OpenAI model to use in batch_requests.jsonl.")
    parser.add_argument("--submit-openai-batch", action="store_true", help="Upload en/batch_requests.jsonl and create an OpenAI Batch API job.")
    parser.add_argument("--openai-api-key", default=env_value("OPENAI_API_KEY"), help="OpenAI API key. Defaults to OPENAI_API_KEY from the environment or .env.")
    parser.add_argument("--openai-project", default=env_value("OPENAI_PROJECT"), help="Optional OpenAI project id from the environment, .env, or CLI.")
    return parser.parse_args()


def main():
    args = parse_args()
    args.series_id = (args.series_id or parse_series_id(args.url)).lower()
    source_url = normalize_syosetu_url(args.url, args.series_id)
    series_dir = TRANSLATIONS_DIR / args.series_id

    steps = [
        "Create folder structure",
        "Write metadata",
        "Update Jekyll excludes",
        "Download Syosetsu chapters",
        "Seed en folder from jp",
    ]
    if not args.skip_openai_batch:
        steps.append("Create OpenAI batch request")
    if args.submit_openai_batch:
        steps.append("Submit OpenAI batch")

    progress = Progress(steps)

    run_step(progress, steps[0], lambda: ensure_structure(series_dir))
    run_step(progress, steps[1], lambda: write_metadata(series_dir, args, source_url))
    run_step(progress, steps[2], lambda: ensure_config_excludes(args.series_id))
    run_step(progress, steps[3], lambda: download_syosetu_chapters(source_url, series_dir / "jp", args.skip_existing))
    run_step(progress, steps[4], lambda: copy_jp_to_en(series_dir, args.overwrite_en))

    next_step = 5
    if not args.skip_openai_batch:
        run_step(progress, steps[next_step], lambda: create_openai_batch_request(series_dir, args.model, args.overwrite_openai_batch))
        next_step += 1
    if args.submit_openai_batch:
        run_step(
            progress,
            steps[next_step],
            lambda: submit_openai_batch(series_dir, args.openai_api_key, args.openai_project),
        )
        next_step += 1

    print(f"\nDone. Series folder: {series_dir}")
    if not args.skip_openai_batch:
        print(f"OpenAI batch request file: {series_dir / 'en' / 'batch_requests.jsonl'}")
    if args.submit_openai_batch:
        print(f"Check and finalize it with: python src/scripts/finalize_openai_batch.py {args.series_id}")
    else:
        print("Translation submission was skipped; submit the batch later or rerun with --submit-openai-batch.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        sys.exit(1)
