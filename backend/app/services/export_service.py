import csv
import io
from datetime import datetime

from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session


class ExportService:
    def overview_csv(self, db: Session):
        rows = db.execute(text("""
            SELECT governorate_name_en, latest_total_visitors, latest_total_beds,
                   latest_average_occupancy_rate, priority_score, capacity_classification,
                   next_forecast_value, justification_text
            FROM (
                WITH latest AS (SELECT MAX(month_index) AS month_index FROM core.fact_visitors_monthly),
                latest_fc AS (
                    SELECT DISTINCT ON (f.governorate_id) f.governorate_id, f.forecast_value
                    FROM forecast.region_demand_forecast f
                    JOIN forecast.model_run mr ON mr.model_run_id = f.model_run_id
                    ORDER BY f.governorate_id, mr.model_run_id DESC, f.forecast_month
                )
                SELECT
                    g.governorate_name_en,
                    v.total_visitors AS latest_total_visitors,
                    rb.total_beds AS latest_total_beds,
                    o.average_occupancy_rate AS latest_average_occupancy_rate,
                    p.priority_score,
                    c.capacity_classification,
                    fc.forecast_value AS next_forecast_value,
                    p.justification_text
                FROM core.governorate g
                LEFT JOIN latest l ON TRUE
                LEFT JOIN core.fact_visitors_monthly v ON v.governorate_id = g.governorate_id AND v.month_index = l.month_index
                LEFT JOIN core.fact_rooms_beds_monthly rb ON rb.governorate_id = g.governorate_id AND rb.month_index = l.month_index
                LEFT JOIN core.fact_hotel_occupancy_monthly o ON o.governorate_id = g.governorate_id AND o.month_index = l.month_index
                LEFT JOIN analytics.region_priority_score_monthly p ON p.governorate_id = g.governorate_id AND p.month_index = l.month_index
                LEFT JOIN analytics.region_classification_monthly c ON c.governorate_id = g.governorate_id AND c.month_index = l.month_index
                LEFT JOIN latest_fc fc ON fc.governorate_id = g.governorate_id
                ORDER BY g.governorate_id
            ) q
        """)).mappings().all()
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(['Governorate', 'Visitors', 'Beds', 'Occupancy Rate', 'Priority Score', 'Capacity Classification', 'Next Forecast', 'Justification'])
        for r in rows:
            writer.writerow([r['governorate_name_en'], r['latest_total_visitors'], r['latest_total_beds'], r['latest_average_occupancy_rate'], r['priority_score'], r['capacity_classification'], r['next_forecast_value'], r['justification_text']])
        data = stream.getvalue().encode('utf-8')
        return StreamingResponse(io.BytesIO(data), media_type='text/csv', headers={'Content-Disposition': 'attachment; filename=overview_export.csv'})

    def region_csv(self, db: Session, governorate_id: int):
        rows = db.execute(text("""
            SELECT v.month_index, v.total_visitors, rb.total_rooms, rb.total_beds, o.average_occupancy_rate, p.priority_score
            FROM core.fact_visitors_monthly v
            LEFT JOIN core.fact_rooms_beds_monthly rb ON rb.governorate_id = v.governorate_id AND rb.month_index = v.month_index
            LEFT JOIN core.fact_hotel_occupancy_monthly o ON o.governorate_id = v.governorate_id AND o.month_index = v.month_index
            LEFT JOIN analytics.region_priority_score_monthly p ON p.governorate_id = v.governorate_id AND p.month_index = v.month_index
            WHERE v.governorate_id = :gid
            ORDER BY v.month_index
        """), {'gid': governorate_id}).mappings().all()
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(['Month', 'Visitors', 'Rooms', 'Beds', 'Occupancy Rate', 'Priority Score'])
        for r in rows:
            writer.writerow([r['month_index'], r['total_visitors'], r['total_rooms'], r['total_beds'], r['average_occupancy_rate'], r['priority_score']])
        data = stream.getvalue().encode('utf-8')
        return StreamingResponse(io.BytesIO(data), media_type='text/csv', headers={'Content-Disposition': f'attachment; filename=governorate_{governorate_id}_timeseries.csv'})

    def executive_summary_html(self, db: Session):
        kpis = db.execute(text("""
            WITH latest AS (SELECT MAX(month_index) AS month_index FROM core.fact_visitors_monthly)
            SELECT
                (SELECT month_index::text FROM latest) AS latest_month,
                (SELECT SUM(total_visitors) FROM core.fact_visitors_monthly v JOIN latest l ON v.month_index = l.month_index) AS total_visitors,
                (SELECT SUM(total_beds) FROM core.fact_rooms_beds_monthly r JOIN latest l ON r.month_index = l.month_index) AS total_beds,
                (SELECT AVG(average_occupancy_rate) FROM core.fact_hotel_occupancy_monthly o JOIN latest l ON o.month_index = l.month_index) AS avg_occupancy
        """)).mappings().one()
        top = db.execute(text("""
            WITH latest AS (SELECT MAX(month_index) AS month_index FROM analytics.region_priority_score_monthly)
            SELECT g.governorate_name_en, p.priority_score, c.capacity_classification, p.justification_text,
                   p.occupancy_component, p.growth_component, p.visitor_bed_component, p.forecast_component
            FROM analytics.region_priority_score_monthly p
            JOIN latest l ON p.month_index = l.month_index
            JOIN core.governorate g ON g.governorate_id = p.governorate_id
            LEFT JOIN analytics.region_classification_monthly c ON c.governorate_id = p.governorate_id AND c.month_index = p.month_index
            ORDER BY p.priority_score DESC NULLS LAST
            LIMIT 5
        """)).mappings().all()
        rows_html = ''.join(
            f"<tr><td>{r['governorate_name_en']}</td><td>{r['priority_score']}</td><td>{r['capacity_classification'] or '-'}</td><td>{r['justification_text'] or '-'}</td><td>Occ {r['occupancy_component'] or 0} · Growth {r['growth_component'] or 0} · Beds {r['visitor_bed_component'] or 0} · Forecast {r['forecast_component'] or 0}</td></tr>"
            for r in top
        )
        html = f"""
        <html><head><meta charset='utf-8'><title>Executive Summary</title>
        <style>
        body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2937; }}
        .kpi {{ display: inline-block; width: 22%; margin-right: 2%; background: #f8fafc; padding: 14px; border-radius: 10px; vertical-align: top; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 24px; }}
        th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; }}
        h1, h2 {{ margin-bottom: 12px; }}
        .meta {{ color: #64748b; margin-bottom: 24px; }}
        .note {{ background:#f8fafc; border:1px solid #d1d5db; border-radius:10px; padding:12px; margin-top:16px; }}
        </style></head><body>
        <h1>MoTA AI-GIS PoC Executive Summary</h1>
        <div class='meta'>Generated at {datetime.utcnow().isoformat()}Z</div>
        <div class='kpi'><strong>Latest Month</strong><br>{kpis['latest_month']}</div>
        <div class='kpi'><strong>Total Visitors</strong><br>{int(kpis['total_visitors'] or 0):,}</div>
        <div class='kpi'><strong>Total Beds</strong><br>{int(kpis['total_beds'] or 0):,}</div>
        <div class='kpi'><strong>Avg Occupancy</strong><br>{(float(kpis['avg_occupancy'] or 0)*100):.1f}%</div>
        <div class='note'>This Phase 2 export now includes indicator explanations and score components so users can see why a governorate is ranked highly.</div>
        <h2>Top Priority Governorates</h2>
        <table><thead><tr><th>Governorate</th><th>Priority Score</th><th>Capacity Status</th><th>Justification</th><th>Score Breakdown</th></tr></thead><tbody>{rows_html}</tbody></table>
        </body></html>
        """
        return HTMLResponse(content=html)
