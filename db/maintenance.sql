-- Optional OFFLINE maintenance. CLUSTER takes an ACCESS EXCLUSIVE lock.
-- Run only in a maintenance window after bulk imports, never per request/startup.
CLUSTER complaints USING ix_complaints_road_time;
ANALYZE complaints;
ANALYZE assignments;
ANALYZE point_entries;
