INSERT INTO admin.app_user (username, password_hash, role_name, full_name, is_active) VALUES
('admin','240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9','admin','System Administrator',TRUE)
ON CONFLICT (username) DO NOTHING;

INSERT INTO core.governorate (governorate_id, governorate_code, governorate_name_en, governorate_name_ar) VALUES
(1,'AMM','Amman','عمان'),
(2,'AQA','Aqaba','العقبة'),
(3,'BAL','Balqa','البلقاء'),
(4,'IRB','Irbid','إربد'),
(5,'JER','Jerash','جرش'),
(6,'KAR','Karak','الكرك'),
(7,'MAA','Ma''an','معان'),
(8,'MAD','Madaba','مادبا'),
(9,'MAF','Mafraq','المفرق'),
(10,'TAF','Tafilah','الطفيلة'),
(11,'AJL','Ajloun','عجلون'),
(12,'ZAR','Zarqa','الزرقاء')
ON CONFLICT DO NOTHING;

-- very simple rectangle polygons for demo use only
INSERT INTO gis.admin_boundary (governorate_id, governorate_code, governorate_name_en, boundary_geom) VALUES
(1,'AMM','Amman', ST_Multi(ST_GeomFromText('POLYGON((35.80 31.80,36.20 31.80,36.20 31.40,35.80 31.40,35.80 31.80))',4326))),
(2,'AQA','Aqaba', ST_Multi(ST_GeomFromText('POLYGON((35.00 29.80,35.30 29.80,35.30 29.30,35.00 29.30,35.00 29.80))',4326))),
(3,'BAL','Balqa', ST_Multi(ST_GeomFromText('POLYGON((35.40 32.00,35.80 32.00,35.80 31.60,35.40 31.60,35.40 32.00))',4326))),
(4,'IRB','Irbid', ST_Multi(ST_GeomFromText('POLYGON((35.70 32.20,36.20 32.20,36.20 31.95,35.70 31.95,35.70 32.20))',4326))),
(5,'JER','Jerash', ST_Multi(ST_GeomFromText('POLYGON((35.70 32.00,36.05 32.00,36.05 31.75,35.70 31.75,35.70 32.00))',4326))),
(6,'KAR','Karak', ST_Multi(ST_GeomFromText('POLYGON((35.40 31.40,35.95 31.40,35.95 30.95,35.40 30.95,35.40 31.40))',4326))),
(7,'MAA','Ma''an', ST_Multi(ST_GeomFromText('POLYGON((35.10 30.80,36.10 30.80,36.10 29.80,35.10 29.80,35.10 30.80))',4326))),
(8,'MAD','Madaba', ST_Multi(ST_GeomFromText('POLYGON((35.50 31.80,35.90 31.80,35.90 31.40,35.50 31.40,35.50 31.80))',4326))),
(9,'MAF','Mafraq', ST_Multi(ST_GeomFromText('POLYGON((36.00 32.30,37.50 32.30,37.50 31.70,36.00 31.70,36.00 32.30))',4326))),
(10,'TAF','Tafilah', ST_Multi(ST_GeomFromText('POLYGON((35.20 31.20,35.60 31.20,35.60 30.80,35.20 30.80,35.20 31.20))',4326))),
(11,'AJL','Ajloun', ST_Multi(ST_GeomFromText('POLYGON((35.60 32.10,35.90 32.10,35.90 31.90,35.60 31.90,35.60 32.10))',4326))),
(12,'ZAR','Zarqa', ST_Multi(ST_GeomFromText('POLYGON((36.00 32.00,36.60 32.00,36.60 31.50,36.00 31.50,36.00 32.00))',4326)))
ON CONFLICT DO NOTHING;

DO $$
DECLARE
    g RECORD;
    month_date DATE;
    m INTEGER := 0;
    month_factor NUMERIC;
    base_visitors NUMERIC;
    base_rooms NUMERIC;
    base_beds NUMERIC;
    occ NUMERIC;
BEGIN
    FOR g IN
        SELECT * FROM core.governorate ORDER BY governorate_id
    LOOP
        month_date := DATE '2024-01-01';
        FOR m IN 0..23 LOOP
            month_factor := CASE EXTRACT(MONTH FROM month_date)
                WHEN 1 THEN 0.80
                WHEN 2 THEN 0.85
                WHEN 3 THEN 0.95
                WHEN 4 THEN 1.05
                WHEN 5 THEN 1.10
                WHEN 6 THEN 1.20
                WHEN 7 THEN 1.28
                WHEN 8 THEN 1.25
                WHEN 9 THEN 1.05
                WHEN 10 THEN 1.00
                WHEN 11 THEN 0.92
                ELSE 0.88
            END;

            base_visitors := (30000 + g.governorate_id * 7000) * month_factor * (1 + (m * 0.01));
            IF g.governorate_code = 'AQA' THEN base_visitors := base_visitors * 1.25; END IF;
            IF g.governorate_code = 'MAA' THEN base_visitors := base_visitors * 1.35; END IF;
            IF g.governorate_code = 'AMM' THEN base_visitors := base_visitors * 1.50; END IF;

            base_rooms := 900 + g.governorate_id * 120;
            base_beds := base_rooms * 2.1;
            IF g.governorate_code = 'AQA' THEN base_rooms := base_rooms * 1.45; base_beds := base_beds * 1.45; END IF;
            IF g.governorate_code = 'AMM' THEN base_rooms := base_rooms * 1.60; base_beds := base_beds * 1.60; END IF;

            occ := LEAST(0.92, GREATEST(0.25, (base_visitors / (base_beds * 35.0))));

            INSERT INTO core.fact_visitors_monthly(governorate_id, month_index, total_visitors)
            VALUES (g.governorate_id, month_date, ROUND(base_visitors,2))
            ON CONFLICT DO NOTHING;

            INSERT INTO core.fact_rooms_beds_monthly(governorate_id, month_index, total_rooms, total_beds)
            VALUES (g.governorate_id, month_date, ROUND(base_rooms,2), ROUND(base_beds,2))
            ON CONFLICT DO NOTHING;

            INSERT INTO core.fact_hotel_occupancy_monthly(governorate_id, month_index, average_occupancy_rate)
            VALUES (g.governorate_id, month_date, ROUND(occ,4))
            ON CONFLICT DO NOTHING;

            month_date := (month_date + INTERVAL '1 month')::date;
        END LOOP;
    END LOOP;
END $$;


INSERT INTO admin.system_parameter(parameter_key, parameter_value, value_type, description) VALUES
('classification_tight_threshold','75','number','Occupancy pressure index threshold for tight capacity'),
('classification_balanced_threshold','45','number','Occupancy pressure index threshold for balanced capacity'),
('priority_weight_occupancy','0.35','number','Priority score weight: occupancy pressure'),
('priority_weight_growth','0.20','number','Priority score weight: growth pressure'),
('priority_weight_visitor_bed','0.25','number','Priority score weight: visitors per 1000 beds'),
('priority_weight_forecast','0.20','number','Priority score weight: forecast pressure'),
('high_priority_threshold','70','number','Threshold for high-priority zone reporting')
ON CONFLICT (parameter_key) DO NOTHING;

INSERT INTO core.tourism_site (site_name_en, site_category, governorate_id, latitude, longitude, site_geom) VALUES
('Petra Archaeological Park','cultural',7,30.3285,35.4444,ST_SetSRID(ST_MakePoint(35.4444,30.3285),4326)),
('Wadi Rum Protected Area','nature',7,29.5721,35.4200,ST_SetSRID(ST_MakePoint(35.4200,29.5721),4326)),
('Aqaba Waterfront','coastal',2,29.5319,35.0061,ST_SetSRID(ST_MakePoint(35.0061,29.5319),4326)),
('Dead Sea Resort Zone','resort',8,31.7185,35.5900,ST_SetSRID(ST_MakePoint(35.5900,31.7185),4326)),
('Jerash Archaeological Site','cultural',5,32.2808,35.8993,ST_SetSRID(ST_MakePoint(35.8993,32.2808),4326)),
('Amman Citadel','cultural',1,31.9545,35.9340,ST_SetSRID(ST_MakePoint(35.9340,31.9545),4326)),
('Karak Castle','cultural',6,31.1808,35.7022,ST_SetSRID(ST_MakePoint(35.7022,31.1808),4326))
ON CONFLICT DO NOTHING;
