# k - SPECIES COMMON NAMES
#
# Looks up English common names for Latin species names from GBIF.
# Results are cached in data/reference/ecology_common_names.csv so the
# API is only called for new species; all subsequent runs read the cache.

import time
import requests
import pandas as pd

from .a_config import REPO_BASE

CACHE_PATH = REPO_BASE / "data" / "reference" / "ecology_common_names.csv"
GBIF_MATCH  = "https://api.gbif.org/v1/species/match"
GBIF_VNAMES = "https://api.gbif.org/v1/species/{}/vernacularNames"
PAUSE = 0.3   # seconds between requests


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        df = pd.read_csv(CACHE_PATH)
        return dict(zip(df["latin_name"], df["common_name"].fillna("")))
    return {}


def _save_cache(lookup: dict):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        list(lookup.items()), columns=["latin_name", "common_name"]
    ).to_csv(CACHE_PATH, index=False)


def _fetch_one(latin_name: str) -> str:
    """Return English common name from GBIF, or '' if not found."""
    try:
        r = requests.get(GBIF_MATCH, params={"name": latin_name}, timeout=10)
        usage_key = r.json().get("usageKey")
        if not usage_key:
            return ""
        time.sleep(PAUSE)
        vr = requests.get(GBIF_VNAMES.format(usage_key), timeout=10)
        results = vr.json().get("results", [])
        # English entries only — no fallback to other languages
        for v in results:
            if v.get("language", "").lower() in ("eng", "en", "english"):
                return v.get("vernacularName", "")
    except Exception:
        pass
    return ""


def get_common_names(latin_names: list) -> dict:
    """
    Return {latin_name: common_name} for every name in the list.
    Only queries GBIF for names not already in the local cache.
    """
    lookup = _load_cache()
    uncached = [n for n in latin_names if n and n not in lookup]

    if uncached:
        print(f"[species_names] Fetching common names for {len(uncached)} new species…")
        for i, name in enumerate(uncached, 1):
            lookup[name] = _fetch_one(name)
            time.sleep(PAUSE)
            if i % 25 == 0:
                print(f"  {i}/{len(uncached)} done")
        _save_cache(lookup)
        print(f"[species_names] Cache saved → {CACHE_PATH.name}")

    return lookup
