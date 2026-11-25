# NESFIC 2026 · D13 proposal answers (draft)

Challenge: Geospatial Identification of Cultivable & Fertile Agricultural Potential Lands (DST Assam – ASSAC)
Solution name: **PotharSight Assam** (*pothar* = agricultural field in Assamese) – an open, explainable land-suitability decision-support layer
Each answer is kept under 500 words. Numbers come from outputs/*/*/tables (final run, 25 Nov 2026).

---

## 1. Problem understanding & user workflow

Assam has large areas of land that could be farmed but are not: culturable waste, current fallow and other fallow together total about 3.35 lakh ha across the 25 districts that report them in the DES Assam Land Utilisation Statistics 2020-21. In Kamrup (Rural) alone it is 31,453 ha, and in Cachar 26,064 ha. These figures exist only as district totals in tables. Nobody can see *where* this land is, *how suitable* it is, or *why*.

**Users:** district agriculture and horticulture officers, district administration, land-use planners, KVKs and extension agencies, and programme managers for schemes such as RKVY, MIDH, PMKSY and the Assam Agribusiness and Rural Transformation Project.

**Current workflow:** an officer planning a programme (for example a new citrus cluster or a rabi-mustard expansion) collects statistics, soil health card summaries, flood maps and local knowledge from different offices. Sites are proposed block by block, mostly from experience. Satellite layers held by ASSAC, soil data held by the Department of Agriculture and flood data held by ASDMA are not combined into one map. As a result:
- identifying land is slow (weeks of correspondence and field checks);
- the choice is hard to justify (no recorded criteria);
- programmes are spread thinly instead of targeted to where they will work.

**Gaps we address**
1. No single, integrated layer that combines availability (is the land vacant or under-used?) with suitability (soil, water, flood, terrain, productivity, access).
2. No ranking at the level where decisions are made: parcel, block and revenue circle.
3. No explanation attached to a result, so decisions cannot be audited or challenged.
4. No downloadable GIS output that departments can reuse in their own systems.
5. No quick way to change the criteria for a different crop or programme.

**Intended outcome:** within minutes, an officer can open their district, choose a programme, see suitability maps and ranked blocks and patches with the reason for each result, adjust the criteria, and download the layers. Field teams then verify only the shortlisted sites, and the Revenue Department checks ownership of those sites only.

---

## 2. Proposed solution & key features

PotharSight Assam is a configurable geospatial pipeline plus a web dashboard.

**Modules**
1. **Data ingestion:** scripted download of nine free layers (Sentinel-1/2, WorldCover, Esri land use, Copernicus DEM, JRC water, CHIRPS, SoilGrids, OpenStreetMap), logged in a data register. Department layers replace any of them by changing one file path.
2. **Land availability:** each 30 m cell is *excluded* (forest, water, river channels, built-up, protected), *vacant*, *long fallow*, *rabi fallow* or *active*, from multi-year land cover and seasonal NDVI.
3. **Suitability model:** FAO-style evaluation – hard limits (slope, flooding), six 0–100 factor scores (soil, water, flood safety, terrain, plant growth, access), weighted into S1/S2/S3/N with a most-limiting-factor rule.
4. **Explanation:** every cell and site stores its factor scores, limiting and strongest factor, and a plain-language reason.
5. **Prioritisation:** S1/S2 land ≥ 0.5 ha forms *priority sites* (a parcel proxy until cadastral data is shared), ranked district-wide and per block; blocks and revenue circles get a priority index.
6. **Programme profiles:** field crops and horticulture, each with its own limits and weights; new crops are added in the config file.
7. **PotharSight web portal (sign-in)** with five sections:
   - **Home:** all districts at a glance. Unused land found, suitable land, second-crop potential, district maps and quick links.
   - **Find land for farming:** a guided search in plain language for officials. Choose the district, what to grow and the type of land; get sites graded A–D with a map, Google Maps links, a 6-factor profile, strong points, problems and a suggestion for each site (for example "add a rabi crop – mustard or lentil"), plus Excel, Google Earth and GIS downloads.
   - **Compare districts & blocks:** a ranking of blocks and revenue circles across districts, with the main problem of each, to place programme targets.
   - **Advanced map analysis (GIS staff):** S1/S2/S3/N suitability classes, live weight sliders, factor scores, GeoTIFF, GeoPackage and Shapefile downloads.
   - **How it works & validation:** data sources, criteria, accuracy checks and scaling.

**What changes versus the current approach:** land identification goes from weeks to minutes, and every result carries its criteria and data sources. Criteria become explicit and adjustable instead of implicit. Outputs are standard GIS files that ASSAC can load into Bhuvan, its own GIS or the department's portal. And the same method runs for any district by adding one line of configuration.

**Scalability by design:**
- new district → add its name to `config.yaml`
- new state → point to that state's boundary layers
- new crop or programme → add a profile with its own thresholds and weights
- department soil, cadastral or programme data → replace a layer file; no code change.

---

## 3. User journey, wireframes & prototype

**User journey** (diagram in the Proof of Work PDF):
0. The officer **signs in** to the PotharSight portal with a user ID and password.
1. The officer selects a **district** (Kamrup Rural or Cachar in the pilot) and a **programme** (field crops or horticulture).
2. The **summary cards** show the priority land area, the number of patches, and the official vacant-cultivable figure next to the model figure.
3. The **map** shows the suitability classes over a satellite basemap, block boundaries with their rank, and the priority patches.
4. Clicking a **patch** shows its rank, area, land status, six factor scores and a plain-language reason.
5. The **block ranking table** shows S1 and S2 hectares, the mean score and the main limitation, which supports block-level allocation of programme targets.
6. **Weight sliders** let the officer test the programme's priorities (for example more weight on access for a market-oriented horticulture cluster), and the ranking updates live.
7. **Download** the layers (GPKG, GeoJSON, SHP, GeoTIFF, CSV) for the field-verification team, Revenue Department checks and the department's own GIS.
8. In Track B, field teams mark patches as verified or rejected, and this feedback re-trains the model.

**Prototype maturity:** working end to end, not a mock-up. The pipeline has run on real data for both pilot districts and both programme profiles, producing:
- pilot districts, for field crops: 3,624 priority sites covering 22,003 ha in Kamrup (Rural), and 4,261 sites covering 36,544 ha in Cachar;
- scale-out districts, added with one configuration line each and no code change: 3,249 sites (12,612 ha) in Lakhimpur and 1,845 sites (9,921 ha) in Dibrugarh;
- ranked block and circle tables;
- validation reports;
- a working Streamlit dashboard ⟨public URL – add after hosting⟩.

The Proof of Work PDF contains screenshots, maps, ranking tables, an example explanation and the validation results.

---

## 4. Technology & solution architecture

**Stack (all open source):**
- Python 3 with rasterio/GDAL, geopandas, shapely, numpy, scipy and pystac-client;
- Streamlit and Folium (Leaflet) for the dashboard.

Outputs are OGC-standard formats (GeoTIFF, GeoPackage, GeoJSON, Shapefile) and CSV. No proprietary licence is needed.

**Data flow**
1. **Ingest** (`fetch`): STAC queries to Microsoft Planetary Computer and Element84 Earth Search, with cloud-optimised GeoTIFF windowed reads. Data comes only for the district's bounding box, so no full scenes are downloaded. There are fallback mirrors for every layer, and OSM comes through Overpass.
2. **Harmonise** (`prep`): everything is reprojected to a common 30 m grid (UTM 46N, EPSG:32646) per district. This step derives slope, distance to water, roads and towns, the protected-area mask and flood frequency.
3. **Classify availability:**
   - rule-based logic on WorldCover 2021 combined with Esri LULC 2017–2023 (stability and change);
   - JRC permanent water;
   - Sentinel-2 seasonal NDVI peaks (kharif June–October, rabi November–March, 2022–2024);
   - long fallow is cropland whose kharif peak NDVI stays below 0.5; rabi fallow is cropland that is cropped in kharif but has a rabi peak below 0.35.
4. **Flood frequency:** Sentinel-1 VV backscatter over the monsoons of 2022–2024 (June–September). The water threshold is self-calibrated per scene against JRC permanent water and stable land, and the output is the fraction of observations flooded.
5. **Suitability:**
   - piece-wise linear and trapezoidal membership functions per indicator, with thresholds from ICAR / Soil Health Card ratings and FAO guidelines;
   - weighted linear combination with AHP-style weights;
   - hard constraints and a minimum-factor cap.
6. **Explain and rank:** limiting and contributing factor rasters, patch vectorisation, zonal statistics per block and circle.
7. **Validate:** comparison with DES statistics, a check on known farmland, and weight-sensitivity analysis.
8. **Serve:** the dashboard reads the exported layers, and the same files are available for download or WMS/WFS publication (GeoServer) in Track B.

**AI/ML:** the prototype deliberately uses transparent rules, because the department needs explainable and auditable results. Track B adds:
- a random-forest or gradient-boosting fallow/cropland classifier trained on ASSAC-verified samples and Sentinel-1/2 time series;
- ML-derived soil property maps calibrated with Soil Health Card points.

**Hosting:**
- pilot: Streamlit Community Cloud or a small VM;
- production: the State Data Centre or the ASSAC server, with a scheduled re-run every season.

Compute is modest: one district runs on a laptop.

---

## 5. Development methodology & intermediate steps

We work in short, evidence-driven iterations: **Plan → Verify data → Acquire → Process → Model → Validate → Application → Test → Demonstrate**.

| Step | Key output | Status |
|---|---|---|
| 1. Discovery: challenge analysis, user needs, criteria from FAO, ICAR and SHC | Criteria table, workbook | Done |
| 2. Data verification: every source tested for open, no-login access; data register | data_register.csv | Done |
| 3. Pilot selection on evidence: DES LUS 2020-21 vacant-cultivable ranking | Kamrup (R) + Cachar | Done |
| 4. Automated acquisition: scripted download with fallbacks | 9 layers per district | Done |
| 5. Processing: common grid, derived layers | Harmonised raster stack | Done |
| 6. Model v1: availability, suitability, reasons, ranking | Maps, patches, rankings | Done |
| 7. Calibration: thresholds set from agronomic norms; checked against official statistics and farmland | Model v2 | Done |
| 8. Application: dashboard with live re-weighting and downloads | Streamlit app | Done |
| 9. Testing: synthetic end-to-end test, sensitivity analysis, visual checks against imagery | Test report | Done |
| 10. Department integration: ASSAC/department layers, user feedback workshop | v3 | Track B |
| 11. ML fallow classifier and crop-specific profiles | v4 | Track B |
| 12. Pilot validation with field teams; hosting at ASSAC/SDC | Validated MVP | Track B |

Each iteration ends with a run of `run_all.py`, validation metrics and a visual review. Changes to criteria are made only in `config.yaml`, so every version is reproducible.

---

## 6. Development timeline & milestones

The timeline is aligned with the NESFIC schedule: prototype development November 2026 – February 2027, Demo Day February 2027, MVP February – May 2027.

| Period | Phase | Milestones and deliverables | Dependencies |
|---|---|---|---|
| Sep–Nov 2026 (done) | Prototype v1–v2 | Two-district working prototype, dashboard, GIS exports, validation | Open data only |
| Dec 2026 | Requirements workshop | Criteria and weights reviewed with ASSAC and agriculture/horticulture officers; crop list fixed | Department time |
| Dec 2026 – Jan 2027 | Data integration | ASSAC LULC/wasteland layers, SHC soil points, ASDMA flood maps, block/circle boundaries integrated | Data-sharing approval |
| Jan 2027 | Model v3 | Crop-specific profiles (rice, mustard, pulses, citrus, banana, vegetables); ML fallow classifier | Training samples from ASSAC |
| Feb 2027 | **Demo Day** | Hosted portal on 4 districts; field-verification module | — |
| Feb–Mar 2027 | MVP | 4–6 districts; user log-in roles, audit log; GeoServer WMS/WFS | Server at ASSAC/SDC |
| **Mar 2027** | **Ready for validation** | Field verification of a sample of patches in each pilot district by department staff | Field teams |
| Apr–May 2027 | Refinement | Accuracy report; model re-trained on feedback; statewide roll-out plan | Validation results |

---

## 7. Data & information requirements

**Used in the prototype (all free, no log-in, verified):**

| Data | Source | Format and resolution | Use |
|---|---|---|---|
| District, circle and block boundaries | geoBoundaries (LGD-based, ODbL) | Vector | AOI, ranking units |
| Land cover 2021 | ESA WorldCover v200 | GeoTIFF, 10 m | Availability |
| Land-use 2017–2023 | Esri/Impact Observatory | GeoTIFF, 10 m | Change, stability, abandonment |
| Elevation | Copernicus GLO-30 | GeoTIFF, 30 m | Slope, terrain |
| Surface water | JRC Global Surface Water | GeoTIFF, 30 m | Permanent water, distance to water |
| Rainfall | CHIRPS annual, 2014–2023 | GeoTIFF, ~5 km | Water factor |
| Soil (pH, SOC, N, CEC, clay) | ISRIC SoilGrids 2.0, 0–30 cm | GeoTIFF, 250 m | Soil factor |
| Optical | Sentinel-2 L2A, 2022–2024 | COG, 10 m (read at 20–40 m) | Seasonal NDVI, fallow, productivity |
| Radar | Sentinel-1 GRD, monsoon 2022–2024 | COG, 10 m (read at 40 m) | Flood frequency |
| Roads, towns, rivers, protected areas | OpenStreetMap | Vector | Access, water, exclusions |
| Land use statistics 2020-21 | DES Assam | Table | Validation and pilot selection |

**Needed from departments for the pilot (not assumed; requested subject to policy):**
- ASSAC: LULC (50K), wasteland atlas, and high-resolution imagery for verification.
- Department of Agriculture: Soil Health Card points, programme target areas.
- Revenue Department: cadastral parcels (Dharitree/Bhunaksha) and land-ownership status.
- ASDMA: flood hazard zones.
- Validated sample points for model training and accuracy assessment.

**Processing and annotation:**
- for the ML classifier, about 1,000 labelled points per district (fallow, cropland, vacant, other), labelled by interpretation of high-resolution imagery;
- department field teams verify a stratified sample.

**Assumptions:**
- Open global layers are adequate for screening, not for allocation decisions.
- Vacancy is biophysical, observed by satellite; legal availability must be confirmed by the Revenue Department.

---

## 8. Team, manpower & expertise

⟨Fill in names, qualifications and prior work for both members.⟩

| Role | Who | Responsibilities |
|---|---|---|
| Lead developer: GIS and remote sensing | Muskan ⟨surname⟩ | Data pipeline, suitability model, validation, dashboard |
| ⟨Second member's role, e.g. agronomy/domain and documentation⟩ | ⟨Name⟩ | Criteria review, user research, field-validation design, documentation |

**Manpower by phase:**
- Prototype: 2 people part-time (done).
- Integration and MVP (Dec 2026 – Mar 2027): 2 full-time, plus about 0.5 FTE of advisory time.
- Pilot validation: department field staff (about 2 days per block for sample verification).

**Critical specialist skills:**
- remote sensing (SAR flood mapping, NDVI time series);
- GIS and multi-criteria modelling;
- agronomy and soil science for criteria;
- web development.

Advisors we will seek: a soil scientist from AAU Jorhat or a KVK, and the ASSAC remote-sensing scientists.

---

## 9. Testing, validation & evidence

**Development testing**
- An automated synthetic end-to-end test (`tests/test_pipeline_synthetic.py`) runs the full pipeline offline on generated data.
- Each layer has a fetch-status log and a data register.
- Every run writes a validation JSON file.

**Quality measures and current evidence (real data, four districts)**
1. **Agreement with official statistics:**
   - Kamrup (R): model vacant and long-fallow land 13,651 ha against DES 31,453 ha (ratio 0.43);
   - Cachar: 13,768 ha against 26,064 ha (0.53);
   - Lakhimpur: 11,402 ha against 23,062 ha (0.49);
   - Dibrugarh: 14,435 ha against 22,546 ha (0.64).
   Including rabi-fallow cropland (a second-crop opportunity), the candidate land is 30,005 / 42,869 / 17,220 / 16,020 ha. The model deliberately leaves out river sand, shifting channels and land that was water in any recent year, so it is conservative.
2. **Farmland plausibility:** 91–99 % of actively double-cropped land scores S1/S2 on biophysical criteria in all four districts. This shows the criteria reward land that is actually productive.
3. **Discrimination:** sites are graded A–D (score ≥ 85, 80–85, 75–80, < 75). Roughly a quarter of the sites fall in each grade, so officials can tell the best land from the marginal. The first uncalibrated version rated almost everything S1; thresholds were then set from Soil Health Card / ICAR norms with a most-limiting-factor rule.
4. **Robustness:** each factor weight was changed by ±20 %. The block ranking stays stable (minimum Spearman ρ 0.99–1.0 in every district, with the same top blocks).
5. **Visual verification:** 120 randomly sampled priority sites (30 per district) were checked against high-resolution Esri World Imagery. 84 (70 %) are consistent with open, fallow or cultivable land, 19 are uncertain (mostly clouds in the imagery) and 17 are doubtful, mainly river islands and banks that have shifted since the 2017–2023 maps. These cases drove two calibration changes (excluding river sand and shifting channels), and the remaining ones are why field verification is built into the workflow.
6. **Data-quality gate:** in Cachar the Sentinel-1 flood layer read waterlogged paddy as flooding (median cropland flood frequency 0.58). An automatic check detected this and the pipeline switched to the JRC/Esri flood proxy.

**Planned pilot metrics:**
- precision of S1/S2 patches against field verification (target ≥ 80 %);
- overall accuracy of the fallow classifier (target ≥ 85 %);
- officer time to shortlist sites (target: from weeks to under one day);
- user satisfaction rating.

---

## 10. Security, privacy, safety & compliance

- **Data protection:**
  - The prototype uses only public, openly licensed data, and its licences (CC BY 4.0, ODbL, Copernicus) are recorded in the data register.
  - It holds no personal data.
  - Cadastral or ownership data, if shared, stays on government servers. It is never published in the public view, and access is role-based.
- **Compliance:**
  - National Geospatial Policy 2022 and Geospatial Guidelines 2021 (open geospatial data, no restricted features).
  - National Data Sharing and Accessibility Policy.
  - DPDP Act 2023 for any personal data in the future (farmer names stay out of scope).
  - Official boundaries from Survey of India / LGD replace geoBoundaries before any official use.
  - Maps carry a disclaimer that boundaries are not authoritative.
- **Security (MVP):**
  - hosting on State Data Centre / ASSAC infrastructure;
  - HTTPS and role-based log-in (viewer, planner, admin);
  - an audit log of criteria changes and downloads;
  - dependency scanning and no secrets in code.
- **Auditability:**
  - Every result can be traced to a config version, data sources and dates, and its factor scores are stored.
  - Runs are reproducible from scripts.
- **Human review and safety:**
  - The tool is decision support, not decision-making.
  - Every shortlisted patch must be verified in the field and checked by the Revenue Department before any allocation.
  - The dashboard shows this message on every result.
  - Excluded classes (forest, wetlands, protected areas, water bodies) are never proposed, which protects ecologically sensitive land.
- **Interoperability:**
  - OGC formats (GeoTIFF, GPKG, GeoJSON, SHP) and planned WMS/WFS mean outputs load into Bhuvan, QGIS, ArcGIS or the department's portal.

---

## 11. Innovation & differentiation

**Prior art:**
- NRSC/Bhuvan wasteland and LULC atlases, and ICAR-NBSS&LUP land evaluation, are authoritative.
- However, they are static, periodic map products. They do not combine availability with suitability, rank sites for a programme, or explain individual results.
- Commercial agri-analytics platforms focus on monitoring existing farms, not finding new land, and are proprietary.

**What is new:**
1. **Availability and suitability in one layer:** the tool identifies land that is both under-used (from multi-year land cover and season-specific NDVI) and suitable, separating "vacant", "long fallow" and "rabi fallow" opportunities.
2. **Explainable at every level:** each cell and patch carries its six factor scores, limiting factor and plain-language reason. This supports accountable decisions and grievance redress.
3. **Programme-aware and live:** different profiles and live weight sliders let each department ask its own question of the same data.
4. **Flood-aware for Assam:** a Sentinel-1 radar flood-frequency layer (cloud-independent during the monsoon) is built into both constraints and scores.
5. **Evidence-checked:** results are compared automatically with official DES statistics and tested for sensitivity.
6. **Replicable at near-zero data cost:**
   - It is built only on free, open data, configuration-driven and runs on a laptop.
   - A new district, state or crop needs no new code.
   - Department data improves results when it becomes available, but is not required to start.

**IP and dependencies:**
- The code is our own and will be offered to the Government of Assam under an open licence (for example Apache 2.0).
- Key dependencies: GDAL, rasterio, geopandas, numpy, scipy, Streamlit, Folium (all open source).
- Data: ESA, Copernicus, JRC, ISRIC, CHIRPS, Esri/IO (CC BY) and OSM (ODbL).
- There are no proprietary dependencies.

---

## 12. Resources, risks & pilot validation

**Resources and cost drivers:**
- Personnel (2 developers and advisory time) is the main cost.
- Compute: a cloud VM or SDC server (8 vCPU, 32 GB RAM, about 500 GB storage) for statewide runs.
- No data licence costs.
- Field verification: department staff time and travel.
- Optional: high-resolution imagery for verification, if ASSAC does not already hold it.
- Indicative MVP budget (Dec 2026 – May 2027): about ₹12 lakh – two developers ₹8 lakh, compute and hosting ₹1 lakh, verification imagery and field-validation support ₹2 lakh, contingency ₹1 lakh. ⟨check and adjust⟩

| Risk | Mitigation |
|---|---|
| Department data access delayed | The prototype is complete on open data; department layers are plug-in replacements |
| Coarse soil data (250 m modelled) | Clearly labelled as screening data; Soil Health Card points used for calibration in Track B |
| Satellite vacancy ≠ legal availability | Revenue Department verification step built into the workflow; no allocation from the model alone |
| Char/riverine land changes yearly | Flood frequency and multi-year land cover; re-run each season |
| Cloud cover in optical imagery | Multi-year seasonal peaks; Sentinel-1 radar for flooding |
| Weight choice is subjective | Stakeholder AHP workshop; sensitivity analysis shown |
| Boundary accuracy | Replace with LGD / Survey of India boundaries from ASSAC |

**Pilot validation (after development):**
1. In Kamrup (Rural) and Cachar, ASSAC and the District Agriculture Office select 3–4 blocks.
2. A stratified random sample of about 100 patches per district (S1, S2, S3 and rejected land) is verified by field staff using a mobile form. The checks cover the land's current use, whether it is vacant, any problems with soil or water, and its legal status from Revenue.
3. We report precision and accuracy, then re-calibrate thresholds and weights and train the ML classifier on the verified points.
4. Success criteria: at least 80 % of S1/S2 patches confirmed as cultivable and available, and officers confirming the tool shortens site selection.
5. After the pilot, a statewide run and integration with the departments' programme planning.
