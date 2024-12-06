"""Module will hold the entries repository, as well as the table initialization function"""

import sqlite3
import logger
import datetime
from contextlib import contextmanager

import model
from config import ENTRIES_TABLE


def init_entries_table(conn: sqlite3.Connection, logger_: logger.logging.Logger) -> None:
    """This initializes the entries table"""
    entries_query = f'''
    CREATE TABLE IF NOT EXISTS {ENTRIES_TABLE} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE UNIQUE,
    entry TEXT
    )'''

    index_query = '''CREATE UNIQUE INDEX IF NOT EXISTS idx_entries_date ON entries(date)'''

    # create the table, logging any basic error
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(entries_query)
        cursor.execute(index_query)
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        logger_.exception('SQLite error:')
    except Exception:
        conn.rollback()
        logger_.exception('SQLite error:')
        raise
    finally:
        if cursor is not None:
            cursor.close()


class Entries:
    """This is the entries repository, responsible for interactions with the database"""
    def __init__(self, db_conn):
        self.conn = db_conn

        #get the logger
        self.logger = logger.journal_logger()
        
        #initialize the tables
        init_entries_table(self.conn, self.logger)

    @contextmanager
    def cursor_manager(self):
        #basic context manager for connections with the database
        cursor = self.conn.cursor()
        try:
            yield cursor
            self.conn.commit()
        except sqlite3.IntegrityError:
            self.conn.rollback()
            self.logger.exception('SQLite error:')
        except Exception:
            self.conn.rollback()
            self.logger.exception('Error at:')
            raise
        finally:
            cursor.close()

    def format_date(self, *dates: datetime.date) -> list[str]:
        #made this a function so any format changes can be done in one place
        return [date.isoformat() for date in dates]

    def save(self, day: model.Day) -> None:
        """ Method performs upsert (update or insert) of given day into the entries table """
        query = '''
            INSERT INTO entries (date, entry) VALUES (?, ?)
            ON CONFLICT(date)
            DO UPDATE SET entry = EXCLUDED.entry
         '''
        formatted_date = self.format_date(day.date)[0]
        with self.cursor_manager() as cursor:
            cursor.execute(query, (formatted_date, day.entry))
            self.logger.info(f'Entry saved for date {formatted_date}')

    def get_by_dates(self, start_date: datetime.date, end_date: datetime.date) -> list[tuple[str, str]]:
        query = f'''
            SELECT date, entry
            FROM {ENTRIES_TABLE}
            WHERE date BETWEEN ? and ?
            '''
        f_start_date, f_end_date = self.format_date(start_date, end_date)
       
        with self.cursor_manager() as cursor:
            cursor.execute(query, (f_start_date, f_end_date))
            entries = cursor.fetchall()
            self.logger.info(f'Entries retrieve for month of {start_date.month}')
            return entries

    def delete(self, day: model.Day) -> None:
        query = f'''
            DELETE FROM {ENTRIES_TABLE}
            WHERE = ?
            '''
        formatted_date = self.format_date(day.date)[0]

        with self.cursor_manager() as cursor:
            cursor.execute(query, (formatted_date, ))
            self.logger.info(f'Entry deleted for date: {formatted_date}')
        
