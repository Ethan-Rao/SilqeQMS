# ShipStation Sync — Acceptance Tests (Production / Browser-only)

## Required DigitalOcean environment variables

- `SHIPSTATION_API_KEY`
- `SHIPSTATION_API_SECRET`
- `SHIPSTATION_DEFAULT_DAYS` (optional, default `30`)
- `SHIPSTATION_LOTLOG_PATH` (optional, default `app/eqms/data/LotLog.csv`)

## How to run the sync

1. Log in as Admin.
2. Go to `Admin` → `ShipStation`.
3. Click **Run Sync**.
4. You should see a success flash message and a new row in **Recent runs**.

## Expected outcomes (what to verify)

- **Distribution entries appear**
  - Go to `Distribution Log`
  - Filter `Source=shipstation`
  - Confirm new rows exist

- **Customers created/linked**
  - Go to `Customers`
  - Search by a facility name you know was shipped to
  - Open the customer and confirm “Recent distributions” shows ShipStation-sourced entries

- **Run summary updated**
  - Go back to `ShipStation`
  - Confirm the latest run shows non-zero `Orders`, `Shipments`, and either `Synced` or `Skipped`

- **Skipped reasons visible**
  - On `ShipStation`, confirm “Recent skipped” shows `reason` codes (e.g. `no_shipments`, `no_valid_items`, `duplicate_external_key`)

- **Idempotency**
  - Click **Run Sync** again immediately
  - Expect **few or zero new** `shipstation` distribution rows (duplicates are skipped via `external_key`)

