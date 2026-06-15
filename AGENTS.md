# AGENTS.md

Guidance for coding agents working in this repository.

## Project Overview

This repo publishes machine-translated web novel chapters through GitHub Pages. The generated site lives in `docs/`, and the translation automation lives in `src/scripts/`.

Important paths:

- `README.md`: user-facing workflow documentation.
- `src/scripts/`: Python command-line tools and the Tkinter OpenAI batch UI.
- `docs/_config.yml`: Jekyll config. New series must exclude `data.json`, `en`, and `jp` from the published site.
- `docs/index.md`: manually maintained public series list.
- `docs/feed.xml`: generated RSS feed.
- `docs/translations/{series_id}/`: one series folder.
- `docs/translations/{series_id}/jp/`: original Japanese chapter text files.
- `docs/translations/{series_id}/en/`: translated chapter text files and OpenAI batch files.
- `docs/translations/{series_id}/out/`: generated Markdown chapters published by the site.
- `docs/translations/{series_id}/data.json`: series metadata and optional `translation-context` prompt notes.

The repo contains thousands of generated chapter files. Use targeted searches and avoid broad formatting or churn in `docs/translations`.

## Environment

Use Python from the repo root unless a script explicitly expects another working directory.

There is no requirements file. Known external dependencies:

- `requests`
- `beautifulsoup4`

Most other scripts use only the Python standard library. OpenAI scripts use direct HTTP calls through `urllib`.

Local secrets:

- `.env` is intentionally ignored by git.
- `.env.example` documents `OPENAI_API_KEY` and optional `OPENAI_PROJECT`.
- Never commit real API keys.

Git may report dubious ownership in this sandbox. If git status is needed, ask before changing global Git config.

## Core Invariants

- Chapter files are named `chapter_0001.txt`, `chapter_0002.txt`, etc.
- Each `jp` chapter and matching `en` chapter must have the same number of lines before merging.
- Preserve blank markers exactly. Existing scripts use both `<blank>` and `<b>` as blank-line markers.
- Image lines use Markdown image syntax, for example `![alt](url)`, and should remain untranslated.
- `merge_chapters.py` skips files when `jp` and `en` line counts differ.
- Manual translation edits should normally touch only `docs/translations/{series_id}/en/`.
- `out` files, per-series `index.md` files, and `feed.xml` are generated outputs.

## Preferred New Series Workflow

For a Syosetu/Ncode series, prefer the newer setup script:

```powershell
python src/scripts/setup_syosetu_series.py https://ncode.syosetu.com/n1234ab/ --name "Series Name" --skip-existing
```

This creates `docs/translations/{series_id}/`, downloads `jp` chapters, seeds `en` from `jp`, updates Jekyll excludes, writes `data.json`, and creates `en/batch_requests.jsonl`.

Useful flags:

- `--series-id n1234ab`: override the ID parsed from the URL.
- `--novel-updates-link URL`: set metadata.
- `--ml-used LABEL`: set metadata.
- `--model gpt-5-mini`: choose the model for generated batch requests. Default is `gpt-5-mini`.
- `--overwrite-en`: replace existing seeded `en` files from `jp`.
- `--overwrite-openai-batch`: recreate an existing `en/batch_requests.jsonl`.
- `--skip-openai-batch`: skip batch request generation.
- `--submit-openai-batch`: upload the JSONL and create an OpenAI Batch API job.

If `--submit-openai-batch` is used, the script writes:

- `docs/translations/{series_id}/openai_batch_submission.json`
- `docs/translations/openai_batch_jobs.json`

Finalizing a completed batch:

```powershell
python src/scripts/finalize_openai_batch.py n1234ab
```

Check all tracked waiting jobs:

```powershell
python src/scripts/finalize_openai_batch.py --all
```

Use `--fix-line-counts` when line count mismatches are expected. It runs `check_translated_files.py` before merging, but it only handles a narrow blank-marker mismatch case.

## UI Workflow

The Tkinter manager can be launched with:

```powershell
python src/scripts/openai_batch_ui.py
```

It can edit series metadata, save OpenAI credentials to `.env`, run setup, check tracked batch jobs, and finalize completed jobs.

Launching GUI apps may require user approval in sandboxed environments.

## Older Manual Workflow

These scripts are still present and useful for focused operations:

```powershell
python src/scripts/create_folder_structure.py n1234ab
python src/scripts/get_chapter_links_from_syosetu.py https://ncode.syosetu.com/n1234ab/ docs/translations/n1234ab/jp --skip-existing
python src/scripts/translate_files_openai_batch.py docs/translations/n1234ab/en gpt-5-mini
python src/scripts/unpack_files_openai_batch.py docs/translations/n1234ab/en/batch_output.jsonl
python src/scripts/check_translated_files.py docs/translations/n1234ab
python src/scripts/merge_chapters.py docs/translations/n1234ab
python src/scripts/create_index_file_per_serie.py docs/translations
python src/scripts/generate_rss_feed.py docs/translations
```

DeepL-style merge/split helpers:

```powershell
python src/scripts/batch_merge_chapters.py docs/translations/n1234ab/en
python src/scripts/split_merge_chapters.py docs/translations/n1234ab/en
```

## Validation Commands

There is no automated test suite. Use targeted script checks based on the change.

For metadata/index/RSS changes:

```powershell
python src/scripts/create_index_file_per_serie.py docs/translations
python src/scripts/generate_rss_feed.py docs/translations
```

For one translated series:

```powershell
python src/scripts/check_translated_files.py docs/translations/n1234ab
python src/scripts/merge_chapters.py docs/translations/n1234ab
python src/scripts/create_index_file_per_serie.py docs/translations
```

For Python syntax after script edits:

```powershell
python -m compileall src/scripts
```

If network access is needed for Syosetu or OpenAI calls, expect sandbox approval to be required.

## Editing Guidance

- Keep edits scoped. Avoid touching generated chapter files unless the task is specifically about those chapters.
- Do not rewrite all indexes or RSS unless the task requires generation.
- When changing a script, preserve its current command-line behavior unless explicitly improving it.
- Prefer root-aware paths via `Path(__file__).resolve().parents[2]` for new scripts or major updates.
- Preserve UTF-8 reads and writes; chapter and metadata files contain Japanese text.
- Do not normalize or re-encode existing translation text unnecessarily.
- If adding a new series manually, also update `docs/_config.yml` excludes and consider whether `docs/index.md` should list it.

## Common Gotchas

- `create_folder_structure.py` appends to `docs/_config.yml` and can duplicate entries; `setup_syosetu_series.py` is safer.
- `create_index_file_per_serie.py` reads the first `# ` heading from each output chapter. Malformed output can break index creation.
- `generate_rss_feed.py` only appends new items; it does not remove or reorder old feed items.
- `translate_files_openai_batch.py` writes `batch_requests.jsonl` into the input folder and includes every `.txt` file there.
- `finalize_openai_batch.py --all` mutates the shared OpenAI batch job registry.
- `docs/index.md` appears manually maintained; generation scripts do not update it.
