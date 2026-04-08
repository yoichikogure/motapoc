#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"
COOKIE_JAR="$(mktemp)"
trap 'rm -f "$COOKIE_JAR"' EXIT

echo "Checking root page..."
curl -fsS "$BASE_URL/" >/dev/null

echo "Checking health..."
curl -fsS "$BASE_URL/health" >/dev/null

echo "Logging in..."
curl -fsS -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' \
  "$BASE_URL/api/auth/login" >/dev/null

echo "Checking authenticated overview endpoints..."
curl -fsS -c "$COOKIE_JAR" -b "$COOKIE_JAR" "$BASE_URL/api/overview/kpis" >/dev/null
curl -fsS -c "$COOKIE_JAR" -b "$COOKIE_JAR" "$BASE_URL/api/overview/regions" >/dev/null
curl -fsS -c "$COOKIE_JAR" -b "$COOKIE_JAR" "$BASE_URL/api/overview/map" >/dev/null

echo "Triggering indicator recompute..."
curl -fsS -c "$COOKIE_JAR" -b "$COOKIE_JAR" -X POST "$BASE_URL/api/analytics/recompute" >/dev/null

echo "Triggering forecast..."
curl -fsS -c "$COOKIE_JAR" -b "$COOKIE_JAR" -X POST "$BASE_URL/api/forecasts/run" >/dev/null

echo "Checking forecast runs..."
curl -fsS -c "$COOKIE_JAR" -b "$COOKIE_JAR" "$BASE_URL/api/forecasts/runs" >/dev/null

echo "Triggering simulation..."
curl -fsS -c "$COOKIE_JAR" -b "$COOKIE_JAR" -X POST "$BASE_URL/api/simulations/run" \
  -H 'Content-Type: application/json' \
  -d '{"governorate_id":2,"target_month":"2026-12-01","additional_beds":500,"additional_rooms":200,"induced_demand_ratio":0.05}' >/dev/null

echo "Checking export endpoints..."
curl -fsS -c "$COOKIE_JAR" -b "$COOKIE_JAR" "$BASE_URL/api/exports/overview.csv" >/dev/null
curl -fsS -c "$COOKIE_JAR" -b "$COOKIE_JAR" "$BASE_URL/api/exports/executive-summary.html" >/dev/null

echo "Smoke test passed."
