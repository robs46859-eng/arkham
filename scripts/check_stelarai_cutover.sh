#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-arkham-492414}"

custom_domains=(
  "projects/${PROJECT_ID}/sites/stelarai-tech/customDomains/stelarai.tech"
  "projects/${PROJECT_ID}/sites/stelarai-tech/customDomains/www.stelarai.tech"
  "projects/${PROJECT_ID}/sites/solamaze-com/customDomains/solamaze.com"
  "projects/${PROJECT_ID}/sites/solamaze-com/customDomains/www.solamaze.com"
  "projects/${PROJECT_ID}/sites/getsemu-com/customDomains/getsemu.com"
  "projects/${PROJECT_ID}/sites/getsemu-com/customDomains/www.getsemu.com"
)

print_heading() {
  printf '\n== %s ==\n' "$1"
}

print_heading "Hosting targets"
(
  cd /Users/joeiton/Projects/fsdash
  firebase target
)

for zone in stelarai-tech solamaze-com getsemu-com; do
  print_heading "Cloud DNS zone ${zone}"
  gcloud dns record-sets list --zone="${zone}" --project="${PROJECT_ID}"
done

print_heading "Load balancer host rules"
gcloud compute url-maps describe arkham-url-map --global --project "${PROJECT_ID}"

print_heading "HTTPS proxy certificates"
gcloud compute target-https-proxies describe arkham-https-proxy --global --project "${PROJECT_ID}"

print_heading "StelarAI API certificate"
gcloud compute ssl-certificates describe stelarai-api-cert --global --project "${PROJECT_ID}"

print_heading "Firebase custom-domain states"
ACCESS_TOKEN="$(gcloud auth print-access-token)"
for name in "${custom_domains[@]}"; do
  curl -sS \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "X-Goog-User-Project: ${PROJECT_ID}" \
    "https://firebasehosting.googleapis.com/v1beta1/${name}" |
    python3 -c 'import json,sys; obj=json.load(sys.stdin); print(obj["name"]); print("  hostState:", obj.get("hostState")); print("  ownershipState:", obj.get("ownershipState")); print("  certState:", obj.get("cert", {}).get("state")); print()'
done
