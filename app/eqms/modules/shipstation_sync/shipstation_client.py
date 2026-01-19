from __future__ import annotations

import base64
import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


class ShipStationError(RuntimeError):
    pass


class ShipStationRateLimited(ShipStationError):
    pass


@dataclass(frozen=True)
class ShipStationClient:
    api_key: str
    api_secret: str
    base_url: str = "https://ssapi.shipstation.com"
    timeout_seconds: int = 60

    def _auth_header(self) -> str:
        token = f"{self.api_key}:{self.api_secret}".encode("utf-8")
        return "Basic " + base64.b64encode(token).decode("ascii")

    def request_json(self, path: str, *, params: dict[str, Any] | None = None, retries: int = 3) -> dict[str, Any]:
        url = self.base_url.rstrip("/") + path
        if params:
            url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})

        last_err: Exception | None = None
        for attempt in range(retries + 1):
            try:
                req = urllib.request.Request(url, method="GET")
                req.add_header("Authorization", self._auth_header())
                req.add_header("Accept", "application/json")
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    raw = resp.read()
                    try:
                        return json.loads(raw.decode("utf-8"))
                    except Exception as e:
                        raise ShipStationError(f"Invalid JSON from ShipStation ({path})") from e
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    # rate limit; brief backoff
                    time.sleep(min(2 * (attempt + 1), 10))
                    last_err = ShipStationRateLimited("Rate limited (429)")
                    continue
                try:
                    body = e.read().decode("utf-8", errors="ignore")
                except Exception:
                    body = ""
                raise ShipStationError(f"HTTP {e.code} from ShipStation: {body[:300]}") from e
            except Exception as e:
                last_err = e
                time.sleep(min(1 * (attempt + 1), 5))
                continue
        raise ShipStationError(f"ShipStation request failed after retries: {last_err}")

    def list_orders(self, *, create_date_start: str, create_date_end: str, page: int, page_size: int = 100) -> list[dict[str, Any]]:
        j = self.request_json(
            "/orders",
            params={
                "createDateStart": create_date_start,
                "createDateEnd": create_date_end,
                "page": page,
                "pageSize": page_size,
            },
        )
        orders = j.get("orders") or []
        return orders if isinstance(orders, list) else []

    def get_order(self, order_id: str) -> dict[str, Any]:
        j = self.request_json(f"/orders/{urllib.parse.quote(str(order_id))}")
        return j if isinstance(j, dict) else {}

    def list_shipments_for_order(self, order_id: str, *, page: int, page_size: int = 100) -> list[dict[str, Any]]:
        j = self.request_json(
            "/shipments",
            params={"orderId": order_id, "page": page, "pageSize": page_size},
        )
        shipments = j.get("shipments") or []
        return shipments if isinstance(shipments, list) else []

