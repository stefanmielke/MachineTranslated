# Machine Translations

### light novel translations by machines

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
1. Create the following folders:
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
        - add exclusion folders on `docs/_config.yaml` (copy from other series).
1. Run `get_chapter_links_from_syosetu.py` to download the chapters on the format expected (if from syosetu, if not, you have to download them).
1. Copy the `jp` files on the `en` folder, to start with the translation with the original files.
1. Run `merge_chapters.py` to create the initial files on the `/out` folder.
1. Run `create_index_file_per_serie.py` to generate the `index.md` files for the new serie.

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