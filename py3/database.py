# 2015-05-29 02:39 PM
# mysql, mysqlimport, mysqldump wrappers to execute *.sql files,
# mysql* must have valid ini or cfg file with credentials
#

from terminal import terminal
from conn import execute_sql
from global_ini import DB_DICT, DIRLIST
from make_csv import list_csv_filepaths_by_date
import os


################################################################
#             0. Generic functions used in other calls         #
################################################################


def replace_in_file(filepath, replace_what, replace_with):
    """
    Replaces 'replace_what' string with 'replace_with' string in filepath.
    """
    with open(filepath) as f:
        lines = f.read().replace(replace_what, replace_with)

    with open(filepath, 'w') as f1:
        f1.write(lines)


def run_sql_string(string, database=None, verbose=False):
    """
    Requires mysql to be in PATH - see ini.bat
    Allows running non-SQL commands in mysql.exe (e.g. source)
    For SQL commands may also use conn.execute_sql()
    """
    if database is None:
        call_string = "mysql -e \"{0}\"".format(string)
    else:
        call_string = "mysql --database {0} --execute \"{1}\"".format(
            database, string)

    if verbose:
        call_string = call_string + " -v"

    terminal(call_string)


def source_sql_file(sql_filename, db_name):
    path = os.path.normpath(sql_filename)
    command = "source {0}".format(path)
    run_sql_string(command, database=db_name)


def import_generic(database, path):
    if os.path.isfile(path):
        call_string = "mysqlimport {0} {1} --delete".format(database, path)
        terminal(call_string)
    else:
        print("File not found:",  path)


def dump_table_csv(db, table, dir_):
    """
    Saves database table in specified directory as csv file.
    """
    call_string = "mysqldump --fields-terminated-by=\\t\ --lines-terminated-by=\\r\\n --tab=\"{0}\" {1} {2}".format(
        dir_, db, table)
    terminal(call_string)
    # Note: below is a fix to kill unnecessary slashes in txt file.
    replace_in_file(os.path.join(dir_, table + ".txt"), "\\", "")


################################################################
#            1. General database operations                    #
################################################################


def recreate_db(db_name):
    """
    Deletes an existing database and recreates it (empty).
    """
    print("Database:", db_name)
    # sql-only, can use pymysql connection for this
    command = "DROP DATABASE IF EXISTS {0}; CREATE DATABASE  {0};".format(
        db_name)
    execute_sql(command)
    print(
        "Deleted existing database and created empty database under same name.")


def get_db_dumpfile_path(db_name):
    """
    Returns the standard path to dump files, configured in DIRLIST in the
    global initialization module.
    """
    dir_ = DIRLIST['global']['database']
    sql_filename = db_name + ".sql"
    path = os.path.join(dir_, sql_filename)
    return path


def load_db_from_dump(db_name):
    """
    Loads a database structure from a dump file.
    See get_db_dumpfile_path to check the standard location.
    """
    print("Database:", db_name)
    path = get_db_dumpfile_path(db_name)
    source_sql_file(path, db_name)
    print("Loaded database structure from file <{0}.sql>. No data was imported.".format(
        db_name))


def save_db_to_dump(db_name):
    """
    Saves the structure of a database to a dump file in the standard location.
    See get_db_dumpfile_path to check the standard location.
    """
    print("Database:", db_name)
    # uses mysqldump and terminal()
    path = get_db_dumpfile_path(db_name)
    #               mysqldump %1  --no-data --routines > %1.sql
    line_command = "mysqldump {0} --no-data --routines > {0}".format(path)
    terminal(line_command)
    print("Dumped database structure to file <{0}.sql>. No data saved to this file.".format(
        db_name))


################################################################
#                  2. DBF file import                          #
################################################################

def import_csv(isodate, form):
    db_name = DB_DICT['raw']

    for csv_path in list_csv_filepaths_by_date(isodate, form):
        if os.path.isfile(csv_path):
            command_line = "mysqlimport --ignore_lines=1 --ignore {0} \"{1}\"".format(
                db_name, csv_path)
            terminal(command_line)
        else:
            print("File not found:",  csv_path)

    print("Finished importing CSV files into raw data database.")
    print("Form:", form, ". Date:", isodate)

################################################################
#              3. Dataset manipulation                         #
################################################################


def dump_table_sql(db, table, file, form):
    """
    Dumps table from database to local directory as a SQL file.
    Support function, it is not called directly from the interface.
    EP (not todo): later will need to write this file to publically open folder on a server
    """
    path = os.path.join(DIRLIST[form]['sql'], file)
    # mysqldump dbf_db f101 --add-drop-table=FALSE --no-create-info
    # --insert-ignore > %SQL_DIR%\f101.sql
    string = "mysqldump {0} {1}     --add-drop-table=FALSE --no-create-info --insert-ignore > \"{2}\"".format(
        db, table, path)
    terminal(string)


def read_table_sql(db, form, file):
    """
    Support function, it is not called directly from the interface.
    """
    path = os.path.join(DIRLIST[form]['sql'], file)
    source_sql_file(path, db)


def get_sqldump_table_and_filename(form):
    """
    Returns (f101, f101.sql) for form 101, and similar output for other forms.
    Support function, it is not called directly from the interface.
    """
    table = 'f' + form
    file = table + ".sql"
    return table, file


def save_dataset_as_sql(form):
    """
    Used in the 'save dataset' and 'migrate dataset' operation modes.
    """
    database = DB_DICT['raw']
    table, file = get_sqldump_table_and_filename(form)
    dump_table_sql(database, table, file, form)
    # mysqldump dbf_db f101 --add-drop-table=FALSE --no-create-info
    # --insert-ignore > %SQL_DIR%\f101.sql


def import_dataset_from_sql(form):
    """
    Used in the 'import dataset' and 'migrate dataset' operation modes.
    """
    database = DB_DICT['final']
    table, file = get_sqldump_table_and_filename(form)
    read_table_sql(database, form, file)
    # mysql --database cbr_db2 -e "source %SQL_DIR%\f101.sql"


def create_final_dataset_in_raw_database():
    """
    Used in the 'make dataset' operation mode.
    """
    db_name = DB_DICT['raw']
    run_sql_string("call insert_f101();", db_name)


################################################################
#             4. Working with the final dataset               #
################################################################


def report_balance_tables():
    """
    Used in the 'report balance' operation mode.
    """
    # prepare TABLES in database
    db_name = DB_DICT['final']
    execute_sql("call balance_report_line_dt_3tables", db_name)

    # dump TABLES to CSV
    dir_ = DIRLIST['101']['output']
    TABLES = ("tmp_output_itogo", "tmp_output_ir", "tmp_output_iv")
    for table in TABLES:
        dump_table_csv(db_name, table, dir_)


def make_balance():
    """
    Used in the 'make balance' operation mode.
    """
    db_name = DB_DICT['final']
    execute_sql("call alloc_make", db_name)
    execute_sql("delete from balance", db_name)
    execute_sql("call balance_make", db_name)
    # use cbr_db2;
    # call alloc_make;
    # delete from balance;
    # call balance_make;


def test_balance():
    """
    Used in the 'test balance' operation mode.
    """
    def do_output(sql):
        print('-> ' + sql)
        out = execute_sql(sql, DB_DICT['final'], verbose=False)
        # I see no valuable info with verbose=True, as I'm printing the results
        # here

        if out:
            for row, val in enumerate(out, 1):
                print("row {0}: {1}".format(row, val))
        else:
            print('No output')

        print()

    do_output('select "Test: balance residuals" as Test')
    do_output('select * from test_balance_residual')
    do_output('select "Test: ref items" as Test')
    do_output('select * from test_ref_items')
    do_output('select "Test: net assets not zero" as Test')
    do_output(
        'select dt, regn, itogo from balance where line = 500 and itogo != 0 order by dt')


def import_alloc(filename='alloc_raw.txt'):
    """
    Used in the 'import alloc' operation mode.
    """
    database = DB_DICT['final']
    path = os.path.join(DIRLIST['global']['alloc'], filename)
    import_generic(database, path)


def import_tables():
    """
    Used in the 'import tables' operation mode.
    """
    database = DB_DICT['final']
    dir_ = os.path.join(DIRLIST['global']['tables'])

    for file in os.listdir(dir_):
        path = os.path.join(dir_, file)
        if file.endswith(".txt"):
            import_generic(database, path)
        if file.endswith(".sql"):
            source_sql_file(path, database)
            # Risk: import_generic and source_sql_file - similar functions
            # different arg order