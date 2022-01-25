from sys import exit, argv, path
from lark import Lark # ONLINE: https://www.lark-parser.org/ide/
from enum import Enum, auto
import csv

class AutoName(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name

class Error(AutoName):
    WrongColumnsCount = auto()
    ColumnsCountInconsistent = auto()
    DifferentTypesInColumn = auto()
    KnownVariableInPrimaryColumn = auto()
    UnknownVariableInForeignColumn = auto()
    WrongVariableInForeignColumn = auto()
    ReservedKeyword = auto()

class DbType(AutoName):
    # TODO: Add Oracle and MySQL https://sqliteonline.com/
    PostgreSQL = auto()
    SQLite = auto()

    @classmethod
    def list(cls):
        return [member.value for role, member in cls.__members__.items()]

class KeywordType():
    Reserved = "reserved"
    Semi = "semi reserved"

directory = path[0]

def read_keywords():
    keywords = {}
    with open(f'{directory}/keywords.csv') as csv_file:
        reader = csv.reader(csv_file, delimiter=' ', strict=True)
        header = next(reader)
        for row in reader:
            try:
                keywords[row[0]] = (header[row.index("reserved", 1)], KeywordType.Reserved)
            except ValueError:
                try:
                    keywords[row[0]] = (header[row.index("semi-reserved", 1)], KeywordType.Semi)
                except ValueError:
                    continue
    return keywords

def read_grammar():
    with open(f'{directory}/grammar.lark') as grammar:
        return Lark(grammar)

keywords = read_keywords()
grammar = read_grammar()

def syntax(fname):
    with open(fname, 'r') as file:
        return grammar.parse(file.read())

class Table:
    variables = {}
    db_type = DbType.PostgreSQL
    no_create = False

    def check_column_counts(name, columns, values):
        row_sizes = [len(row) for row in values]
        min_row = min(row_sizes)
        if min_row != len(columns) and min_row + 1 != len(columns):
            exit(f'{Error.WrongColumnsCount}: Number of columns in '
                 f'`{name}` table is not equal to defined number of columns!')
        if min_row != max(row_sizes):
            exit(f'{Error.ColumnsCountInconsistent}: Number of columns '
                 f'in {name} table is not consistent!')

    def check_column_types(table, columns, column_names):
        types = []
        if len(columns) == len(column_names) - 1:
            types.append('variable')
        enum_variants = []
        for column, column_name in zip(columns, column_names):
            if len(enum_variants) > 1:
                types[-1] = (types[-1] , enum_variants[0], enum_variants[1:])
            enum_variants = [column_name]
            types.append(None)
            for type, value in column:
                if types[-1] is None:
                    types[-1] = type
                is_correct_type = type == types[-1]
                if not is_correct_type:
                    exit(f'{Error.DifferentTypesInColumn}: '
                         f'In table `{table}`, {type} `{value}` was found '
                         f'in {types[-1]} column `{column_name}`!')
                if type == 'constant':
                     enum_variants.append(value)
        if len(enum_variants) > 1:
            types[-1] = (types[-1] , enum_variants[0], enum_variants[1:])
        return types

    def check_primary_keys(table, columns, column_names, column_types):
        primary_key_columns = []
        # short notation allows first column be completely empty
        if len(columns) == len(column_names) - 1:
            column_names = column_names[1:]
            column_types = column_types[1:]
            primary_key_columns.append(True)
        for (column, column_name), column_type in zip(zip(columns, column_names), column_types):
            if column_type != 'variable':
                primary_key_columns.append(False)
                continue
            primary_key_columns.append(None)
            for id, (type, value) in enumerate(column):
                is_primary_key = value not in Table.variables
                if primary_key_columns[-1] is None:
                    primary_key_columns[-1] = is_primary_key
                if primary_key_columns[-1]:
                    if not is_primary_key:
                        exit(f'{Error.KnownVariableInPrimaryColumn}: '
                             f'Found already defined variable `{value}` in '
                             f'primary key column `{column_name}` of table `{table}`!')
                    Table.variables[value] = (table, column_name, id)
        return primary_key_columns

    def check_foreign_keys(table, columns, column_names, column_types):
        foreign_key_columns = []
        if len(columns) == len(column_names) - 1:
            column_names = column_names[1:]
            column_types = column_types[1:]
            foreign_key_columns.append(None)
        for (column, column_name), column_type in zip(zip(columns, column_names), column_types):
            foreign_key_columns.append(None)
            if column_type != 'variable':
                continue
            for type, value in column:
                is_foreign_key = value in Table.variables
                if is_foreign_key:
                    belongs_to = (Table.variables[value][0], Table.variables[value][1])
                if foreign_key_columns[-1] is None:
                    foreign_key_columns[-1] = belongs_to
                if not is_foreign_key and foreign_key_columns[-1] is not None:
                    exit(f'{Error.UnknownVariableInForeignColumn}: '
                         f'Found unknown variable `{value}` in foreign key '
                         f'column `{column_name}` of table `{table}`!')
                if is_foreign_key and belongs_to != foreign_key_columns[-1]:
                    exit(f'{Error.WrongVariableInForeignColumn}: '
                         f'Variable `{value}` in foreign key column `{column_name}` '
                         f'of table `{table}` belongs to {"->".join(belongs_to)} '
                         f'and not {"->".join(foreign_key_columns[-1])}!')
        return foreign_key_columns

    def check_column_names(table, column_names):
        for name in column_names:
            lowercase = name.upper()
            if lowercase in keywords:
                where, what = keywords[lowercase]
                print(f'{Error.ReservedKeyword}: In table {table} column {name} is {what} in {where}!')
                exit()

    def __init__(self, name, column_names, values):
        Table.check_column_names(name, column_names)
        Table.check_column_counts(name, column_names, values)
        columns = [[values[j][i] for j in range(len(values))] for i in range(len(values[0]))]
        self.name = name
        self.column_names = column_names
        self.values = values
        self.types = Table.check_column_types(name, columns, column_names)
        self.primaries = Table.check_primary_keys(name, columns, column_names, self.types)
        self.foreigns = Table.check_foreign_keys(name, columns, column_names, self.types)

    def get_enum_name(self, column):
        return self.name.upper() + '_' + column[1].upper()

    def replace_type(self, c_type):
        # TODO: Add enforcement rules
        if c_type == 'string':
            return 'VARCHAR(255)'
        if c_type == 'boolean':
            return 'BOOLEAN'
        if c_type == 'integer':
            return 'INTEGER'
        if c_type == 'float':
            return 'REAL'
        if c_type == 'timestamp':
            return 'TIMESTAMP'
        if type(c_type) is tuple and c_type[0] == 'constant':
            return self.get_enum_name(c_type)
        exit(f'Internal Error: Unrecognised type {type}')
        return type

    def replace_value(type, value):
        if type == 'string':
            return value.replace('"', "'").replace("\\'", "''")
        if type == 'timestamp':
            return f"'{value.replace('P', ' ')}'"
        if type == 'datetime':
            return value.replace('T', ' ')
        if type == 'constant':
            return f"'{value}'"
        return value

    def serial(unique):
        primary = ' PRIMARY KEY' if unique else ''
        if Table.db_type == DbType.PostgreSQL:
            return f'SERIAL{primary}'
        if Table.db_type == DbType.SQLite:
            return f'INTEGER{primary} AUTOINCREMENT'
        exit(f'Internal Error: Unrecognised db type {Table.db_type}')

    def tables_enums(self):
        enums = []
        for column in self.types:
            # find constant columns
            if type(column) is tuple:
                variants = ', '.join(set(map(lambda x: f"'{x}'", column[2])))
                enums.append(f'CREATE TYPE {self.get_enum_name(column)} AS ENUM (\n  {variants}\n);\n\n')
        inner_tables = []
        primary_single_column = sum(self.primaries) == 1
        for ((name, c_type), primary), foreign in \
         zip(zip(zip(self.column_names, self.types), self.primaries), self.foreigns):
            if primary:
                inner_tables.append(f'    {name} {Table.serial(primary_single_column)}')
            elif foreign is not None:
                inner_tables.append(f'    {name} INTEGER REFERENCES {foreign[0]}({foreign[1]})')
            else:
                inner_tables.append(f'    {name} {self.replace_type(c_type)} NOT NULL')
        if not primary_single_column:
            zipped_keys = []
            if sum(self.primaries) > 1:
                zipped_keys = filter(lambda x: x[1], zip(self.column_names, self.primaries))
            elif sum(map(lambda x: x is not None, self.foreigns)) > 0:
                zipped_keys = filter(lambda x: x[1] is not None, zip(self.column_names, self.foreigns))
            else:
                # no primary or foreign keys were found - use everything we have
                zipped_keys = zip(self.column_names, self.column_names)
            if zipped_keys:
                keys = ", ".join(list(map(lambda x: x[0], zipped_keys)))
                inner_tables.append(f'    PRIMARY KEY ({keys})')
        return '\n'.join(enums) + f'CREATE TABLE {self.name} (\n' + ',\n'.join(inner_tables) + '\n);\n'

    def __str__(self):
        if Table.no_create:
            # PostgreSQL way
            result = [f'TRUNCATE {self.name} RESTART IDENTITY CASCADE;']
        else:
            result = [self.tables_enums()]
        for values in self.values:
            columns_values = []
            if len(values) == len(self.column_names) - 1:
                column_names = self.column_names[1:]
                primaries = self.primaries[1:]
                foreigns = self.foreigns[1:]
            else:
                column_names = self.column_names
                primaries = self.primaries
                foreigns = self.foreigns
            foreign_link = None
            for (((c_type, value), column), primary), foreign in \
              zip(zip(zip(values, column_names), primaries), foreigns):
                if primary:
                    continue
                if foreign:
                    columns_values.append((column, str(1 + Table.variables[value][2])))
                else:
                    columns_values.append((column, Table.replace_value(c_type, value)))
            unzipped = list(zip(*columns_values))
            columns = ', '.join(unzipped[0])
            values = ', '.join(unzipped[1])
            if foreign_link is None:
                result.append(f'INSERT INTO {self.name} ({columns}) VALUES ({values});')
            else:
                result.append(str(foreign_link))
        result.append('\n')
        return '\n'.join(result)

def semantics(tree):
    tables = []
    for table in tree.children:
        name = table.children[0]
        columns = [token.value for token in table.children[1].children]
        values = [[(column.data.value, column.children[0].value)
            for column in row.children] for row in table.children[2].children]
        tables.append(Table(name.value, columns, values))
    return tables

def get_flags(args):
    arguments = []
    flags = []
    isFlag = False
    for argument in args[1:]:
        if isFlag:
            flags[-1] = (flags[-1], argument)
            isFlag = False
        elif argument.startswith('-'):
            isFlag = True
            flags.append(argument)
        else:
            arguments.append(argument)
    if isFlag:
        print(f'Value was not found for flag {flags[-1]}.')
        exit()
    return arguments, flags

if __name__ == '__main__':
    # hide traceback: sys.tracebacklimit = 0
    if len(argv) == 1:
        print('Please provide at least one source file.')
        exit()
    (fnames, flags) = get_flags(argv)
    supported = ', '.join(DbType.list())
    for (flag, value) in flags:
        if flag == '-s' or flag == '--sql':
            if value not in DbType.list():
                print(f'Unsupported database {value}. Currently supported {supported}. '
                      f'You can try one of those. If it doesn\'t work, create an issue.')
                exit()
            Table.db_type = DbType[value]
        if flag == '-u' or flag == '--update':
            Table.no_create = True
    for fname in fnames:
        tree = syntax(fname)
        tables = semantics(tree)
        print(''.join(map(str, tables)), end='')
