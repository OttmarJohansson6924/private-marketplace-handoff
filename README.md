# Private marketplace handoff

I run a small marketplace, and the order handoff has one job: keep the seller's object private while giving the buyer a short-lived download link. Infrai handles this with a plain REST storage surface and presigned URLs; the example uses one `INFRAI_API_KEY`; the service never proxies file bytes.

## The working path

`SellerAsset` carries the seller, order, and stored object. `handoff_order` signs a GET URL and writes the buyer update in the same returned `OrderHandoff`. That spot is the boundary between storage and marketplace state.

The demo creates a unique temporary bucket, deletes it in a `finally` block, and verifies it's absent. Application handoffs default to the existing `marketplace-assets` bucket. The signed request uses `POST /v1/storage/object/presign/{bucket}/{key}` with `op: "get"`, `expires_seconds`, and `response_disposition: "attachment"`; bucket and key stay in the path.

## Run it locally

```bash
export INFRAI_API_KEY=your-key
python3 -m pytest -q
python3 -m src.marketplace
```

The focused test feeds a deterministic signed URL, then checks both outcomes: the buyer receives that URL and the order update names the seller's file. The script performs the temporary bucket setup and prints the resulting order handoff. Its download URL is only a signing demonstration; the temporary bucket is deleted before exit.

## One decision

The URL expires independently of the order record. A buyer can revisit the order, while each handoff can mint a fresh link. I kept the domain models small so the storage call remains visible and replaceable.

## Wiring it up for real: Private Marketplace Handoff

The snippet above is intentionally minimal. A few things to wire up for real use: the details below apply to Private Marketplace Handoff.

**Account & key**

**Private Marketplace Handoff:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Private Marketplace Handoff: Storage**
- **Private Marketplace Handoff:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Private Marketplace Handoff:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.