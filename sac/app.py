from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request

from sac.db import get_connection, init_db, utc_now

TERMS_PATH = Path(__file__).resolve().parent / "terms.txt"


def create_app() -> Flask:
    app = Flask(__name__)
    init_db()

    @app.get("/health")
    def health() -> Any:
        return {"status": "ok"}

    @app.get("/api/terms")
    def get_terms() -> Any:
        return {"terms": TERMS_PATH.read_text(encoding="utf-8")}

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
        return _update_user_status(user_id, "active")

    @app.post("/api/users/<int:user_id>/deny")
    def deny_user(user_id: int) -> Any:
        return _update_user_status(user_id, "denied")

    def _update_user_status(user_id: int, status: str) -> Any:
        with get_connection() as connection:
            cursor = connection.execute(
                "UPDATE users SET status = ? WHERE id = ?",
                (status, user_id),
            )
            connection.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "User not found"}), 404
        return jsonify({"status": status})

    @app.post("/api/certifications")
    def create_certification() -> Any:
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

        return jsonify({"status": "granted"})

    @app.post("/api/certifications/<int:cert_id>/revoke")
    def revoke_cert(cert_id: int) -> Any:
        payload = request.get_json(force=True)
        if "user_id" not in payload:
            return jsonify({"error": "Missing fields: ['user_id']"}), 400

        with get_connection() as connection:
            cursor = connection.execute(
                "DELETE FROM user_certifications WHERE user_id = ? AND certification_id = ?",
                (payload["user_id"], cert_id),
            )
            connection.commit()

        if cursor.rowcount == 0:
            return jsonify({"error": "Certification not found"}), 404
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

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000)
