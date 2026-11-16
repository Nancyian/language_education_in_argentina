# Archive manifest

Archive of the institutional and expert fields (media field pending). Generated 2026-11-16. Total: **152 files, 20.1 MB** — within GitHub's 100 MB per-file and 1 GB per-repo limits.

| Directory | Files | Size | Contents |
|---|---:|---:|---|
| `code/` | 111 | 0.7 MB | 111 Python modules: harvest, screening, corpus assembly, LDA, figures, report generation |
| `data/metadata/` | 2 | 41 KB | Bibliographic metadata only (full text removed): 71 official + 66 expert records |
| `data/processed/` | 8 | 1.1 MB | Model outputs: topic–word (φ), document–topic (θ), coherence/perplexity curves, polarity, word counts |
| `figures/official/` | 9 | 4.1 MB | 7-figure set + perplexity curve + K-selection diagnostics |
| `figures/expert/` | 7 | 2.5 MB | 7-figure set |
| `docs/` | 10 | 11.7 MB | Figure sets (DOCX/PDF), comparative report, full-text word counts, polarity annotation, timeline |
| `README.md`, `LICENSE`, `CITATION.cff`, `.gitignore` | 4 | 12 KB | Repository metadata |

## Excluded from the repository

| Item | Size | Reason |
|---|---:|---|
| `work/ft_exp/*.pdf` (66 article PDFs) | 104 MB | Publisher copyright; DOI/URL in `data/metadata/` allows re-download |
| Full-text corpus tables (`*_merged_by_source.xlsx`, `*_corpus.csv`) | 41 MB | Contains third-party article text |
| Scraped government page bodies (`off_web*.json`) | 0.1 MB | Contains third-party page text |
| Raw HTML crawl + browser profile (`work/_probe/`, `work/ab_profile/`) | 33 MB | Transient, non-reproducible |
| Intermediate document drafts (`work/docx_*_v*.docx`, `_atlas_v*.pdf`) | 65 MB | Superseded versions; final versions in `docs/` |
| Large intermediate TSV (`bysource.tsv`, `sheet1_full.tsv`) | 54 MB | Regenerable from metadata + harvest scripts |

## Reproducibility checklist

1. `data/metadata/*.csv` + `code/fetch_dialnet*.py` → re-download open-access articles.
2. `code/run_fulltext.py` → extract and normalise full text (≈10 s/request rate limit).
3. `code/off_model.py` / `lab_model2.py` → topics, θ, φ, coherence sweep.
4. `code/off_perplexity.py`, `code/off_coh_seeds.py` → K-selection diagnostics.
5. `code/off_figs.py`, `code/lab_figs2.py`, `code/fig3_net.py` → figures 1–7.
