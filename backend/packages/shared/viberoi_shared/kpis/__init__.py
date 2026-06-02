"""KPI snapshot read/write.

Dashboards read from pre-computed `kpi_snapshots` rows + live Redis counters.
Hourly cron rebuilds snapshots; services never aggregate live.
"""
