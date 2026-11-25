# PotharSight Assam – Geospatial Identification of Cultivable & Fertile Agricultural Potential Land

NESFIC 2026 · Challenge D13 · Challenge owner: DST Assam – ASSAC ·
Districts: **Kamrup (Rural)**, **Cachar**, **Lakhimpur** and **Dibrugarh** – the top four in Assam for vacant cultivable land (DES Assam 2020-21)

A spatial decision-support layer that finds vacant / under-used land, checks whether it can be
farmed, scores how suitable it is for a programme, explains **why**, and ranks patches, blocks and
revenue circles. All inputs are free, open and need **no login**.

## Portal

A guided web portal for officials: pick a district, what to grow and the type of land, and get graded sites
(A–D) on a map with reasons, block comparisons and downloads (Excel, Google Earth KML, GeoJSON). An advanced
map page serves GIS staff. Demo access is shown on the sign-in page (user `evaluator`, password `pothar2026`).

```
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

## Re-running the analysis (Windows, Python 3.10–3.12)

```
pip install -r requirements.txt
python check_access.py                  # checks the open data sources are reachable
python run_all.py                       # all districts in config.yaml, all steps
python run_all.py --district cachar     # one district
python run_all.py --steps fetch --only s1 soil   # retry specific layers
python run_all.py --steps prep model    # re-run the model after editing config.yaml
```
The first full run downloads roughly 1–3 GB per district.

## How it works

| Stage | What happens | Code |
| --- | --- | --- |
| Grid | District boundary (geoBoundaries/LGD) → 30 m UTM 46N grid | `d13/core.py` |
| Acquire | WorldCover 2021, Esri LULC 2017-23, Sentinel-2 NDVI (rabi/kharif peaks 2022-24), Sentinel-1 monsoon flood frequency, Copernicus DEM, SoilGrids 0-30 cm, CHIRPS rainfall, JRC surface water, OSM roads/towns/rivers/protected areas | `d13/fetch.py` |
| Availability | Land status: excluded / vacant open land / long-fallow cropland / rabi-fallow cropland / active double-cropped | `d13/model.py: land_status` |
| Constraints | Slope and flood limits per programme profile | `config.yaml: profiles` |
| Suitability | Six factor scores (soil, water, flood safety, terrain, productivity, access) → weighted 0-100 → S1/S2/S3/N | `d13/model.py: suitability` |
| Reasons | Per-pixel factor scores, limiting and contributing factor; plain-language reason per patch | `d13/model.py`, `d13/rank.py` |
| Prioritise | S1/S2 patches ≥ 0.5 ha ranked; blocks and revenue circles ranked by priority index | `d13/rank.py` |
| Validate | Comparison with DES Assam land-use statistics; farmland sanity check; ±20 % weight sensitivity | `d13/validate.py` |
| Outputs | COG GeoTIFFs, GeoPackage, Shapefile, GeoJSON, CSV, PNG maps, SUMMARY.md, dashboard | `d13/report.py`, `app/` |

## Scaling to more districts, states and programmes

- **New district in Assam:** add 3 lines under `districts:` in `config.yaml` and run `python run_all.py --district <key>`.
- **New state:** replace the three boundary files in `data/boundaries/` with that state's districts, sub-districts and blocks
  (geoBoundaries covers all of India) and set the UTM zone in `project.crs`. No code changes.
- **New crop / programme:** add a profile under `profiles:` with its own slope/flood limits and weights.
- **Department data (Track B):** any GeoTIFF/GPKG supplied by ASSAC (LULC 1:10k, soil series, SHC, cadastral parcels)
  can replace the matching open layer by dropping it into `data/interim/<district>/` with the same file name.

## Outputs (per district / programme)
```
outputs/<district>/<profile>/
  maps/       suitability_score.tif, suitability_class.tif, land_status.tif, factor_scores.tif (6 bands),
              limiting_factor.tif, contributing_factor.tif
  vectors/    priority_patches.gpkg/.geojson/shp, blocks_ranking.gpkg, circles_ranking.gpkg
  tables/     priority_patches.csv, blocks_ranking.csv, circles_ranking.csv, validation.json, sensitivity.csv
  figures/    suitability_class.png, land_status.png, suitability_score.png, block_ranking.png
  SUMMARY.md
```

## Data credits and licences
ESA WorldCover (CC BY 4.0) · Esri/Impact Observatory LULC (CC BY 4.0) · Copernicus Sentinel-1/2 and DEM (free) ·
ISRIC SoilGrids 2.0 (CC BY 4.0) · CHIRPS (public domain) · JRC Global Surface Water · OpenStreetMap (ODbL) ·
geoBoundaries (ODbL) · DES Assam Land Utilisation Statistics 2020-21. Data accessed through Microsoft Planetary Computer.

## Limitations
Soil is modelled at 250 m, not field-tested. "Available" is a satellite-based status; ownership and legal status
must be verified by the Revenue Department. Boundaries are for analysis only and are not authoritative.
