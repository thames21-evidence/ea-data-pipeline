import geopandas as gpd
from pathlib import Path
from math import ceil, sqrt, radians, sin, cos, atan2

REPO_BASE = Path(__file__).resolve().parent.parent
SHP = REPO_BASE / "data" / "gis" / "thames21_scorecard_waterbodies.shp"


def haversine_km(lon1, lat1, lon2, lat2):
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2) ** 2
    c = 2 * atan2(a ** 0.5, (1 - a) ** 0.5)
    return R * c


def generate_grid_points(minx, miny, maxx, maxy, max_points=25):
    width = maxx - minx
    height = maxy - miny
    if width <= 0 or height <= 0:
        return [((minx + maxx) / 2.0, (miny + maxy) / 2.0)]
    aspect = width / height if height > 0 else 1.0
    nx = max(1, int(ceil(sqrt(max_points * aspect))))
    ny = max(1, int(ceil(max_points / nx)))
    while nx * ny > max_points:
        if nx >= ny:
            nx -= 1
        else:
            ny -= 1
    dx = width / nx
    dy = height / ny
    points = []
    for i in range(nx):
        for j in range(ny):
            cx = minx + (i + 0.5) * dx
            cy = miny + (j + 0.5) * dy
            points.append((cx, cy))
    return points, nx, ny, dx, dy


if __name__ == '__main__':
    gdf = gpd.read_file(SHP).to_crs('EPSG:4326')
    # choose group field
    group_field = None
    for col in ("CaBA_Catch", "WB_NAME", "wb_name", "name", "label"):
        if col in gdf.columns:
            group_field = col
            break
    if group_field is None:
        obj_cols = [c for c in gdf.columns if gdf[c].dtype == object]
        group_field = obj_cols[0] if obj_cols else None
    if group_field is None:
        raise SystemExit('No grouping field')

    dissolved = gdf.dissolve(by=group_field).reset_index()
    print(f"Found {len(dissolved)} dissolved catchments grouped by '{group_field}'\n")

    MAX_POINTS = 100

    for idx, row in dissolved.iterrows():
        name = row[group_field]
        minx, miny, maxx, maxy = row.geometry.bounds
        pts, nx, ny, dx, dy = generate_grid_points(minx, miny, maxx, maxy, max_points=MAX_POINTS)
        total = len(pts)
        # estimate km spacing using haversine between two neighbouring centres (if possible)
        if nx > 1:
            # pick two adjacent horizontally
            a = (minx + (0.5) * dx, miny + (0.5) * dy)
            b = (minx + (1.5) * dx, miny + (0.5) * dy)
            dx_km = haversine_km(a[0], a[1], b[0], b[1])
        else:
            dx_km = None
        if ny > 1:
            a = (minx + (0.5) * dx, miny + (0.5) * dy)
            b = (minx + (0.5) * dx, miny + (1.5) * dy)
            dy_km = haversine_km(a[0], a[1], b[0], b[1])
        else:
            dy_km = None

        print(f"Catchment: {name}")
        print(f"  bbox: ({minx:.6f}, {miny:.6f}) - ({maxx:.6f}, {maxy:.6f})")
        print(f"  grid points: {total} (nx={nx}, ny={ny})")
        print(f"  dx,dy (deg): {dx:.6f}, {dy:.6f}")
        if dx_km is not None:
            print(f"  dx ~ {dx_km:.2f} km")
        if dy_km is not None:
            print(f"  dy ~ {dy_km:.2f} km")
        sample = pts[:min(9, total)]
        print(f"  sample centres (lon,lat):")
        for s in sample:
            print(f"    {s[0]:.6f},{s[1]:.6f}")
        print()
