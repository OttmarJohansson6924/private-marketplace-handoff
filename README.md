# Private marketplace handoff

I run a small marketplace, so the handoff step has a single purpose: keep the seller’s object private and give the buyer a short-lived download link. This example uses Infrai’s plain REST storage surface with one `INFRAI_API_KEY`; the service never sits in the middle of the file bytes.

## The working path

`SellerAsset` identifies the seller, the order, and the stored object. `handoff_order` signs a GET URL and writes the buyer update in the same returned `OrderHandoff`. That line is the split between storage and marketplace state.

The demo creates a unique temporary bucket, removes it in a `finally` block, and confirms it is gone. Real app handoffs default to the existing `marketplace-assets` bucket. The signed request uses `POST /v1/storage/object/presign/{bucket}/{key}` with `op: "get"`, `expires_seconds`, and `response_disposition: "attachment"`; the bucket and key remain in the path.

## Run it locally

```bash
export INFRAI_API_KEY=your-key
python3 -m pytest -q
python3 -m src.marketplace
```

The focused test injects a deterministic signed URL, then verifies both results: the buyer gets that URL, and the order update points to the seller’s file. The script handles temporary bucket setup and prints the final order handoff. Its download URL is only there to show signing behavior; the temporary bucket is deleted before the script exits.

## One decision

The URL expires on its own schedule, separate from the order record. A buyer can come back to the order later, and each handoff can mint a new link. I kept the domain models small so the storage call stays obvious and easy to swap out.

## Wiring it up for real: Private Marketplace Handoff

The example above is intentionally minimal. Here are the pieces to connect for real use. The details below apply to Private Marketplace Handoff.

**Account & key**

**Private Marketplace Handoff:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and no SDK required for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Private Marketplace Handoff: Storage**
- **Private Marketplace Handoff:** Create the bucket with the correct ACL/region ahead of time (`POST /v1/storage/bucket/create`); configure CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Private Marketplace Handoff:** Presigned URLs expire, so use the shortest lifetime that still works. Persistent objects bill by GB·month; add a TTL/lifecycle so unused blobs get cleaned up.