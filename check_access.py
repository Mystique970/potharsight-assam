"""Step 1: check that this computer can reach the open data sources (no login needed).
Each layer has a primary and backup source; the pipeline needs at least one per layer.
Run:  python check_access.py
"""
import requests

H = {"User-Agent": "d13-agri-suitability/1.0 (NESFIC 2026 research prototype; python-requests)", "Accept": "*/*"}
TESTS = {
    "Satellite catalogue A: Planetary Computer": [("GET", "https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a")],
    "Satellite catalogue B: Earth Search (AWS)": [("GET", "https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a")],
    "Land cover backup: ESA WorldCover (AWS)": [("HEAD", "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N24E090_Map.tif")],
    "Elevation backup: Copernicus DEM (AWS)": [("HEAD", "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N26_00_E091_00_DEM/Copernicus_DSM_COG_10_N26_00_E091_00_DEM.tif")],
    "Land-use history backup: Esri LULC": [("HEAD", "https://lulctimeseries.blob.core.windows.net/lulctimeseriesv003/lc2023/46R_20230101-20240101.tif")],
    "Soil: ISRIC SoilGrids": [("HEAD", "https://files.isric.org/soilgrids/latest/data/soc/soc_0-5cm_mean.vrt")],
    "Rainfall: CHIRPS v3 or v2": [("HEAD", "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/annual/global/tifs/chirps-v3.0.2020.tif"),
                                 ("HEAD", "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_annual/tifs/chirps-v2.0.2020.tif")],
    "Surface water: JRC (Google Storage)": [("HEAD", "https://storage.googleapis.com/global-surface-water/downloads2021/occurrence/occurrence_90E_30Nv1_4_2021.tif")],
    "Roads/towns: OpenStreetMap Overpass (any mirror)": [
        ("POST", u) for u in ["https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter",
                              "https://overpass.kumi.systems/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]],
}
for name, tries in TESTS.items():
    res = []
    for method, url in tries:
        try:
            if method == "POST":
                r = requests.post(url, data={"data": "[out:json];node(26.1,91.7,26.11,91.71);out 1;"}, headers=H, timeout=60)
            else:
                r = requests.request(method, url, headers=H, timeout=30, allow_redirects=True)
            code = r.status_code
        except Exception as e:  # noqa: BLE001
            code = type(e).__name__
        res.append(code)
        if code == 200:
            break
    print(f"{'OK  ' if 200 in res else 'FAIL'}  {name}   {res}")
print("\nKeep these lines for troubleshooting. The pipeline uses whichever source works for each layer.")
