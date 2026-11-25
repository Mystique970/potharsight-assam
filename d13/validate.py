"""Validation: official statistics, farmland sanity check, weight sensitivity."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy import ndimage
from scipy.stats import spearmanr

from .core import District, load_grid, log
from .model import CANDIDATE, FACTORS
from .rank import _units


def run(d: District, profile: str, res: dict) -> dict:
    g = load_grid(d)
    pix_ha = g.res * g.res / 1e4
    st, cls, score, stack = res["status"], res["cls"], res["score"], res["stack"]
    out: dict = {"district": d.key, "profile": profile}

    # 1. Official land-use statistics (DES Assam 2020-21): culturable waste + current + other fallows
    model_ha = float(np.isin(st, [1, 2]).sum() * pix_ha)
    model_all_ha = float(np.isin(st, CANDIDATE).sum() * pix_ha)
    off = d.dcfg.get("official_vacant_cultivable_ha")
    out["official_vacant_cultivable_ha"] = off
    out["model_vacant_plus_long_fallow_ha"] = round(model_ha)
    out["model_all_candidate_incl_rabi_fallow_ha"] = round(model_all_ha)
    if off:
        out["ratio_model_to_official"] = round(model_ha / off, 2)

    # 2. Known active farmland should score well biophysically (not counting availability)
    farm = st == 4
    out["active_farmland_share_scoring_S1_S2"] = round(float(np.isin(cls[farm], [1, 2]).mean()), 3) if farm.any() else None
    out["mean_score_active_farmland"] = round(float(np.nanmean(score[farm])), 1) if farm.any() else None
    out["mean_score_candidate_land"] = round(float(np.nanmean(score[np.isin(st, CANDIDATE)])), 1)

    # 3. Weight sensitivity: +/-20 % on each factor weight, Spearman rank correlation of block ranking
    w0 = d.cfg["profiles"][profile]["weights"]
    u, ras = _units(d, g, "blocks")
    ids = u.uid.values
    cand = np.isin(st, CANDIDATE)
    c = d.cfg["classes"]

    def block_index(w):
        wv = np.array([w[f] for f in FACTORS], "float32")[:, None, None]
        sc = (stack * wv).sum(0) / wv.sum() * 100
        s1 = ndimage.sum(cand & (sc >= c["S1"]) & (cls != 5), ras, ids)
        s2 = ndimage.sum(cand & (sc >= c["S2"]) & (sc < c["S1"]) & (cls != 5), ras, ids)
        ms = ndimage.sum(np.where(cand, np.nan_to_num(sc), 0), ras, ids) / np.maximum(ndimage.sum(cand, ras, ids), 1)
        return (s1 + 0.5 * s2) * ms

    base = block_index(w0)
    rows = []
    for f in FACTORS:
        for k in (0.8, 1.2):
            w = dict(w0)
            w[f] = w0[f] * k
            alt = block_index(w)
            rho = spearmanr(base, alt).statistic if len(ids) > 2 else np.nan
            top_b = set(np.argsort(-base)[:5])
            top_a = set(np.argsort(-alt)[:5])
            rows.append(dict(factor=f, change=f"{int((k - 1) * 100):+d}%", spearman_rho=round(float(rho), 3),
                             top5_overlap=len(top_b & top_a)))
    sens = pd.DataFrame(rows)
    out["sensitivity_min_rho"] = float(sens.spearman_rho.min())
    out["sensitivity_mean_top5_overlap"] = float(sens.top5_overlap.mean())
    od = d.out / profile / "tables"
    od.mkdir(parents=True, exist_ok=True)
    sens.to_csv(od / "sensitivity.csv", index=False)
    (od / "validation.json").write_text(json.dumps(out, indent=1))
    log.info("[validate] %s", out)
    return out
