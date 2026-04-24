# StelarAI Domain Cutover Note

Date: 2026-04-24

## Why this repo matters

`arkham` is the control-plane and documentation repo for the cross-project cutover.

This repo now contains:

- `docs/stelarai-tech-build-plan.md`
- `docs/stelarai-tech-agent-spec.md`
- `scripts/check_stelarai_cutover.sh`
- `scripts/stelarai_api_smoke.py`

## Canonical domain intent

- `stelarai.tech` and `www.stelarai.tech` -> Firebase Hosting
- `api.stelarai.tech` -> Google load balancer -> `fs-ai`
- `solamaze.com` and `www.solamaze.com` -> Firebase Hosting
- `getsemu.com` and `www.getsemu.com` -> Firebase Hosting

## Registrar nameservers

- `stelarai.tech`
  - `ns-cloud-d1.googledomains.com`
  - `ns-cloud-d2.googledomains.com`
  - `ns-cloud-d3.googledomains.com`
  - `ns-cloud-d4.googledomains.com`
- `solamaze.com`
  - `ns-cloud-b1.googledomains.com`
  - `ns-cloud-b2.googledomains.com`
  - `ns-cloud-b3.googledomains.com`
  - `ns-cloud-b4.googledomains.com`
- `getsemu.com`
  - `ns-cloud-a1.googledomains.com`
  - `ns-cloud-a2.googledomains.com`
  - `ns-cloud-a3.googledomains.com`
  - `ns-cloud-a4.googledomains.com`

## Current project-side state

- Hosting sites exist for `stelarai-tech`, `solamaze-com`, and `getsemu-com`
- Cloud DNS records have been written for the new frontend domains
- `api.stelarai.tech` is wired to the `fs-ai` load balancer path matcher
- `stelarai-api-cert` exists and is attached, but still must converge to `ACTIVE`
- Firebase custom domains exist, but public ownership and certificate state still need to converge

## Operational checks

- Use `scripts/check_stelarai_cutover.sh` for GCP and Firebase state readback.
- Use `scripts/stelarai_api_smoke.py` for authenticated StelarAI CRUD smoke tests after auth and DNS are ready.
