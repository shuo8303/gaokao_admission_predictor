"""MySQL-backed usage logging for visits and prediction submissions.

The logger is intentionally fail-safe: database errors must never interrupt
normal prediction. If MySQL is not configured or temporarily unavailable, the
site simply skips logging for that request.
"""

import os
from contextlib import closing

from flask import request


_TABLES_READY = False


def log_visit(path=None):
    """Record one page visit in the visit_logs table."""
    _run_safely(
        """
        INSERT INTO visit_logs (path, ip, user_agent)
        VALUES (%s, %s, %s)
        """,
        (
            path or request.path,
            _get_client_ip(),
            request.headers.get("User-Agent", "")[:512],
        ),
    )


def log_prediction(feature, score, rank, has_result, result_school=None, result_major=None):
    """Record one quick or precise prediction submission."""
    _run_safely(
        """
        INSERT INTO prediction_logs
            (feature, score, `rank`, has_result, result_school, result_major, ip)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            feature,
            score,
            rank,
            bool(has_result),
            result_school,
            result_major,
            _get_client_ip(),
        ),
    )


def get_usage_statistics(limit=20):
    """Return dashboard statistics for the admin usage page.

    The function returns an empty-state dictionary when MySQL is not configured
    or temporarily unavailable, so the admin page can render a friendly message
    instead of crashing.
    """
    try:
        connection = _connect()
        if connection is None:
            return _empty_statistics(configured=False)

        with closing(connection):
            _ensure_tables(connection)

            return {
                "configured": True,
                "total_visits": _fetch_scalar(
                    connection,
                    "SELECT COUNT(*) FROM visit_logs",
                ),
                "total_predictions": _fetch_scalar(
                    connection,
                    "SELECT COUNT(*) FROM prediction_logs",
                ),
                "quick_predictions": _fetch_scalar(
                    connection,
                    "SELECT COUNT(*) FROM prediction_logs WHERE feature = %s",
                    ("quick",),
                ),
                "precise_predictions": _fetch_scalar(
                    connection,
                    "SELECT COUNT(*) FROM prediction_logs WHERE feature = %s",
                    ("precise",),
                ),
                "successful_predictions": _fetch_scalar(
                    connection,
                    "SELECT COUNT(*) FROM prediction_logs WHERE has_result = 1",
                ),
                "failed_predictions": _fetch_scalar(
                    connection,
                    "SELECT COUNT(*) FROM prediction_logs WHERE has_result = 0",
                ),
                "recent_visits": _fetch_all(
                    connection,
                    """
                    SELECT path, ip, user_agent, created_at
                    FROM visit_logs
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (limit,),
                ),
                "recent_predictions": _fetch_all(
                    connection,
                    """
                    SELECT feature, score, `rank`, has_result, result_school,
                           result_major, ip, created_at
                    FROM prediction_logs
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (limit,),
                ),
                "recent_quick_predictions": _fetch_all(
                    connection,
                    """
                    SELECT feature, score, `rank`, has_result, result_school,
                           result_major, ip, created_at
                    FROM prediction_logs
                    WHERE feature = %s
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    ("quick", limit),
                ),
                "recent_precise_predictions": _fetch_all(
                    connection,
                    """
                    SELECT feature, score, `rank`, has_result, result_school,
                           result_major, ip, created_at
                    FROM prediction_logs
                    WHERE feature = %s
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    ("precise", limit),
                ),
            }
    except Exception:
        return _empty_statistics(configured=True)


def _run_safely(sql, params=None):
    """Run one SQL statement while shielding the application from DB errors."""
    try:
        connection = _connect()
        if connection is None:
            return

        with closing(connection):
            _ensure_tables(connection)
            with connection.cursor() as cursor:
                cursor.execute(sql, params or ())
            connection.commit()
    except Exception:
        # Statistics are best-effort only. The user-facing prediction flow must
        # continue even if MySQL is down, credentials are wrong, or tables fail.
        return


def _connect():
    """Create a PyMySQL connection from environment variables."""
    try:
        import pymysql
    except ImportError:
        return None

    required_env = (
        "MYSQL_HOST",
        "MYSQL_USER",
        "MYSQL_PASSWORD",
        "MYSQL_DATABASE",
    )
    if any(not os.getenv(name) for name in required_env):
        return None

    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
        charset="utf8mb4",
        autocommit=False,
    )


def _fetch_scalar(connection, sql, params=None):
    """Return the first column of the first row for a query."""
    with connection.cursor() as cursor:
        cursor.execute(sql, params or ())
        row = cursor.fetchone()

    if not row:
        return 0

    return row[0]


def _fetch_all(connection, sql, params=None):
    """Return all rows for a SELECT query as dictionaries."""
    import pymysql

    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute(sql, params or ())
        return cursor.fetchall()


def _empty_statistics(configured):
    """Build a predictable empty statistics object for template rendering."""
    return {
        "configured": configured,
        "total_visits": 0,
        "total_predictions": 0,
        "quick_predictions": 0,
        "precise_predictions": 0,
        "successful_predictions": 0,
        "failed_predictions": 0,
        "recent_visits": [],
        "recent_predictions": [],
        "recent_quick_predictions": [],
        "recent_precise_predictions": [],
    }


def _ensure_tables(connection):
    """Create log tables once per process if they do not already exist."""
    global _TABLES_READY

    if _TABLES_READY:
        return

    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS visit_logs (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                path VARCHAR(255) NOT NULL,
                ip VARCHAR(45),
                user_agent VARCHAR(512),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_visit_created_at (created_at),
                INDEX idx_visit_path (path)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS prediction_logs (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                feature VARCHAR(32) NOT NULL,
                score INT,
                `rank` INT,
                has_result BOOLEAN NOT NULL DEFAULT FALSE,
                result_school VARCHAR(255),
                result_major VARCHAR(255),
                ip VARCHAR(45),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_prediction_created_at (created_at),
                INDEX idx_prediction_feature (feature),
                INDEX idx_prediction_result_school (result_school)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

    connection.commit()
    _TABLES_READY = True


def _get_client_ip():
    """Return the real client IP when behind a proxy, otherwise remote_addr."""
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()[:45]

    return (request.remote_addr or "")[:45]
