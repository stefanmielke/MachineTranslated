# Machine Translations

### light novel translations by machines

- Website: [https://stefanmielke.github.io/MachineTranslated/](https://stefanmielke.github.io/MachineTranslated/)

---

### Process

All translations were done using ML. Originally translated with DeepL.

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

We are open for PR that help with the translations.

#### Guidelines:

- Only update the files on the "en" folder.
- The 'jp' and 'en' files have to have the same amount of lines, so the merge can work.
- `<blank>` tags are added to add the same amount of spacing as the original work, so remember to keep them exact.
- Images can't be translated, only the original is used.

---

### Future Improvements

- Improve the translation using other models. Open Source models tested could not reach a good quality, but I couldn't test with `nllb-200-3.3B`, only up to `nllb-200-1.3B`. ChatGPT 4o was the best one, but too expensive for this project.
- Remove extra files from the website, and leave only the out files.
- Create the website entirely using github actions.
    - Have to create home index.md automatically.
    - Move files out of docs folder (or use another folder for output?).
    - Run py scripts during build (`merge_chapters.py` and `create_index_file_per_serie.py`).