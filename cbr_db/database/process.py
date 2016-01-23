"""
This module contains interface functions to mysql processes,
such as mysqldump, mysqlimport, etc.
"""

import os
import re
import tempfile

from cbr_db.database.connection import get_credentials
from cbr_db.filesystem import get_db_dumpfile_path
from cbr_db.terminal import terminal
from cbr_db.utils.text import replace_in_file


def mysqlimport_generic(database, path):
    credentials = get_credentials()
    call_string = "mysqlimport -u{0} -p{1} {2} {3} --delete".format(
        credentials['user'], credentials['passwd'],
        database, path)
    terminal(call_string)


def mysqlimport(db_name, csv_path, ignore_lines = 1, add_mode = "ignore"):
    credentials = get_credentials()
    # Trying to use mysqlimport without --lines-terminated-by="\r\n" (this works on Debian linux on remote server)
    command_line = r'mysqlimport -u{0} -p{1} --ignore_lines={2} --{3} {4} "{5}" '.format(
                    credentials['user'], credentials['passwd'],
                    ignore_lines, add_mode, db_name, csv_path)
    terminal(command_line)


def run_sql_string(string, database=None, verbose=False):
    """
    Runs <string> as command for mysql.exe
    Notes:
       Requires mysql to be in PATH - see ini.bat/ini.py. Also requires host/port/user/password credentials MySQL configureation files.
       Allows running non-SQL commands in mysql.exe (e.g. source)
       For SQL commands may also use conn.execute_sql()
    """
    credentials = get_credentials()
    if database is None:
        call_string = "mysql -u{0} -p{1} -e \"{2}\"".format(
            credentials['user'], credentials['passwd'],
            string)
    else:
        call_string = "mysql -u{0} -p{1} --database {2} --execute \"{3}\"".format(
            credentials['user'], credentials['passwd'],
            database, string)

    # todo: -v not showing to screen, check if it so, change
    if verbose:
        call_string = call_string + " -v"

    terminal(call_string)


def source_sql_file(sql_filename, db_name):
    path = sql_filename.replace('\\', '/')
    command = r"source {0}".format(path)
    run_sql_string(command, database=db_name)


def dump_table_csv(db, table, directory):
    """
    Saves database table in specified directory as csv file.
    """
    credentials = get_credentials()
    call_string = r'mysqldump -u{0} -p{1} --fields-terminated-by="\t" --lines-terminated-by="\r\n" --tab="{2}" {3} {4}'.format(
        credentials['user'], credentials['passwd'],
        directory, db, table)
    terminal(call_string)
    # Note: below is a fix to kill unnecessary slashes in txt file.
    replace_in_file(os.path.join(directory, table + ".txt"), "\\", "")
    # more cleanup, delete extra sql files:
    extra_sql = os.path.join(directory, table + ".sql")
    os.remove(extra_sql)


def dump_table_sql(db, table, path):
    """
    Dumps table from database to local directory as a SQL file.
    """
    credentials = get_credentials()
    string = r'mysqldump -u{0} -p{1} {2} {3} --add-drop-table=FALSE --no-create-info --insert-ignore > "{4}"'.format(
        credentials['user'], credentials['passwd'],
        db, table, path)
    terminal(string)


def patch_sql_file(path):
    """
    Applies necessary patches to SQL file (such as username/password).
    Returns path to patched file (in a temp folder).
    """
    with open(path, encoding='utf-8') as file:
        text = file.read()
    credentials = get_credentials()
    text = re.sub(r"([`'])\w+[`']@[`']\w+[`']",
                  r"\1{}\1@\1%\1".format(credentials['user']),
                  text)
    tempdir = os.path.join(tempfile.gettempdir(), 'cbr-db')
    if not os.path.isdir(tempdir):
        os.makedirs(tempdir)
    temp_file_path = os.path.join(tempdir, os.path.split(path)[1])
    with open(temp_file_path, 'w', encoding='utf-8') as file:
        file.write(text)
    return temp_file_path


def mysqldump(db_name):
    credentials = get_credentials()
    print("Database:", db_name)
    path = get_db_dumpfile_path(db_name)
    #               mysqldump %1  --no-data --routines > %1.sql
    line_command = "mysqldump -u{0} -p{1} {2} --no-data --routines > {3}".format(
        credentials['user'], credentials['passwd'],
        db_name, path)
    terminal(line_command)
    print("Dumped database structure to file <{0}.sql>. No data saved to this file.".format(
        db_name))