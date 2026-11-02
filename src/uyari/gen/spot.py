"""Human spot read: export a random ``pct``% of a batch to ``reports/spot/<batch>.xlsx``.
A batch with more than 5% rejected rows in the spot read is withdrawn (deprecate its chunks)."""

from __future__ import annotations

import math
import random

from uyari.csvio import read_csv
from uyari.data.primary import chunk_files
from uyari.paths import Paths


def export_spot(paths: Paths, lang: str, batch: str, pct: float):
    from openpyxl import Workbook

    f = [x for x in chunk_files(paths, lang) if x.stem == batch]
    if not f:
        raise FileNotFoundError(f"batch {batch} not found in primary/{lang}")
    rows = [r for r in read_csv(f[0]) if r["status"] == "active"]
    k = max(1, math.ceil(len(rows) * pct / 100))
    sample = random.Random(f"spot:{batch}").sample(rows, min(k, len(rows)))
    wb = Workbook()
    ws = wb.active
    ws.title = "spot"
    ws.append(["chunk_id", "domain_l1", "texto", "aceptable (si/no)", "motivo"])
    for r in sample:
        ws.append([r["chunk_id"], r["domain_l1"], r["text"], "", ""])
    out = paths.reports / "spot" / f"{batch}.xlsx"
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return out
