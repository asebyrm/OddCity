"""
Database utility functions - Transaction management
"""
from contextlib import contextmanager
from ..database import get_db_connection


@contextmanager
def db_transaction():
    """
    Transaction context manager - Otomatik commit/rollback
    
    Kullanım:
        with db_transaction() as (conn, cursor):
            cursor.execute("INSERT INTO ...")
            # Başarılı olursa otomatik commit
            # Hata olursa otomatik rollback
    """
    conn = get_db_connection()
    if conn is None:
        raise ConnectionError("Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        conn.start_transaction()
        yield conn, cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()


@contextmanager
def get_cursor(dictionary=True):
    """
    Basit cursor context manager (transaction olmadan)
    
    Kullanım:
        with get_cursor() as cursor:
            cursor.execute("SELECT * FROM users")
            result = cursor.fetchall()
    """
    conn = get_db_connection()
    if conn is None:
        raise ConnectionError("Database connection failed")
    
    cursor = conn.cursor(dictionary=dictionary)
    
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

