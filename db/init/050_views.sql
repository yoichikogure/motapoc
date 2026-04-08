CREATE OR REPLACE VIEW mart.latest_overview AS
WITH latest AS (SELECT MAX(month_index) AS month_index FROM core.fact_visitors_monthly)
SELECT
    g.governorate_id,
    g.governorate_code,
    g.governorate_name_en,
    v.total_visitors,
    rb.total_rooms,
    rb.total_beds,
    o.average_occupancy_rate
FROM core.governorate g
LEFT JOIN latest l ON TRUE
LEFT JOIN core.fact_visitors_monthly v ON v.governorate_id = g.governorate_id AND v.month_index = l.month_index
LEFT JOIN core.fact_rooms_beds_monthly rb ON rb.governorate_id = g.governorate_id AND rb.month_index = l.month_index
LEFT JOIN core.fact_hotel_occupancy_monthly o ON o.governorate_id = g.governorate_id AND o.month_index = l.month_index;
