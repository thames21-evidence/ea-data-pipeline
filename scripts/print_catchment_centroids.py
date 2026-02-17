import geopandas as gpd
from pathlib import Path

shp = Path(r"c:\Users\HarrisonTremain\Documents\thames21-data-pull\data\gis\thames21_scorecard_waterbodies.shp")
if not shp.exists():
    print('Shapefile not found:', shp)
    raise SystemExit(1)

g = gpd.read_file(shp).to_crs('EPSG:4326')

for i, row in g.iterrows():
    name = None
    for col in ('CaBA_Catch', 'WB_NAME', 'wb_name', 'name', 'label'):
        if col in row and row[col] is not None:
            name = row[col]
            break
    if name is None:
        name = f'catch_{i}'
    c = row.geometry.centroid
    print(f"{name}\t{c.y:.6f}\t{c.x:.6f}")
