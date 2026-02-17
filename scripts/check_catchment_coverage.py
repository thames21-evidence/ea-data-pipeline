import geopandas as gpd
from pathlib import Path
from math import radians, sin, cos, atan2, sqrt

SHAPE = Path(r"c:\Users\HarrisonTremain\Documents\thames21-data-pull\data\gis\thames21_scorecard_waterbodies.shp")
RADIUS_KM = 25.0

def haversine_km(lon1, lat1, lon2, lat2):
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

if not SHAPE.exists():
    print('Shapefile not found:', SHAPE)
    raise SystemExit(1)

g = gpd.read_file(SHAPE).to_crs('EPSG:4326')
# prefer grouping field
group_field = None
for c in ("CaBA_Catch", "WB_NAME", "wb_name", "name", "label"):
    if c in g.columns:
        group_field = c
        break

if group_field is None:
    print('No grouping field found; using each feature separately')
    groups = [(str(i), geom) for i, geom in enumerate(g.geometry)]
else:
    dissolved = g.dissolve(by=group_field).reset_index()
    groups = [(row[group_field], row.geometry) for _, row in dissolved.iterrows()]

print(f"Checking coverage with radius = {RADIUS_KM} km (representative_point center).\n")
print(f"{'Catchment':40s} {'RepLat':8s} {'RepLon':8s} {'MaxDist_km':10s} {'Covered'}")
print('-'*80)

for name, geom in groups:
    try:
        rep = geom.representative_point()
        rep_lat = rep.y
        rep_lon = rep.x
        maxd = 0.0
        # iterate exterior coords of all parts
        if geom.type == 'Polygon':
            parts = [geom]
        else:
            parts = list(geom.geoms)
        for part in parts:
            # exterior
            for lon, lat in part.exterior.coords:
                d = haversine_km(rep_lon, rep_lat, lon, lat)
                if d > maxd:
                    maxd = d
            # include interiors? (holes) not needed
        covered = maxd <= RADIUS_KM
        print(f"{str(name)[:40]:40s} {rep_lat:8.4f} {rep_lon:8.4f} {maxd:10.3f} {str(covered)}")
    except Exception as e:
        print(f"{str(name)[:40]:40s} ERROR computing: {e}")
