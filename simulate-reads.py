#!/usr/bin/env python3
"""Simulate ONT amplicon reads for a dry run: python3 simulate_reads.py nbd|lsk|bare N out.fastq
Writes out.fastq plus out.fastq.truth.tsv (read_id -> true plate-well)."""
import os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util
_spec = importlib.util.spec_from_file_location("barbell_cdi", os.path.join(os.path.dirname(os.path.abspath(__file__)), "barbell-cdi.py"))
_m = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_m)
NB_SEQS, PRIMER_F, PRIMER_R, rc, read_tags, read_plates = _m.NB_SEQS, _m.PRIMER_F, _m.PRIMER_R, _m.rc, _m.read_tags, _m.read_plates

IUPAC = {"R": "AG", "Y": "CT", "M": "AC"}
res = lambda s: "".join(random.choice(IUPAC.get(c, c)) for c in s)

def mutate(s, sub=.03, ins=.01, dele=.01):
    o = []
    for c in s:
        r = random.random()
        if r < dele:
            continue
        if r < dele + ins:
            o.append(random.choice("ACGT"))
        o.append(random.choice("ACGT") if random.random() < sub else c)
    return "".join(o)

ctx, n, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
here = os.path.dirname(os.path.abspath(__file__))
tags = read_tags(os.path.join(here, "data", "utags-sequence.csv"))
plates = read_plates(os.path.join(here, "data", "utags-platemap.csv"))
random.seed(1)
adapter = {"nbd": "TTTTTTTTCCTGTACTTCGTTCAGTTACGTATTGCTAAGGTTAA" + NB_SEQS["NB01"] + "CAGCACCT",
           "lsk": "CCTGTACTTCGTTCAGTTACGTATTGCT",
           "bare": ""}[ctx]
with open(out, "w") as fh, open(out + ".truth.tsv", "w") as th:
    for i in range(n):
        r = random.choice(plates)
        insert = "".join(random.choice("ACGT") for _ in range(random.randint(1300, 1500)))
        top = (adapter + tags[r["utag-fwd"]] + res(PRIMER_F) + insert +
               rc(adapter + tags[r["utag-rev"]] + res(PRIMER_R)))
        if random.random() < .5:
            top = rc(top)
        top = mutate(top)
        rid = f"read{i}"
        th.write(f"{rid}\t{r['plate-well']}\n")
        fh.write(f"@{rid}\n{top}\n+\n{'I' * len(top)}\n")
