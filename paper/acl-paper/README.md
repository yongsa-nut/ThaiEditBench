# ThaiEditBench — ACL LaTeX build

Official ACL style files + the paper ported to LaTeX. The source of truth for prose is
`../paper-thaieditbench-acl.md`; this folder is the typeset version.

## Files
- `acl_paper.tex` — the paper (main file).
- `custom.bib` — references (verified; matches the `\citep` keys).
- `fig1-degradation.pdf` — Figure 1 (regenerate via `../../thaiwrite/editing/viz/plot_degradation.py`).
- `acl.sty`, `acl_natbib.bst` — official ACL style files (acl-org/acl-style-files).
- `acl_lualatex.tex` — upstream template, kept for reference.
- `fonts/NotoSerifThai-{Regular,Bold}.ttf` — bundled Thai font (loaded by path, so the
  project is self-contained and needs no system/TeXLive font install).

## ⚠️ Compile with **LuaLaTeX** (not pdfLaTeX)
The paper contains Thai script, which needs `fontspec` + `babel` font switching — pdfLaTeX
cannot render it. The preamble auto-switches to the **bundled Noto Serif Thai** on Thai
characters (`\babelprovide[import, onchar=ids fonts]{thai}`), so inline Thai needs no wrapping.

### Overleaf (recommended — zero setup)
1. Upload this whole folder (or zip it) to a new Overleaf project.
2. **Menu → Settings → Compiler → LuaLaTeX.**
3. Compile. Overleaf's TeX Live has Noto Serif Thai and a recent babel, so it works as-is.

### Local (TeX Live / MiKTeX with LuaLaTeX + the Noto Serif Thai font installed)
```
latexmk -lualatex acl_paper.tex
# or:  lualatex acl_paper && bibtex acl_paper && lualatex acl_paper && lualatex acl_paper
```

### If Thai shows as boxes (□□□)
The font auto-switch isn't taking effect (usually an old babel without `onchar`). The
bundled font in `fonts/` is correct; the issue is the switching. Easiest fix — make the
bundled Thai font the single main font (renders Latin + Thai, loses the Times look):
```latex
\babelfont{rm}[Path=fonts/, Extension=.ttf,
  UprightFont=NotoSerifThai-Regular, BoldFont=NotoSerifThai-Bold]{NotoSerifThai}
```
(replacing the `\babelfont{rm}{TeX Gyre Termes}` + `\babelprovide`/`\babelfont[thai]` block).

## Modes
`\usepackage[review]{acl}` = anonymous + line numbers (submission). Change `review` to
`preprint` (non-anonymous, page numbers) or `final` (camera-ready) as needed.

## Status
Structurally checked (environments, braces, citation keys all resolve). **Not compiled here**
— no TeX engine on the build machine — so do a first compile on Overleaf and skim for overfull
lines / the 4-page body limit (Limitations, References, and Appendix A–E are uncounted).
