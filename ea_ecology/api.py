import time
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
from typing import Optional

# Default base URL for the EA ecology API
BASE_URL = "https://environment.data.gov.uk/ecology/api/v1"


def get_session(total_retries: int = 5, backoff: float = 0.5):
    s = requests.Session()
    retries = Retry(total=total_retries, backoff_factor=backoff, status_forcelist=(429, 500, 502, 503, 504))
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://", HTTPAdapter(max_retries=retries))
    return s


SESSION = get_session()



def fetch_json(endpoint, params=None, max_attempts: int = 6, base_url: Optional[str] = None, session: Optional[requests.Session] = None):
    url = f"{(base_url or BASE_URL).rstrip('/')}/{endpoint.lstrip('/')}"
    params = params or {}
    attempt = 0
    backoff = 1.0
    sess = session or SESSION
    while attempt < max_attempts:
        attempt += 1
        try:
            r = sess.get(url, params=params, timeout=20)
        except Exception as e:
            print(f"fetch_json network error for {url} attempt={attempt}: {e}")
            time.sleep(backoff)
            backoff *= 2
            continue

        if r.status_code in (403, 429) or 500 <= r.status_code < 600:
            print(f"fetch_json transient status {r.status_code} for {url} attempt={attempt}; backing off {backoff}s")
            time.sleep(backoff)
            backoff *= 2
            continue

        try:
            r.raise_for_status()
        except Exception as e:
            print(f"fetch_json error for {url}: {e}")
            return []

        try:
            data = r.json()
        except Exception:
            return []

        if isinstance(data, dict):
            for k in ("items", "results", "features", "data"):
                if k in data and isinstance(data[k], list):
                    return data[k]
            return [data]
        return data if isinstance(data, list) else [data]


def fetch_all(endpoint, params=None, pagination_sleep: float = 1.0, session: Optional[requests.Session] = None, base_url: Optional[str] = None):
    out = []
    skip = 0
    take = 250
    params = params.copy() if params else {}
    sess = session or SESSION
    while True:
        params.update({"skip": skip, "take": take})
        try:
            items = fetch_json(endpoint, params=params, base_url=base_url, session=sess)
        except Exception as e:
            print(f"fetch_all error for {endpoint} params={params}: {e}")
            return out
        if not items:
            break
        out.extend(items)
        if len(items) < take:
            break
        skip += take
        time.sleep(pagination_sleep)
    return out



def safe_save(df: pd.DataFrame, out_path: Path):
    # Write atomically: write to a temp file in the same directory then replace
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    try:
        df.to_csv(tmp_path, index=False)
        # atomic replace
        tmp_path.replace(out_path)
    except PermissionError:
        alt = out_path.with_name(out_path.stem + "_new" + out_path.suffix)
        print(f"PermissionError writing {out_path.name}, saving as {alt.name}")
        df.to_csv(alt, index=False)
    except Exception as e:
        # cleanup tmp if exists
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass
        raise
