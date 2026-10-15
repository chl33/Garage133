```bash
python3 src/download/download.py \
    --start "2026-02-27 10:00:00" \
    --end "2026-02-27 10:15:00" \
    --left-state "closed_empty" \
    --right-state "closed_car"
```

Key Improvements:
- Flexible Formatting: Works with "2026-02-27 10:00", "02/27/2026 10am", or even "today 10:00".
- Automatic UTC Conversion: InfluxDB still gets the UTC ISO strings it requires, but you don't have to do the math yourself.
- Timezone Argument: If you ever need to use a different timezone, you can pass --timezone "UTC" or any other IANA name.
- Static State Labeling: Trimming and downloads label steady-state garage conditions without state transitions.
