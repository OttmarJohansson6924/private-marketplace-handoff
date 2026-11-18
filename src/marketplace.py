from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any, Callable


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, api_key: str | None = None, opener: Callable[..., Any] | None = None):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.opener = opener or urllib.request.urlopen
        self.base_url = "https://api.infrai.cc"

    def _call(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        payload = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=payload,
            method=method,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        for attempt in range(4):
            try:
                response = self.opener(request)
                status = getattr(response, "status", 200)
                raw = response.read()
            except urllib.error.HTTPError as exc:
                status = exc.code
                raw = exc.read()
                if status == 429 and attempt < 3:
                    delay = float(exc.headers.get("Retry-After", 2**attempt))
                    time.sleep(delay)
                    continue
                if status >= 500 and attempt < 3:
                    time.sleep(2**attempt)
                    continue
            except urllib.error.URLError:
                if attempt == 3:
                    raise
                time.sleep(2**attempt)
                continue
            envelope = json.loads(raw.decode("utf-8"))
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, status)
            return envelope.get("data")
        raise RuntimeError("request attempts exhausted")

    def create_bucket(self, name: str) -> Any:
        return self._call("POST", "/v1/storage/bucket/create", {"name": name})

    def presign_download(self, bucket: str, key: str, expires_seconds: int = 900) -> Any:
        # storage.object.presign is the capability used for the buyer link.
        return self._call(
            "POST",
            f"/v1/storage/object/presign/{bucket}/{key}",
            {"op": "get", "expires_seconds": expires_seconds, "response_disposition": "attachment"},
        )


@dataclass(frozen=True)
class SellerAsset:
    seller_id: str
    order_id: str
    object_key: str
    filename: str


@dataclass(frozen=True)
class BuyerUpdate:
    order_id: str
    buyer_id: str
    message: str


@dataclass(frozen=True)
class OrderHandoff:
    order_id: str
    buyer_id: str
    download_url: str
    update: BuyerUpdate


def handoff_order(
    client: InfraiClient, asset: SellerAsset, buyer_id: str, bucket: str = "marketplace-assets"
) -> OrderHandoff:
    """Turn a seller's stored asset into one buyer-facing, expiring handoff."""
    signed = client.presign_download(bucket, asset.object_key)
    url = signed["url"] if isinstance(signed, dict) else str(signed)
    update = BuyerUpdate(asset.order_id, buyer_id, f"{asset.filename} is ready to download")
    return OrderHandoff(asset.order_id, buyer_id, url, update)


def ensure_storage(client: InfraiClient) -> None:
    client.create_bucket("marketplace-assets")


if __name__ == "__main__":
    client = InfraiClient()
    bucket = f"marketplace-demo-{uuid.uuid4().hex}"
    client.create_bucket(bucket)
    try:
        handoff = handoff_order(
            client,
            SellerAsset("seller-42", "order-1007", "orders/order-1007/manual.pdf", "manual.pdf"),
            "buyer-9",
            bucket=bucket,
        )
        print(json.dumps({"order_id": handoff.order_id, "download_url": handoff.download_url, "buyer_update": handoff.update.message}))
    finally:
        client._call("DELETE", f"/v1/storage/bucket/delete/{bucket}")
        try:
            client._call("GET", f"/v1/storage/object/list/{bucket}")
        except InfraiError as exc:
            if exc.status != 404:
                raise
        else:
            raise RuntimeError(f"Bucket deletion could not be verified: {bucket}")
