from __future__ import annotations

import csv
import io
import os
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_file, session

from sac.db import get_connection, init_db, utc_now

TERMS_PATH = Path(__file__).resolve().parent / "terms.txt"


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SAC_SECRET_KEY", "change-me")
    init_db()

    def _get_admin_token() -> str:
        return os.environ.get("SAC_ADMIN_TOKEN", "change-me")

    def _require_admin() -> tuple[bool, Any]:
        if session.get("is_admin"):
            return True, None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()
            if token == _get_admin_token():
                return True, None
        return False, (jsonify({"error": "Unauthorized"}), 401)

    def _record_action(user_id: int | None, action: str, performed_by: str, metadata: str | None = None) -> None:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO staff_actions (user_id, action, performed_by, performed_at, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, action, performed_by, utc_now(), metadata),
            )
            connection.commit()

    @app.get("/")
    def kiosk() -> Any:
        return render_template("kiosk.html")

    @app.get("/admin")
    def admin() -> Any:
        return render_template("admin.html")

    @app.get("/health")
    def health() -> Any:
        return {"status": "ok"}

    @app.post("/api/admin/login")
    def admin_login() -> Any:
        payload = request.get_json(force=True)
        if payload.get("token") != _get_admin_token():
            return jsonify({"error": "Invalid token"}), 401
        session["is_admin"] = True
        session["admin_name"] = payload.get("admin_name", "admin")
        return jsonify({"status": "ok"})

    @app.post("/api/admin/logout")
    def admin_logout() -> Any:
        session.clear()
        return jsonify({"status": "logged_out"})

    @app.get("/api/terms")
    def get_terms() -> Any:
        return {"terms": TERMS_PATH.read_text(encoding="utf-8")}

    @app.put("/api/terms")
    def update_terms() -> Any:
        is_admin, error = _require_admin()
        if not is_admin:
            return error
        payload = request.get_json(force=True)
        if "terms" not in payload:
            return jsonify({"error": "Missing fields: ['terms']"}), 400
        TERMS_PATH.write_text(payload["terms"], encoding="utf-8")
        return jsonify({"status": "updated"})

    @app.post("/api/users")
    def create_user() -> Any:
        payload = request.get_json(force=True)
        required_fields = {"campus_id", "email", "first_name", "last_name", "terms_accepted"}
        missing = required_fields - payload.keys()
        if missing:
            return jsonify({"error": f"Missing fields: {sorted(missing)}"}), 400
        if not payload.get("terms_accepted"):
            return jsonify({"error": "Terms must be accepted"}), 400

        with get_connection() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO users (campus_id, email, first_name, last_name, status, role, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload["campus_id"],
                        payload["email"],
                        payload["first_name"],
                        payload["last_name"],
                        "pending",
                        payload.get("role", "student"),
                        utc_now(),
                    ),
                )
                connection.commit()
            except Exception as exc:  # sqlite3.IntegrityError
                return jsonify({"error": "User already exists", "details": str(exc)}), 409

        return jsonify({"status": "pending"}), 201

    @app.get("/api/users")
    def list_users() -> Any:
        is_admin, error = _require_admin()
        if not is_admin:
            return error
        status = request.args.get("status")
        query = "SELECT * FROM users"
        params: list[Any] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)

        with get_connection() as connection:
            rows = connection.execute(query, params).fetchall()
            return jsonify([dict(row) for row in rows])

    @app.post("/api/users/<int:user_id>/approve")
    def approve_user(user_id: int) -> Any:
        is_admin, error = _require_admin()
        if not is_admin:
            return error
        payload = request.get_json(silent=True) or {}
        performed_by = payload.get("performed_by") or session.get("admin_name", "admin")
        return _update_user_status(user_id, "active", performed_by)

    @app.post("/api/users/<int:user_id>/deny")
    def deny_user(user_id: int) -> Any:
        is_admin, error = _require_admin()
        if not is_admin:
            return error
        payload = request.get_json(silent=True) or {}
        performed_by = payload.get("performed_by") or session.get("admin_name", "admin")
        return _update_user_status(user_id, "denied", performed_by)

    def _update_user_status(user_id: int, status: str, performed_by: str) -> Any:
        with get_connection() as connection:
            cursor = connection.execute(
                "UPDATE users SET status = ? WHERE id = ?",
                (status, user_id),
            )
            connection.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "User not found"}), 404
        _record_action(user_id, f"user_{status}", performed_by)
        return jsonify({"status": status})

    @app.post("/api/certifications")
    def create_certification() -> Any:
        is_admin, error = _require_admin()
        if not is_admin:
            return error
        payload = request.get_json(force=True)
        required_fields = {"name", "scope"}
        missing = required_fields - payload.keys()
        if missing:
            return jsonify({"error": f"Missing fields: {sorted(missing)}"}), 400

        with get_connection() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO certifications (name, description, scope)
                    VALUES (?, ?, ?)
                    """,
                    (
                        payload["name"],
                        payload.get("description"),
                        payload["scope"],
                    ),
                )
                connection.commit()
            except Exception as exc:
                return jsonify({"error": "Certification already exists", "details": str(exc)}), 409

        return jsonify({"status": "created"}), 201

    @app.get("/api/certifications")
    def list_certifications() -> Any:
        with get_connection() as connection:
            rows = connection.execute("SELECT * FROM certifications").fetchall()
        return jsonify([dict(row) for row in rows])

    @app.post("/api/certifications/<int:cert_id>/grant")
    def grant_cert(cert_id: int) -> Any:
        is_admin, error = _require_admin()
        if not is_admin:
            return error
        payload = request.get_json(force=True)
        required_fields = {"user_id", "granted_by"}
        missing = required_fields - payload.keys()
        if missing:
            return jsonify({"error": f"Missing fields: {sorted(missing)}"}), 400

        with get_connection() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO user_certifications (user_id, certification_id, granted_by, granted_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (payload["user_id"], cert_id, payload["granted_by"], utc_now()),
                )
                connection.commit()
            except Exception as exc:
                return jsonify({"error": "Certification already granted", "details": str(exc)}), 409

        _record_action(
            payload["user_id"],
            "cert_granted",
            payload["granted_by"],
            metadata=str(cert_id),
        )
        return jsonify({"status": "granted"})

    @app.post("/api/certifications/<int:cert_id>/revoke")
    def revoke_cert(cert_id: int) -> Any:
        is_admin, error = _require_admin()
        if not is_admin:
            return error
        payload = request.get_json(force=True)
        if "user_id" not in payload:
            return jsonify({"error": "Missing fields: ['user_id']"}), 400
        performed_by = payload.get("performed_by") or session.get("admin_name", "admin")

        with get_connection() as connection:
            cursor = connection.execute(
                "DELETE FROM user_certifications WHERE user_id = ? AND certification_id = ?",
                (payload["user_id"], cert_id),
            )
            connection.commit()

        if cursor.rowcount == 0:
            return jsonify({"error": "Certification not found"}), 404
        _record_action(payload["user_id"], "cert_revoked", performed_by, metadata=str(cert_id))
        return jsonify({"status": "revoked"})

    @app.post("/api/swipe")
    def swipe() -> Any:
        payload = request.get_json(force=True)
        input_value = payload.get("input_value")
        certification_id = payload.get("certification_id")
        if not input_value:
            return jsonify({"error": "Missing fields: ['input_value']"}), 400

        with get_connection() as connection:
            user = connection.execute(
                "SELECT * FROM users WHERE campus_id = ? OR email = ?",
                (input_value, input_value),
            ).fetchone()

            result = "denied"
            user_id = None
            if user and user["status"] == "active":
                user_id = user["id"]
                if certification_id is None:
                    result = "approved"
                else:
                    cert = connection.execute(
                        """
                        SELECT 1 FROM user_certifications
                        WHERE user_id = ? AND certification_id = ?
                        """,
                        (user_id, certification_id),
                    ).fetchone()
                    result = "approved" if cert else "denied"

            connection.execute(
                """
                INSERT INTO swipe_events (user_id, input_value, certification_checked, timestamp, result)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, input_value, certification_id, utc_now(), result),
            )
            connection.commit()

        response = {"result": result}
        if user_id:
            response["user_id"] = user_id
        return jsonify(response)

    @app.get("/api/analytics/swipes")
    def analytics_swipes() -> Any:
        is_admin, error = _require_admin()
        if not is_admin:
            return error
        interval = request.args.get("interval", "day")
        if interval not in {"day", "week", "month"}:
            return jsonify({"error": "Invalid interval"}), 400

        sql = (
            "SELECT strftime('%Y-%m-%d', timestamp) as bucket, COUNT(*) as count "
            "FROM swipe_events GROUP BY bucket ORDER BY bucket DESC"
        )
        if interval == "week":
            sql = (
                "SELECT strftime('%Y-%W', timestamp) as bucket, COUNT(*) as count "
                "FROM swipe_events GROUP BY bucket ORDER BY bucket DESC"
            )
        if interval == "month":
            sql = (
                "SELECT strftime('%Y-%m', timestamp) as bucket, COUNT(*) as count "
                "FROM swipe_events GROUP BY bucket ORDER BY bucket DESC"
            )

        with get_connection() as connection:
            rows = connection.execute(sql).fetchall()
        return jsonify([dict(row) for row in rows])

    @app.get("/api/analytics/unique-users")
    def analytics_unique_users() -> Any:
        is_admin, error = _require_admin()
        if not is_admin:
            return error
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT strftime('%Y-%m-%d', timestamp) as bucket, COUNT(DISTINCT user_id) as count
                FROM swipe_events
                WHERE user_id IS NOT NULL
                GROUP BY bucket
                ORDER BY bucket DESC
                """
            ).fetchall()
        return jsonify([dict(row) for row in rows])

    @app.get("/api/analytics/cert-usage")
    def analytics_cert_usage() -> Any:
        is_admin, error = _require_admin()
        if not is_admin:
            return error
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT certifications.name, COUNT(swipe_events.id) as count
                FROM swipe_events
                JOIN certifications ON swipe_events.certification_checked = certifications.id
                GROUP BY certifications.name
                ORDER BY count DESC
                """
            ).fetchall()
        return jsonify([dict(row) for row in rows])

    @app.get("/api/analytics/heatmap")
    def analytics_heatmap() -> Any:
        is_admin, error = _require_admin()
        if not is_admin:
            return error
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT strftime('%w', timestamp) as day,
                       strftime('%H', timestamp) as hour,
                       COUNT(*) as count
                FROM swipe_events
                GROUP BY day, hour
                ORDER BY day, hour
                """
            ).fetchall()
        return jsonify([dict(row) for row in rows])

    @app.get("/api/analytics/export")
    def analytics_export() -> Any:
        is_admin, error = _require_admin()
        if not is_admin:
            return error
        export_type = request.args.get("type", "swipes")
        if export_type not in {"swipes", "users"}:
            return jsonify({"error": "Invalid export type"}), 400

        with get_connection() as connection:
            if export_type == "users":
                rows = connection.execute("SELECT * FROM users").fetchall()
                headers = rows[0].keys() if rows else []
            else:
                rows = connection.execute("SELECT * FROM swipe_events").fetchall()
                headers = rows[0].keys() if rows else []

        output = io.StringIO()
        writer = csv.writer(output)
        if headers:
            writer.writerow(headers)
            for row in rows:
                writer.writerow([row[key] for key in headers])

        buffer = io.BytesIO(output.getvalue().encode("utf-8"))
        filename = f"sac_{export_type}.csv"
        return send_file(
            buffer,
            mimetype="text/csv",
            as_attachment=True,
            download_name=filename,
        )

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000)
