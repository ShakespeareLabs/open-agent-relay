# Read-only campaign report

This zero-dependency example proves the complete Relay path without calling a model. The CSV remains on the publisher computer; callers receive only the calculated report.

## Publisher

```bash
export RELAY_ACCESS_KEY="replace-with-at-least-16-characters"
./serve.sh
```

Replace `campaigns.csv` with data using the same columns to reuse the example. Keep real source data out of version control.

## Caller

```bash
export RELAY_ACCESS_KEY="replace-with-at-least-16-characters"
relay ask \
  --target http://PUBLISHER_LAN_IP:8787 \
  --expect-agent campaign-report \
  --json \
  "Summarize all campaigns"
```

Mention an exact campaign name to limit the report:

```bash
relay ask --target http://PUBLISHER_LAN_IP:8787 \
  --expect-agent campaign-report --json \
  "Summarize Launch Retargeting"
```
