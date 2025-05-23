# /usr/bin/env python3
"""
This tool is suitable for either production or test environments.

It can be considered as a tool to reproduce a bug or a tool for recovery the system to the point that is saved on
sqlite database (history.sqlite.3)

Sample usage:
python3 scripts/apply_history_db.py \
    --db-file scripts/history.sqlite.3.test \
    --base-url http://192.168.1.100 \
    --excluded-urls \
        /api/v1/sample-api/
"""
import argparse
import dataclasses
import json
import os
import shutil
import sqlite3
import subprocess  # nosec
import sys
from pathlib import Path
from typing import Any, Final, List, Optional, TextIO, Tuple


import requests
from prettytable import HRuleStyle, PrettyTable, PrettyTable

HISTORY_CONFIG_TABLE_NAME: Final[str] = 'request_logger_djangorequestshistorymodel'
MAX_COLUMN_WIDTH: Final[int] = 50
MAX_CELL_LENGTH: Final[int] = 1500
DEFAULT_EXCLUDED_URLS: Final[List[str]] = []
DEFAULT_INTERACTIVE_ASK_YES_NO_ANSWER: Final[str] = "no"
PROGRESS_BAR_DESCRIPTION: Final[str] = 'Replaying HTTP Requests'


@dataclasses.dataclass
class ColumnNames:
    id: str = "id"
    label: str = "label"
    request_method: str = "request_method"
    request_path: str = "request_path"
    request_data: str = "request_data_binary"
    response_code: str = "response_code"
    # response_data: str = "response_data"

    @property
    def table_displaying_names(self) -> tuple:
        return tuple(dataclasses.asdict(self).values())

    @property
    def columns(self) -> list:
        return list(dataclasses.asdict(self).values())


class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'


class PyLess:
    """ It's an implementation for less in python"""

    def __init__(self, content):
        self.content = content.splitlines() if isinstance(content, str) else content
        self.rows, self.columns = self.get_terminal_size()
        self.page_size = self.rows - 1  # leaving space for prompt

    @staticmethod
    def get_terminal_size():
        try:
            rows, columns = os.popen('stty size', 'r').read().split()  # nosec
            return int(rows), int(columns)
        except ValueError:
            # Fallback to shutil.get_terminal_size if stty fails
            size = shutil.get_terminal_size((80, 20))  # default size
            return size.lines, size.columns

    def getch(self):
        """Get a single character from standard input."""
        import termios
        import tty
        file_no = sys.stdin.fileno()
        old_settings = termios.tcgetattr(file_no)
        try:
            tty.setraw(file_no)
            char = sys.stdin.read(1)
        finally:
            termios.tcsetattr(file_no, termios.TCSADRAIN, old_settings)
        return char

    def display(self):
        current_line = 0
        total_lines = len(self.content)

        while current_line < total_lines:
            os.system('clear')  # nosec
            end_line = min(current_line + self.page_size, total_lines)
            print('\n'.join(self.content[current_line:end_line]), end='')

            if current_line < total_lines - 1:
                # Show the blinking cursor
                sys.stdout.write("\n:")
                sys.stdout.write("\033[?25h")  # Show cursor
                sys.stdout.flush()

            response = self.getch()

            # Hide cursor after key press
            sys.stdout.write("\033[?25l")  # Hide cursor

            if response.lower() == 'q':
                break
            if response == ' ' and current_line < total_lines - 1:
                current_line = end_line  # Go to the next page
            elif response == '\r':
                current_line += 1  # Go to the next line
                if current_line >= total_lines:
                    break  # Exit if the end of the content is reached

            # Overwrite ":" with spaces
            print("\r" + " " * len(":"), end='')
            # Move the cursor up to the start of the cleared line
            print("\033[A\r", end='')


def truncate_text(text, max_length):
    if len(str(text)) > max_length:
        return text[:max_length - 3] + "..."
    return text


def print_colored(text: str, color=Colors.RESET, **kwargs):
    """ Function to print colored text """
    print(color + text + Colors.RESET, **kwargs)


def print_error(text: str):
    """ Function to print error messages """
    # To have ordered printed texts we don't use stderr when mode is interactive
    file: TextIO
    if configuration.interactive:
        file = sys.stdout
    else:
        file = sys.stderr
    print(Colors.RED + text + Colors.RESET, file=file)


def exit_with_message(message: str, code: int = 1) -> None:
    if code == 0:
        print_colored(message)
        sys.exit(code)
    print_error(message)
    sys.exit(code)


def run_command(
        command,
        mimic_set_dash_x: bool = True,
        mimic_set_dash_e: bool = True,
):
    """ Runs a command
        Mimics set -x; print the command before running
        Mimics set -e; check the return code
    """
    if mimic_set_dash_x:
        print(f"+ {' '.join(command)}")
    result = subprocess.run(  # pylint: disable=subprocess-run-check   # nosec
        command,
        shell=False,
        text=True,
        stderr=subprocess.PIPE,  # nosec
    )
    if result.returncode == 0:
        return

    msg: Final[str] = f"Command failed with return code {result.returncode}: {result.stderr}"
    if not mimic_set_dash_e:
        print_colored(msg, color=Colors.RED)
        return

    print_error(msg)
    sys.exit(result.returncode)


class Row:
    """ Row in sqlite which holds column names """

    def __init__(self, keys: List[str], data: List[str]):
        self.__keys = keys
        self.__data: List[Any] = data
        self.__class = self.create_dataclass()
        self.data_class_obj = self.__class(*self.__data)

    def create_dataclass(self, class_name: str = "Row") -> Any:
        """ Creates a dataclass with dynamic fields to hold row data"""
        return dataclasses.make_dataclass(class_name, self.__keys)

    @property
    def data(self):
        return self.__data

    @data.setter
    def data(self, data: List[Any]):
        self.__data = list(data)

    def __getitem__(self, key: str):
        return getattr(self.data_class_obj, key)

    def __iter__(self):
        items = []
        for field in dataclasses.fields(self.data_class_obj):
            items.append(self[field.name])
        return iter(items)


class PrettyTableWrapper:
    def __init__(self, columns: tuple, max_width: int, enable_less: bool):
        """
        Prints a table
        :param columns: field names
        :param max_width: maximum width of each column
        :param enable_less: if True, output will be given to Less
        """
        self.align = "l"
        self.__columns_displaying_names: tuple = columns
        self.__max_width = max_width
        self.__pretty_table: Optional[PrettyTable] = None
        self.__enable_less = enable_less
        self.__records: Optional[List[Row]] = None

    def do_print(self):
        """ prints table with `less` functionality"""
        assert self.records, "`records` property must be set"
        if self.__enable_less:
            PyLess(str(self.__pretty_table)).display()
            return

        print(self.__pretty_table)

    @property
    def records(self) -> Optional[List[Row]]:
        """ gets table records """
        return self.__records

    @records.setter
    def records(self, records: List[Row]):
        """ sets table records """
        self.__records = records
        self.__prepare_table()
        assert isinstance(self.__pretty_table, PrettyTable)
        for id_, row in enumerate(self.__records, start=1):
            # here we replace db_id with new id with is ordinal
            new_columns = [id_]
            for cell in list(row)[1:]:
                new_cell = cell
                if isinstance(cell, bytes):
                    new_cell = cell.decode()
                truncated_new_cell = truncate_text(new_cell, max_length=MAX_CELL_LENGTH)
                new_columns.append(truncated_new_cell)
            self.__pretty_table.add_row(new_columns)

    def __prepare_table(self):
        """ prepare the PrettyTable object """
        self.__pretty_table = PrettyTable(align=self.align, hrules=HRuleStyle.ALL)

        self.__pretty_table.field_names = self.__columns_displaying_names
        self.__set_max_width()

    def __set_max_width(self):
        """ sets maximum width of each column """
        for field_name in self.__pretty_table.field_names:
            self.__pretty_table.max_width[field_name] = self.__max_width

    def __str__(self) -> str:
        return str(self.__pretty_table)


class DatabaseTableManager:
    """ Manages a table in database (only shows its content"""

    def __init__(
            self,
            db_path: str,
            table_name: str,
            column_names: tuple,
    ) -> None:
        self.db_path: Path = Path(db_path).expanduser().resolve()
        self.__validate_if_db_exists()
        self.__table_name: str = table_name
        self.__column_names: tuple = column_names

    def __validate_if_db_exists(self):
        if not self.db_path.exists():
            msg: Final[str] = f"DB '{self.db_path}' does not exist."
            exit_with_message(msg)


    def __fetch_rows(self) -> List[Tuple[Any, ...]]:
        try:
            # Connection is managed with a context manager, which handles commit/rollback.
            with sqlite3.connect(self.db_path) as conn:
                # Create a cursor object using the connection.
                cursor = conn.cursor()
                query = f'SELECT {", ".join(self.__column_names)} FROM {self.__table_name}'
                cursor.execute(query)
                # Fetch all results and store them in a variable.
                rows = cursor.fetchall()
                # Close the cursor after executing the query.
                cursor.close()
                return rows
        except sqlite3.Error as e:
            msg: Final[str] = f"DB '{self.db_path}' does not exist."
            print_colored(msg, color=Colors.RED)
            print_error(f'SQLite error: {e}')
            return []

    @property
    def records(self) -> List[Row]:
        records: List[Row] = []
        rows: List[Tuple[Any, ...]] = self.__fetch_rows()
        for row in rows:
            row_obj = Row(keys=list(self.__column_names), data=list(row))
            records.append(row_obj)
        return records


class HistoryDatabaseManager(DatabaseTableManager):
    """ manages interactions with history database """

    def __init__(  # pylint: disable=too-many-arguments
            self,
            db_path: str,
            start_from_id: int,
            excluded_urls: List[str],
            pretty: PrettyTableWrapper,
            table_name: str,
            column_names: tuple,
    ) -> None:
        super().__init__(db_path, table_name, column_names)
        self.__pretty_table: PrettyTableWrapper = pretty
        self.__excluded_urls = excluded_urls
        self.__start_from_id: int = start_from_id

    @property
    def sanitized_records(self) -> List[Row]:
        """ gets sanitized records from sqlite database """
        sanitized_records: List[Row] = []
        rows = self.records
        for row in rows:
            path = row[ColumnNames.request_path]
            if path not in self.__excluded_urls:
                sanitized_records.append(row)
        for row in sanitized_records[self.__start_from_id - 1:]:
            path = row[ColumnNames.request_path]
            if path not in self.__excluded_urls:
                sanitized_records.append(row)
        return sanitized_records

    def print_sanitized_records(self):
        self.__pretty_table.records = self.sanitized_records
        self.__pretty_table.do_print()


@dataclasses.dataclass(init=True)
class Configuration:
    """ Holds user configuration """
    db_file: str
    base_url: str
    excluded_urls: List[str]
    dry_run: bool
    max_column_width: int
    interactive: bool
    skip_request_errors: bool
    start_from_id: int

    @classmethod
    def from_parse_args(cls) -> "Configuration":
        parsed_args: argparse.Namespace = cls.parse_args()
        conf = Configuration(**parsed_args.__dict__)
        cls.validate(conf)
        return conf

    @staticmethod
    def parse_args() -> argparse.Namespace:
        parser = argparse.ArgumentParser(
            description="Replay HTTP Requests from SQLite Database",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,  # Use the formatter class here
        )
        parser.add_argument('-f', '--db-file', type=str, default='./django_request_replay/db.sqlite3',
                            help='Path to SQLite database file [either absolute or relative path.]')
        parser.add_argument('-b', '--base-url', type=str, default='http://127.0.0.1:8000', help='Base URL of this project')
        parser.add_argument('-e', '--excluded-urls', nargs='*', default=DEFAULT_EXCLUDED_URLS,
                            help='List of URLs to exclude')
        parser.add_argument('-m', '--start-from-id', type=int, default=1,
                            help='Starts reproducing requests from row number <start-from-id>')
        parser.add_argument('-d', '--dry-run', action='store_true',
                            help='Prints all the requests except excluded')
        parser.add_argument('-w', '--max-column-width', type=int, default=MAX_COLUMN_WIDTH,
                            help='List of URLs to exclude')
        parser.add_argument('-i', '--interactive', action='store_true', default=False,
                            help='Enables interactive mode to ask execution of each command from the user.')
        parser.add_argument('-s', '--skip-request-errors', action='store_true', default=False,
                            help='If error 4xx and 5xx occurs, skip them.')

        return parser.parse_args()

    @classmethod
    def validate(cls, conf: "Configuration"):
        """ validates user input """
        if conf.start_from_id <= 0:
            raise ValueError("'start-from-id' must be a positive integer")


class CommandLineInterfaceUtils:

    @classmethod
    def ask_yes_no(cls, question: str, default=DEFAULT_INTERACTIVE_ASK_YES_NO_ANSWER) -> bool:
        """
            Ask a yes/no question via input() and return their answer.

            yes/y -> True
            no/n -> False
        """
        valid_mapping: dict = {"yes": True, "y": True, "no": False, "n": False}

        while True:
            user_choice: str = input(question + " [y/N/q] ").lower()
            if user_choice == "q":
                sys.exit(0)
            if default is not None and user_choice == '':
                return bool(valid_mapping[default])

            if user_choice not in valid_mapping:
                print_colored("Please respond with 'yes' or 'no' or 'quit' (or 'y' or 'n' or 'q').\n", file=sys.stdout)
                continue

            return bool(valid_mapping[user_choice])


class RequestReplayer:
    """ regenerates the state that is saved on sqlite db with pretty table functionality"""

    def __init__(  # pylint: disable=too-many-arguments
            self,
            db_man: HistoryDatabaseManager,
            command_line_interface: CommandLineInterfaceUtils,
            pretty: PrettyTableWrapper,
            conf: Configuration,
    ) -> None:
        self.__pretty_table: PrettyTableWrapper = pretty
        self.__base_url: str = conf.base_url
        self.__interactive: bool = conf.interactive
        self.__skip_request_errors: Final[bool] = conf.skip_request_errors
        self.__db_manager = db_man
        self.__auth_token: Optional[str] = None
        self.__cli_interface_utils: CommandLineInterfaceUtils = command_line_interface
        self.__conf: Configuration = conf


    def __send_request(self, url: str, method: str, **kwargs):
        try:
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            }
            if self.__auth_token:
                headers['Authorization'] = f"Token {self.__auth_token}"
            return requests.request(
                url=url,
                method=method,
                headers=headers,
                verify=False,  # NOSONAR
                allow_redirects=False,
                timeout=30,
                **kwargs
            )
        except requests.RequestException as e:
            print_colored(
                f'exception: {e}\n',
                color=Colors.RED,
                file=sys.stderr
            )
            raise e

    def replay_requests(self, records_to_replay: List[Row]) -> None:
        for request_num, record in enumerate(records_to_replay, start=1):

            if self.__interactive is False:
                self.__replay_none_interactive(request_num, record)
                continue

            total_requests_num = len(records_to_replay)
            self.__replay_interactive(request_num, record, total_requests_num)

    def process_record(self, request_num: int, record: Row) -> Tuple[bool, int]:
        method = record[ColumnNames.request_method]
        path = record[ColumnNames.request_path]
        data = record[ColumnNames.request_data]
        url = f'{self.__base_url}{path}'
        request_data = self.parse_request_data(data)

        response = self.__send_request(url, method, json=request_data)
        records = [record]
        self.__pretty_table.records = records
        return self.handle_response(request_num, record, response)

    @staticmethod
    def parse_request_data(data: bytes) -> Optional[dict]:
        try:
            return dict(json.loads(data))
        except json.JSONDecodeError:
            return None

    @staticmethod
    def handle_response(request_num: int, record: Row, response) -> Tuple[bool, int]:
        method = record[ColumnNames.request_method]
        path = record[ColumnNames.request_path]
        status_code: int = response.status_code

        msg: str = f'Request #{request_num} (code: {status_code}) {method.upper()} {path}, \n\n'

        if 200 <= response.status_code <= 299:
            print_colored(
                "-> SUCCEEDED: " + msg,
                Colors.GREEN,
                file=sys.stdout,
                flush=False,
            )
            return True, status_code

        print_error("-> FAILED: " + msg)

        return False, status_code

    def get_to_be_processed_records(self) -> List[Row]:
        records = self.__db_manager.records
        if not records:
            exit_with_message(f"There are no processable records on db '{self.__db_manager.db_path}'")

        sanitized_records = self.__db_manager.sanitized_records
        return sanitized_records

    def start_replay(self) -> None:
        records_to_replay: List[Row] = self.get_to_be_processed_records()
        self.replay_requests(records_to_replay)

    def validate(self):
        """ validates provided data and object to check whether reply is possible """
        total_records = self.__db_manager.records
        to_be_processed_records = self.get_to_be_processed_records()
        if not to_be_processed_records:
            exit_with_message(f"There are no processable records on db '{self.__conf.db_file}'")

        print_colored(f"Number of total records: {len(total_records)}\n"
                      f"Number of processable records: {len(to_be_processed_records)}\n")

    def __replay_interactive(self, request_num: int, record: Row, total_requests_num: int):
        self.__pretty_table.records = [record]
        prompt_message = f"{self.__pretty_table}\n" \
                         f"Replay request {request_num}/{total_requests_num}? (ID: {record[ColumnNames.id]})"
        is_answer_yes: bool = self.__cli_interface_utils.ask_yes_no(question=prompt_message)
        if not is_answer_yes:
            print_colored(f"Skipping request {request_num}.")
            return

        print_colored(f"Executing request {request_num}.")
        self.process_record(request_num, record)

    def __replay_none_interactive(self, request_num: int, record: Row):
        success, _ = self.process_record(request_num, record)
        if success:
            return
        if self.__skip_request_errors:
            return

        exit_with_message("Exiting after receiving error...")



if __name__ == "__main__":
    configuration: Configuration = Configuration.from_parse_args()

    print_colored(f'excluded_urls: \n\t{configuration.excluded_urls}\n')
    pretty_obj = PrettyTableWrapper(
        columns=ColumnNames().table_displaying_names,
        max_width=configuration.max_column_width,
        enable_less=configuration.interactive,
    )
    db_manager = HistoryDatabaseManager(
        db_path=configuration.db_file,
        start_from_id=configuration.start_from_id,
        excluded_urls=configuration.excluded_urls,
        pretty=pretty_obj,
        table_name=HISTORY_CONFIG_TABLE_NAME,
        column_names=ColumnNames().table_displaying_names,
    )
    request_replayer = RequestReplayer(
        db_man=db_manager,
        pretty=pretty_obj,
        command_line_interface=CommandLineInterfaceUtils(),
        conf=configuration,
    )

    request_replayer.validate()

    if configuration.dry_run:
        db_manager.print_sanitized_records()
        exit_with_message('done.', code=0)

    request_replayer.start_replay()
