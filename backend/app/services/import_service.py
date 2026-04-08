import csv
import io
import json
from datetime import datetime

from fastapi import HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session


class ImportService:
    REQUIRED = {
        'visitors_monthly': ['governorate_id', 'month_index', 'total_visitors'],
        'rooms_beds_monthly': ['governorate_id', 'month_index', 'total_rooms', 'total_beds'],
        'hotel_occupancy_monthly': ['governorate_id', 'month_index', 'average_occupancy_rate'],
        'admin_boundaries': ['governorate_id', 'governorate_code', 'governorate_name_en', 'wkt'],
    }

    def _create_job(self, db: Session, dataset_type: str, filename: str, username: str | None):
        return db.execute(text("""
            INSERT INTO admin.import_job(dataset_type, filename, status, created_by)
            VALUES (:dataset_type, :filename, 'running', :created_by)
            RETURNING import_job_id
        """), {'dataset_type': dataset_type, 'filename': filename, 'created_by': username}).scalar_one()

    def _log_error(self, db: Session, job_id: int, row_number: int, message: str, raw_row: dict):
        db.execute(text("""
            INSERT INTO admin.import_error(import_job_id, row_number, error_message, raw_row_json)
            VALUES (:job_id, :row_number, :message, CAST(:raw_row AS jsonb))
        """), {
            'job_id': job_id,
            'row_number': row_number,
            'message': message,
            'raw_row': json.dumps(raw_row, ensure_ascii=False),
        })

    def _validate_headers(self, dataset_type: str, fieldnames: list[str] | None):
        if dataset_type not in self.REQUIRED:
            raise HTTPException(status_code=400, detail=f'Unsupported dataset_type: {dataset_type}')
        missing = [c for c in self.REQUIRED[dataset_type] if not fieldnames or c not in fieldnames]
        if missing:
            raise HTTPException(status_code=400, detail=f'Missing columns: {", ".join(missing)}')

    def _parse_month(self, value: str):
        return datetime.strptime(value[:10], '%Y-%m-%d').date()

    def upload_csv(self, db: Session, dataset_type: str, upload: UploadFile, username: str | None = None):
        content = upload.file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))
        self._validate_headers(dataset_type, reader.fieldnames)
        job_id = self._create_job(db, dataset_type, upload.filename or 'upload.csv', username)

        processed = success = errors = 0
        summary = {'duplicates_in_file': 0, 'negative_values': 0, 'invalid_months': 0, 'null_like_values': 0}
        seen = set()
        try:
            delete_sql = {
                'visitors_monthly': 'DELETE FROM core.fact_visitors_monthly',
                'rooms_beds_monthly': 'DELETE FROM core.fact_rooms_beds_monthly',
                'hotel_occupancy_monthly': 'DELETE FROM core.fact_hotel_occupancy_monthly',
                'admin_boundaries': 'DELETE FROM gis.admin_boundary',
            }[dataset_type]
            db.execute(text(delete_sql))

            for idx, row in enumerate(reader, start=2):
                processed += 1
                try:
                    if any(str(v).strip() == '' for v in row.values()):
                        summary['null_like_values'] += 1
                    key = tuple(row.get(c) for c in self.REQUIRED[dataset_type][:2])
                    if key in seen:
                        summary['duplicates_in_file'] += 1
                    seen.add(key)

                    gid = int(row['governorate_id'])
                    if dataset_type == 'admin_boundaries':
                        db.execute(text("""
                            INSERT INTO gis.admin_boundary(governorate_id, governorate_code, governorate_name_en, boundary_geom)
                            VALUES (:gid, :code, :name, ST_Multi(ST_GeomFromText(:wkt, 4326)))
                            ON CONFLICT (governorate_id)
                            DO UPDATE SET governorate_code = EXCLUDED.governorate_code,
                                          governorate_name_en = EXCLUDED.governorate_name_en,
                                          boundary_geom = EXCLUDED.boundary_geom
                        """), {'gid': gid, 'code': row['governorate_code'], 'name': row['governorate_name_en'], 'wkt': row['wkt']})
                    else:
                        try:
                            month = self._parse_month(row['month_index'])
                        except Exception:
                            summary['invalid_months'] += 1
                            raise
                        if dataset_type == 'visitors_monthly':
                            total_visitors = float(row['total_visitors'])
                            if total_visitors < 0: summary['negative_values'] += 1
                            db.execute(text("""
                                INSERT INTO core.fact_visitors_monthly(governorate_id, month_index, total_visitors)
                                VALUES (:gid, :month, :val)
                                ON CONFLICT (governorate_id, month_index)
                                DO UPDATE SET total_visitors = EXCLUDED.total_visitors
                            """), {'gid': gid, 'month': month, 'val': total_visitors})
                        elif dataset_type == 'rooms_beds_monthly':
                            total_rooms = float(row['total_rooms']); total_beds = float(row['total_beds'])
                            if total_rooms < 0 or total_beds < 0: summary['negative_values'] += 1
                            db.execute(text("""
                                INSERT INTO core.fact_rooms_beds_monthly(governorate_id, month_index, total_rooms, total_beds)
                                VALUES (:gid, :month, :rooms, :beds)
                                ON CONFLICT (governorate_id, month_index)
                                DO UPDATE SET total_rooms = EXCLUDED.total_rooms, total_beds = EXCLUDED.total_beds
                            """), {'gid': gid, 'month': month, 'rooms': total_rooms, 'beds': total_beds})
                        elif dataset_type == 'hotel_occupancy_monthly':
                            rate = float(row['average_occupancy_rate'])
                            if rate < 0: summary['negative_values'] += 1
                            db.execute(text("""
                                INSERT INTO core.fact_hotel_occupancy_monthly(governorate_id, month_index, average_occupancy_rate)
                                VALUES (:gid, :month, :rate)
                                ON CONFLICT (governorate_id, month_index)
                                DO UPDATE SET average_occupancy_rate = EXCLUDED.average_occupancy_rate
                            """), {'gid': gid, 'month': month, 'rate': rate})
                    success += 1
                except Exception as e:
                    errors += 1
                    self._log_error(db, job_id, idx, str(e), row)

            status = 'completed' if errors == 0 else 'completed_with_errors'
            db.execute(text("""
                UPDATE admin.import_job
                SET status = :status, processed_rows = :processed, success_rows = :success, error_rows = :errors,
                    message = :message, validation_summary_json = CAST(:summary AS jsonb)
                WHERE import_job_id = :job_id
            """), {
                'status': status,
                'processed': processed,
                'success': success,
                'errors': errors,
                'message': f'Imported {success} row(s)',
                'summary': json.dumps(summary),
                'job_id': job_id,
            })
            db.commit()
            return {
                'import_job_id': job_id,
                'dataset_type': dataset_type,
                'status': status,
                'processed_rows': processed,
                'success_rows': success,
                'error_rows': errors,
                'validation_summary': summary,
            }
        except Exception:
            db.rollback()
            raise

    def list_jobs(self, db: Session):
        rows = db.execute(text("""
            SELECT import_job_id, dataset_type, filename, status, processed_rows, success_rows, error_rows,
                   message, validation_summary_json, created_by, created_at
            FROM admin.import_job
            ORDER BY import_job_id DESC
        """)).mappings().all()
        return [dict(r) for r in rows]

    def list_errors(self, db: Session, job_id: int):
        rows = db.execute(text("""
            SELECT import_error_id, row_number, error_message, raw_row_json, created_at
            FROM admin.import_error
            WHERE import_job_id = :job_id
            ORDER BY import_error_id
        """), {'job_id': job_id}).mappings().all()
        return [dict(r) for r in rows]
