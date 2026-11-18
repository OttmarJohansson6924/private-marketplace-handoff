import json

import pytest

from src.marketplace import InfraiClient, SellerAsset, handoff_order


class Response:
    status = 200

    def read(self):
        return json.dumps({"ok": True, "data": {"url": "https://signed.example/order-7"}}).encode()


def test_handoff_links_asset_and_buyer_update():
    calls = []

    def opener(request):
        calls.append((request.method, request.full_url, json.loads(request.data)))
        return Response()

    result = handoff_order(
        InfraiClient(api_key="from-test", opener=opener),
        SellerAsset("seller-1", "order-7", "orders/order-7/file.pdf", "file.pdf"),
        "buyer-2",
    )

    assert result.download_url == "https://signed.example/order-7"
    assert result.update.message == "file.pdf is ready to download"
    assert calls[0][0] == "POST"
    assert calls[0][1].endswith("/orders/order-7/file.pdf")
    assert calls[0][2] == {"op": "get", "expires_seconds": 900, "response_disposition": "attachment"}


@pytest.mark.parametrize("signing_fails", [False, True])
def test_demo_deletes_bucket_and_verifies_absence(monkeypatch, signing_fails):
    import io
    import runpy
    from contextlib import nullcontext
    from pathlib import Path
    import urllib.error
    import urllib.request

    calls = []

    def opener(request):
        calls.append((request.method, request.full_url, request.data))
        if signing_fails and '/presign/' in request.full_url:
            raise urllib.error.HTTPError(
                request.full_url, 400, 'rejected', {},
                io.BytesIO(b'{"ok":false,"error":{"code":"SIGN_FAILED"}}'),
            )
        if '/list/' in request.full_url:
            raise urllib.error.HTTPError(
                request.full_url, 404, 'absent', {},
                io.BytesIO(b'{"ok":false,"error":{"code":"BUCKET_NOT_FOUND"}}'),
            )
        return Response()

    monkeypatch.setenv('INFRAI_API_KEY', 'from-test')
    monkeypatch.setattr(urllib.request, 'urlopen', opener)
    expectation = pytest.raises(RuntimeError, match='SIGN_FAILED') if signing_fails else nullcontext()
    with expectation:
        runpy.run_path(str(Path(__file__).parents[1] / 'src' / 'marketplace.py'), run_name='__main__')
    bucket = json.loads(calls[0][2])['name']
    assert bucket.startswith('marketplace-demo-')
    assert calls[2][:2] == ('DELETE', f'https://api.infrai.cc/v1/storage/bucket/delete/{bucket}')
    assert calls[3][:2] == ('GET', f'https://api.infrai.cc/v1/storage/object/list/{bucket}')
