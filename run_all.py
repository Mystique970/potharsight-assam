"""D13 pipeline runner.

Examples
  python run_all.py                                  # all districts in config.yaml, all steps
  python run_all.py --district kamrup                # one district
  python run_all.py --district cachar --steps fetch --only dem soil
  python run_all.py --steps model                    # re-run model only (after editing weights)

Steps: fetch -> prep -> model (suitability, ranking, validation, figures)
"""
import argparse
import logging
import sys
import time

from d13 import fetch, model, rank, report, validate
from d13.core import get_district, load_config, make_grid


def main():
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--district", nargs="*", default=list(cfg["districts"]))
    ap.add_argument("--steps", nargs="*", default=["fetch", "prep", "model"])
    ap.add_argument("--only", nargs="*", help=f"fetchers to run: {list(fetch.FETCHERS)}")
    ap.add_argument("--profiles", nargs="*", default=list(cfg["profiles"]))
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S",
                        handlers=[logging.StreamHandler(sys.stdout),
                                  logging.FileHandler("pipeline.log", encoding="utf-8")])
    for key in a.district:
        try:
            run_district(key, cfg, a)
        except Exception:
            logging.exception("District %s stopped with an error (see above). Continuing.", key)


def run_district(key, cfg, a):
    if True:
        d = get_district(key, cfg)
        t0 = time.time()
        logging.info("=== %s ===", key)
        if "fetch" in a.steps:
            make_grid(d)
            status = fetch.run(d, a.only)
            bad = {k: v for k, v in status.items() if v != "ok"}
            if bad:
                logging.warning("Some layers failed: %s  (re-run with --only <name>)", bad)
        if "prep" in a.steps:
            model.preprocess(d)
            model.land_status(d)
        if "model" in a.steps:
            for p in a.profiles:
                res = model.suitability(d, p)
                patches = rank.run(d, p, res)
                validate.run(d, p, res)
                report.figures(d, p, res, patches)
                report.web_overlay(d, p, res)
                report.summary(d, p, patches)
        logging.info("=== %s done in %.1f min ===", key, (time.time() - t0) / 60)


if __name__ == "__main__":
    main()
