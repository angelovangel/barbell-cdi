## barbell demux for custom CDI amplicon libraries (ONT)

Demultiplexes combinatorial dual-index (CDI) amplicon libraries sequenced on Oxford Nanopore with
[barbell](https://github.com/rickbeeloo/barbell). Each amplicon carries a utag + primer at both ends; the **pair** of utags
(e.g. a 32 x 12 grid = 384 wells) identifies the sample. Works for NBD (native barcoding) and LSK (ligation) libraries and
any primer pair (default 16S 27F / 1492R).

### Quick start

**Requirements:** Python >= 3.8 (stdlib only) and `barbell` on your PATH
(`RUSTFLAGS="-C target-cpu=native" cargo install barbell` or `conda install -c bioconda barbell`). Optional, to call it as `barbell-cdi`:

```bash
chmod +x barbell-cdi.py && ln -s "$(pwd)/barbell-cdi.py" /usr/local/bin/barbell-cdi
```

```bash
# all 384 wells, output named Plate1-A1.fastq ...
barbell-cdi demux -r 'fastq_pass/**/*.fastq.gz' -c nbd -o demux_out -t 16

# your own sample names / a subset of wells
barbell-cdi demux -r 'fastq_pass/**/*.fastq.gz' -c nbd --samplesheet samples.csv -o demux_out -t 16

# ONT barcodes also split the pool: ONT barcode first, then utags inside each bin
barbell-cdi twopass -r 'fastq_pass/**/*.fastq.gz' -k SQK-NBD114-96 --samplesheet samples.csv -o twopass_out -t 16
```

`-r` takes files, globs (quote them so the script expands them; `**` recurses) or directories (searched recursively for
`.fastq/.fq[.gz]`). `-h` on any subcommand lists its options and the input file formats.

### Choosing the command and context

```
5'-[ONT context][utag-fwd][forward primer] ...insert... [reverse primer][utag-rev][ONT context]-3'
```

The "context" is the constant sequence directly 5' of the utag, which barbell uses as part of the flank. `demux` defaults to
`bare`; for untrimmed NBD (reads in `fastq_pass/barcode01`) pass `-c nbd --ont-barcode NB01`, for LSK reads pass `-c lsk`:

| `-c` | Use for | Sequence 5' of the utag |
|---|---|---|
| `nbd` | SQK-NBD114 | `CAGCACCT` (after every NB barcode); with `--ont-barcode NB07`: `ATTGCTAAGGTTAA` + NB07 + `CAGCACCT` |
| `lsk` | SQK-LSK114, no ONT barcode | `CTTCGTTCAGTTACGTATTGCT` (end of the Ligation Adapter) |
| `bare` (default) | Reads whose ONT adapter/barcode is already trimmed (`twopass` uses this in pass 2) | nothing |

* **`demux`**: utags are the only sample identifier (no ONT barcodes, or one per library).
* **`twopass`**: several ONT barcodes in one run (e.g. NB01-NB04). Pass 1 `barbell kit` splits by ONT barcode and trims it;
  pass 2 runs `demux -c bare` inside each bin, so the same utag pair can be reused in different bins.
* Don't use `-c nbd` for LSK libraries (56% vs 93% assigned in simulation). **MAB kits (SQK-MAB114) cannot be used in CDI**: their
  reads carry the barcode context and utag at the read start only, so no tag pair can be formed (the downstream tag is low quality/trimmed).
* Unsure what is really upstream of your utags? Run `context` (see Troubleshooting) and pass its suggestion as `--prefix`.

Other subcommands: `queries` (write the query FASTAs only), `tagqc` (check tags, plate map and sample sheet), `context`.

### Input files

| Option | Default | Format | Example row |
|---|---|---|---|
| `--tags` | `data/utags-sequence.csv` | no header: `tag ID,sequence` | `U013,CAACAGTAG` |
| `--plates` | `data/utags-platemap.csv` | `plate,well,utag-fwd,utag-rev` | `1,A1,U013,U001` |
| `--samplesheet` | none | `sample,plate,well[,ont-barcode]`, csv or `.xlsx` | `Soil_A,1,A1` |

You only write the sample sheet: which sample is in which well. The plate map (found next to the script) turns wells into tags.

**Tags** (`--tags`): 96 tags of 9 nt (`U001`-`U096`), 5'->3' as in the oligo. Only tags used by the plate map / sample sheet go into
the queries (`--all-tags` uses all). Every tag ID you reference must exist here. Check your setup with `tagqc`: tag edit distances, the plate map's layout per plate (which tags run along rows / columns),
duplicate wells, missing tag sequences, and with `--samplesheet` the samples per plate, ONT bins and decoys.

**Plate map** (`--plates`): the full library design, 4 plates x 96 wells. Column 1-12 = rev tags `U001`-`U012`; rows A-H = fwd tags
`U013`-`U020` on plate 1, `U021`-`U028` on plate 2, `U029`-`U036` on plate 3, `U037`-`U044` on plate 4 (so plate 2 well C7 = `U023` + `U007`). Without a sample sheet the outputs are named `Plate1-A1.fastq` etc.
Without a sample sheet every well is a sample. You don't edit or pass it unless your physical tag layout differs.

**Sample sheet** (`--samplesheet`): your sample names and their plates and wells.

```
sample,plate,well
Soil_A,1,A1
Water_2,1,H12
```

* `plate` may be written `1`, `Plate1` or `P1`; `well` as `A1` or `A01` (or `Plate1-A1` without a plate column).
* Output is `samples/<sample>.fastq`; spaces and special characters in names become `_`. Only listed samples are written.
* Instead of `plate,well` you can give the tags directly (`utag-fwd,utag-rev`, e.g. `U013,U001`), e.g. for tags without a plate layout.
* Headers are case-insensitive; column order and extra columns don't matter; blank rows are skipped.
  Excel: first worksheet, or `--sheet-name`; old `.xls` is not supported.
* Duplicate names are an error, as are two samples in the same well (except in different `ont-barcode` bins).
* `ont-barcode` is used by `twopass` only: each bin is searched for its own samples, and bins without samples are skipped.
  Without the column every bin is searched for every sample.
* **Decoys:** all plate-map tags are searched even if your sheet doesn't use them, so reads from unlisted wells are reported
  as unexpected instead of being forced onto the most similar listed tag. The script prints how many decoys it added, and warns
  if the plate map is missing. `--no-decoys` turns this off (more mis-assignments).

### Output

Results and the script's own files are at the top; everything barbell writes is in `barbell/`.

```
demux_out/
  samples/<sample>.fastq[.gz]   the result: one file per sample, utag and primer trimmed off
  summary.tsv                   reads per sample with plate, well and tags (0-read samples too); input for plate-heatmap.py
  unexpected.tsv                tag pairs found on reads but not in the plate map / sample sheet, with read counts
  run_summary.csv               totals (also printed): reads in, with a hit, assigned, tag at both / one end, unexpected
  barbell-cdi.log               everything the script printed, with date and command line
  barbell/
    inspect.txt                 most common read patterns
    trimmed/                    per-tag-pair files (below)
    queries/                    the query FASTAs used
    annotation.tsv, filtered.tsv, dropped.tsv, trim_failed.txt, filters.txt, *.log
```

barbell names `trimmed/` files `<tag at read start>__<tag at read end>`, so each well gives two files, one per strand:

```
barbell/trimmed/U013__U001.trimmed.fastq   forward-strand reads
barbell/trimmed/U001__U013.trimmed.fastq   reverse-strand reads    -> both merged into samples/Plate1-A1.fastq
```

Pairs not in the plate map / sample sheet (e.g. `U001__U037`) are not merged; they are listed in `unexpected.tsv`.
Reads keep their sequenced orientation; add `--flip` to reverse-complement reverse-strand reads (forward primer -> reverse primer).
Once you have checked the results, `barbell/` can be deleted.

```
twopass_out/
  samples/<ONT bin>/<sample>.fastq
  summary.tsv, unexpected.tsv   as above, with an ont_barcode column
  ont_bins.tsv                  reads per ONT bin: in bin, with hit, assigned
  run_summary.csv, barbell-cdi.log
  barbell/
    pass1_kit/, pass1_kit.log   barbell kit output (reads per ONT bin)
    pass2_utag/<bin>/           the demux run of each bin (its own log, summaries and barbell/ folder)
```

### Troubleshooting: few reads assigned

`demux` prints what was found per read (from `barbell/inspect.txt`):

| Line | Meaning |
|---|---|
| utag at both ends | tag pair read: only these reads can be assigned |
| utag at one end, primer-flank only at the other | the other end's tag is damaged or missing |
| utag at ONE end only | no tag pair possible |
| primer-flank only | primer found, utag unreadable |

* **Mostly one end only:** the far end has no utag in this prep, is truncated, or was trimmed by the basecaller (use untrimmed
  reads), or the primer/context at that end is wrong.
* **Mostly primer-flank only / few hits:** wrong primers or wrong context.
* **Other primers** (ITS, COI, 18S, ...): give both 5'->3' as ordered, IUPAC allowed: `--primer-f <SEQ> --primer-r <SEQ>`
  (`demux`, `twopass`, `queries`, `context`). The primer is part of the flank and is trimmed from the output.
* **Wrong context:** `context` finds exact utag + primer matches and prints the consensus of the sequence upstream, plus a
  ready-to-use prefix. On real NB94 reads it returned adapter tail + `AAGGTTAA` + NB94 + `CAGCACCT`, the documented NBD layout.

  ```bash
  barbell-cdi context -r reads.fastq.gz
  barbell-cdi demux -r reads.fastq.gz -c bare --prefix <suggested prefix> ...
  ```
* Tuning: `--flank-max-errors N` (relax if reads are missed), `--min-score-diff X` (raise, e.g. 0.2, for fewer wrong-well calls),
  `--max-offset 250` (max distance of the utag from the read end).

### Reference
**Barbell paper:** https://doi.org/10.1093/bioinformatics/btag349  
**Workflow:** `demux` runs barbell `annotate` (find utag + flank at both ends, both strands) -> `inspect` (pattern summary; the
two top patterns should be `Ftag ... Rtag(rc)` and `Rtag ... Ftag(rc)`) -> `filter` (keep reads with a tag at both ends) ->
`trim` (cut tags and primers, one file per tag pair) -> rename tag pairs to samples. It adapts to both the release barbell
(comma-separated `-q`/`-b`, single input) and newer builds, decompresses `.gz` input first, and raises `ulimit -n` for `trim`
(use `ulimit -n 65535` if you run barbell by hand).

**Query FASTAs.** One per end; each entry is the full oligo `context + utag + primer`, 5'->3'. Ready-made files for the default primers are in `data/fasta/`; regenerate with `queries --primer-f ... --primer-r ...`.

**This tag set.**
* Rev tags `U001`-`U012` all start with `A`, so barbell folds that base into the flank and compares 8 nt instead of 9 (printed; works).
* Minimum edit distance is 2 for rev tags (`U005`/`U011`), 3 for fwd tags: expect 0-2 wrong-well calls per ~1,400 assigned reads
  in simulation. Raise `--min-score-diff` if that matters.
* The 384-well grid is complete, so with the full plate map chimeras/index hopping cannot be detected; they land in a wrong well.
  With a sample sheet covering part of the grid, they show up in `unexpected.tsv`.

**ONT sequences.** The 96 NB barcodes and the NBD/LSK flanks match ONT's Chemistry Technical Document
(CHTD_500_v1_revAV_24July2026). You can check unknown reads with `context`.


### Repository

| File | Description |
|---|---|
| `barbell-cdi.py` | The tool (`demux`, `twopass`, `context`, `queries`, `tagqc`) |
| `data/utags-sequence.csv`, `data/utags-platemap.csv` | Default tags and plate map |
| `data/samplesheet-example.csv`, `data/samplesheet-example-twopass.csv` | Example sample sheets (the second with `ont-barcode`) |
| `data/utags-10bp-sequence.csv`, `data/utags-10bp-platemap.csv` | An alternative 10 nt tag set (`U001`-`U044`) and its plate map (rows = rev, columns = fwd tags); use with `--tags` and `--plates` |
| `data/fasta/` | Ready-made query FASTAs for the default primers |
| `simulate-reads.py` | Fake reads with known truth: `python3 simulate-reads.py nbd 3000 sim.fastq` |
| `plate-heatmap.py` | HTML heatmap of reads per well: `python3 plate-heatmap.py demux_out/summary.tsv -o plates.html` (samples are placed by the `plate`/`well` columns, so custom names need no extra file) |
