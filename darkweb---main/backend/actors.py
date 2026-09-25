from .db import get_postgres_connection


def get_all_actors():
    """
    Fetch all actors from PostgreSQL.
    Returns a list of actor IDs.
    """

    connection = get_postgres_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT actor_id
                FROM actors
                ORDER BY actor_id;
                """
            )

            rows = cursor.fetchall()

        return [
            {
                "actor_id": row[0]
            }
            for row in rows
        ]

    finally:
        connection.close()