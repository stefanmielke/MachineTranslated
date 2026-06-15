# Machine Translations

### web novel translations by machines

- Website: [https://stefanmielke.github.io/MachineTranslated/](https://stefanmielke.github.io/MachineTranslated/)

---

### Objective

The objective of this project is to serve as a base for other translations. Not necessarily to be used as is.

### Process

All translations were done using ML. Originally translated with DeepL and GPT4o-mini.

#### Steps:

1. Run `get_chapter_links_from_syosetu.py` to download the chapters on the format expected.
1. Run `batch_merge_chapters.py` to merge chapters together to translate entire files.
1. Import the files using DeepL "Translate files" option.
1. Run `split_merge_chapters.py` on the output of the translations to get back the original chapter files, now translated.
    1. Optional: here you can update the translation files manually.
1. Run `merge_chapters.py` to merge the jp with the en translation and generate the final output of each chapter.
1. Run `create_index_file_per_serie.py` to generate the `index.md` files for each serie.

#### Syosetsu setup with OpenAI batch:

For a new Syosetsu series, prepare the local files with:

```bash
python src/scripts/setup_syosetu_series.py https://ncode.syosetu.com/n1234ab/ --name "Series Name" --skip-existing
```

The setup script creates the folder structure, downloads `jp` chapters, seeds `en` from `jp`, and creates `en/batch_requests.jsonl` for OpenAI batch upload. Use `--model` to choose the OpenAI model for the generated batch requests, for example `--model gpt-5`, `--model gpt-5-mini`, or `--model gpt-5-nano`.

To also upload the JSONL file and create an OpenAI Batch API job, set `OPENAI_API_KEY` and add `--submit-openai-batch`:

```bash
python src/scripts/setup_syosetu_series.py https://ncode.syosetu.com/n1234ab/ --name "Series Name" --skip-existing --submit-openai-batch
```

The created batch/file IDs are saved to `docs/translations/{series_id}/openai_batch_submission.json`.
Submitted jobs are also tracked in `docs/translations/openai_batch_jobs.json` so they can be checked in bulk.

After OpenAI finishes the batch, check and finalize the translated files with:

```bash
python src/scripts/finalize_openai_batch.py n1234ab
```

To check every waiting job and finalize whichever ones are complete, run:

```bash
python src/scripts/finalize_openai_batch.py --all
```

The finalize script checks the OpenAI Batch API. If the batch is still running, it stops and tells you to run it again later. If the batch is complete, it downloads the batch output, unpacks translated chapter files into `en`, merges `jp` and `en` into `out`, updates series indexes, and updates the RSS feed. Add `--fix-line-counts` if you want it to run `check_translated_files.py` before merging.

You can also use the simple Python UI:

```bash
python src/scripts/openai_batch_ui.py
```

The UI opens to the translations manager, where you can browse all translation folders, edit each `data.json` field with text boxes, add `translation-context` notes for character names/settings/terminology, list JP chapters once, see whether each chapter has translated output, and open JP/EN/output chapter files in your default external editor. Press `Working Translations` to open the batch/job controls. That window can save `OPENAI_API_KEY` and optional `OPENAI_PROJECT` to `.env`, test the API key, select `gpt-5`, `gpt-5-mini`, `gpt-5-nano`, `gpt-4o`, or `gpt-4o-mini` from a model dropdown, run the setup script, show tracked OpenAI batch jobs, reload the local job list, check all waiting jobs against OpenAI, and finalize completed jobs. A green `API key: OK` status means the key is saved and a test request to OpenAI succeeded. Press `Check All Waiting` whenever you want to pull the latest OpenAI status for every waiting job.

You can keep the API key in a local `.env` file at the repository root. The real `.env` file is ignored by git; use `.env.example` as the template:

```env
OPENAI_API_KEY=sk-your-api-key-here
# Optional: uncomment when using a specific OpenAI project.
# OPENAI_PROJECT=proj_your_project_id_here
```

The script reads OpenAI settings in this order: CLI flags, environment variables, then `.env`.

---

### Contributions

We are open for PR that help with the translations, as long as they are machine translations.

If you want a new series translated, please open an issue with the series name and source.

#### Guidelines:

**For translations of existing series:**
- Only update the files on the "en" folder.
- The 'jp' and 'en' files have to have the same amount of lines, so the merge can work.
- `<blank>` tags are added to add the same amount of spacing as the original work, so remember to keep them exact.
- Images can't be translated, only the original is used (but the translation should still have an empty line on its place).

**For new series:**
1. Run `create_folder_structure.py` passing the series_id to create the initial structure:
    - inside `/docs/translations/{series_id}`:
        - `/jp`: to put the original chapters.
        - `/en`: to put the English translations.
        - `/out`: to put the final `md` files that will go to the website.
        - `data.json`: for additional info of the series.
            - the json contains:
                - `name`: name of the series (usually from Novel Updates).
                - `novel-updates-link`: series URL from Novel Updates.
                - `source-link`: link to the original source of the series.
                - `ml-used`: machine translation tool used.
                - `translation-context`: optional character, setting, and terminology notes appended to the OpenAI translation system prompt.
1. Run `get_chapter_links_from_syosetu.py` to download the chapters on the format expected (if from syosetu, if not, you have to download them).
    - pass the URL from syosetsu and the output folder (the `/jp` folder created above)
1. Copy the `jp` files on the `en` folder, to start with the translation with the original files.
1. For translation:
    1. If using DeepL:
        1. Run `batch_merge_chapters.py` to merge the files into one.
        1. Upload the file for translation.
        1. Run `split_merge_chapters.py` to split them again, now translated.
    1. If using OpenAI:
        1. Run `translate_files_openai_batch.py` to merge the files into one `jsonl` file.
        1. Upload the file for translation using the batch service.
        1. Run `unpack_files_openai_batch.py` to split them again, now translated.
1. Run `merge_chapters.py` to create the initial files on the `/out` folder.
    - You may need to fix the paragraphs, since they need to match between the `jp` and `en` files.
1. Run `create_index_file_per_serie.py ..\..\docs\translations\` to generate the `index.md` files for the new serie.
1. Run `generate_rss_feed.py ..\..\docs\translations\` to update the rss feed.


**Format of the original source files:**
- Every line should be used as it is on the original source.
- It has to be on text form, to ease the translation tools.
- Blank lines should use `<blank>` tag, to also ease on the translation tools (they don't translate the tag, but keep them as-is), but also by the merge tool that generates the output (they get translated to `&nbsp;` to keep an empty line).
- Images should go directly to md format (`![alt_text](url)`).

---

### Future Improvements

- Create the website entirely using github actions.
    - Have to create home index.md automatically.
    - Move files out of docs folder (or use another folder for output?).
    - Run py scripts during build (`merge_chapters.py` and `create_index_file_per_serie.py`).
