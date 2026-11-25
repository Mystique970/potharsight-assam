# Suitability criteria (v1, editable in config.yaml)

## 1. Availability (land status)
| Code | Status | Rule |
|---|---|---|
| 0 | Excluded | WorldCover tree/built/water/wetland/mangrove, built-up in any of the last 3 Esri years, stable trees or water, JRC water occurrence ≥ 40 %, water in any yearly Esri map (shifting channels), OSM protected areas |
| 1 | Vacant open land | WorldCover grass/shrub/moss, or Esri rangeland, not cropland (bare ground = river sand, left out) |
| 2 | Long fallow / under-used cropland | Cropland whose kharif peak NDVI < 0.50, or cropland (WorldCover or any earlier Esri year) now mapped by Esri as rangeland |
| 3 | Seasonal (rabi) fallow | Kharif-cropped land whose rabi peak NDVI < 0.35 – second-crop opportunity |
| 4 | Active double-cropped | Not a candidate; used to sanity-check the model |

## 2. Hard constraints (per programme)
| Profile | Max slope | Max monsoon flood frequency |
|---|---|---|
| Field crops (rice, mustard, pulses) | 15 % | 0.8 |
| Horticulture (citrus, banana, vegetables) | 30 % | 0.3 |

## 3. Factor scores (0–100) and weights
| Factor | Indicators and thresholds | Source | Field crops | Horticulture |
|---|---|---|---|---|
| Soil fertility | pH optimum 6.0–7.5, zero at 4.5/8.5 (35 %), SOC 5→15 g/kg (25 %), total N 0.5→2.5 g/kg (15 %), CEC 5→25 cmol/kg (15 %), clay optimum 15–35 % (10 %) – Soil Health Card / ICAR ratings | SoilGrids 0–30 cm | 0.30 | 0.30 |
| Water availability | Rainfall optimum 1500–2500 mm, zero at 1000/4000 (40 %), distance to river/perennial water 3 km→250 m (60 %) | CHIRPS, JRC, OSM | 0.20 | 0.15 |
| Flood safety | Monsoon water frequency 0.4→0 | Sentinel-1 GRD 2022–24 | 0.15 | 0.20 |
| Terrain | Slope 15 %→2 % | Copernicus DEM | 0.15 | 0.10 |
| Productivity | Peak NDVI 0.3→0.85 | Sentinel-2 2022–24 | 0.10 | 0.10 |
| Access | Distance to road 5 km→250 m (60 %), to town 25 km→3 km (40 %) | OSM | 0.10 | 0.15 |

Classes: S1 ≥ 80, S2 65–80, S3 50–65, N < 50 or constrained. Most-limiting-factor rule: any factor < 40 caps the class at S2, any factor < 20 caps it at S3.
Calibration (25 Nov 2026): thresholds tightened from agronomic norms after v1 rated almost everything S1 (mean 86); see the validation section of the Proof of Work.
Limiting factor = largest weighted shortfall; contributing factor = largest weighted strength.
Patch priority = 0.8 × mean score + up to 20 points for size (full at ≥ 10 ha).
Block priority index = (S1 ha + 0.5 × S2 ha) × mean candidate score / 100.
