from sys import exit, argv
from lark import Lark # ONLINE: https://www.lark-parser.org/ide/
from enum import Enum, auto

class Error(Enum):
    # TODO: ADD CHECK FOR ONLY ONE PRIMARY KEY IN THE TABLE
    WrongColumnsCount = auto(),
    ColumnsCountInconsistent = auto(),
    DifferentTypesInColumn = auto(),
    KnownVariableInPrimaryColumn = auto(),
    UnknownVariableInForeignColumn = auto(),
    WrongVariableInForeignColumn = auto(),

class AutoName(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name

class DbType(AutoName):
    # TODO: Add ORACLE and MariaDB, MySQL https://sqliteonline.com/
    PostgreSQL = auto()
    SQLite = auto()

    @classmethod
    def list(cls):
        return [member.value for role, member in cls.__members__.items()]


grammar = Lark(r'''
// A bunch of tables
start: table (_NL table)* _NL*

// Each table is defined from name in curly brackets, columns and values
table: _LCB WORD _RCB "\n" columns "\n" data
columns: (_LSB WORD _RSB)+
data: (row "\n")+
row: value (_S value)*
?value: string | null | boolean | date_time | float | integer | variable

// variable
variable: WORD

// null
null: "NULL"

// boolean
boolean: true | false
true: "TRUE"
false: "FALSE"

// date_time
?date_time: offset_date_time | local_date_time | local_date | local_time

_time_offset: "Z"i | ( "+" | "-" ) DIGIT2 ":" DIGIT2
_partial_time: DIGIT2 ":" DIGIT2 ":" DIGIT2 [ "." DIGIT+ ] // 01-12 // 01-28, 01-29, 01-30, 01-31 based on month|year
_full_date: DIGIT4 "-" DIGIT2 "-" DIGIT2
_full_time: _partial_time _time_offset

offset_date_time: _full_date "T"i _full_time
local_date_time: _full_date "T"i _partial_time
local_date: _full_date
local_time: _partial_time

// integer
integer: DEC_INT | HEX_INT | OCT_INT | BIN_INT

DEC_INT: [ "-" | "+" ] DIGIT | "1".."9" ( DIGIT | "_" DIGIT )+
HEX_INT: "0x" HEXDIG *( HEXDIG | "_" HEXDIG )
OCT_INT: "0o" "0".."7" *( "0".."7" | "_" "0".."7" )
BIN_INT: "0b" "0".."1" *( "0".."1" | "_" "0".."1" )

// string
// TODO: national alphabets
string: ESCAPED_STRING
ESCAPED_STRING: "'" INNER_STRING "'" | "\"" INNER_STRING "\""
INNER_STRING: /.*?/ /(?<!\\)(\\\\)*?/

// float
float: FLOAT
FLOAT: DEC_INT ( EXP | "." ZERO_PREFIXABLE_INT [ EXP ] ) | SPECIAL_FLOAT
ZERO_PREFIXABLE_INT: DIGIT *( DIGIT | "_" DIGIT )
EXP: "e" [ "-" | "+" ] ZERO_PREFIXABLE_INT
SPECIAL_FLOAT: [ "-" | "+" ] ( "inf" | "nan" )


// brackets
_LCB: _S* "{" _S*
_RCB: _S* "}" _S*
_LSB: _S* "[" _S*
_RSB: _S* "]" _S*
_S: " " | "\t"
_NL: "\n"+ | "\r\n"+

// imports from common library
DIGIT: "0".."9"
DIGIT4: /[0-9]{4}/
DIGIT2: /[0-9]{2}/
HEXDIG: DIGIT | "A"i | "B"i | "C"i | "D"i | "E"i | "F"i
WORD: ("a".."z" | "A".."Z" | "_")+
%import common.SIGNED_INT
%import common.INT

SQL_COMMENT: _S* /--[^\n]*/
// disregard spaces and comments in text
%ignore SQL_COMMENT
''')

def syntax(fname):
    with open(fname, 'r') as file:
        return grammar.parse(file.read())

class Table:
    variables = {}
    db_type = DbType.PostgreSQL

    def check_column_counts(name, columns, values):
        row_sizes = [len(row) for row in values]
        min_row = min(row_sizes)
        if min_row != len(columns) and min_row + 1 != len(columns):
            exit(f'{Error.WrongColumnsCount}: Number of columns in'
                 f'`{name}` table is not equal to defined number of columns!')
        if min_row != max(row_sizes):
            exit(f'{Error.ColumnsCountInconsistent}: Number of columns'
                 f'in {name} table is not consistent!')

    def check_column_types(table, columns, column_names):
        types = []
        if len(columns) == len(column_names) - 1:
            types.append('variable')
        for column, column_name in zip(columns, column_names):
            types.append(None)
            for type, value in column:
                if types[-1] is None:
                    types[-1] = type
                is_correct_type = type == types[-1]
                if not is_correct_type:
                    exit(f'{Error.DifferentTypesInColumn}: '
                         f'In table `{table}`, {type} `{value}` was found '
                         f'in {column_type} column `{column_name}`!')
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

    def __init__(self, name, column_names, values):
        Table.check_column_counts(name, column_names, values)
        columns = [[values[j][i] for j in range(len(values))] for i in range(len(values[0]))]
        self.name = name
        self.column_names = column_names
        self.values = values
        self.types = Table.check_column_types(name, columns, column_names)
        self.primaries = Table.check_primary_keys(name, columns, column_names, self.types)
        self.foreigns = Table.check_foreign_keys(name, columns, column_names, self.types)
        print(self, end='')

    def replace_type(type):
        if type == 'string':
            return 'VARCHAR(255)'
        if type == 'int':
            return 'INTEGER'
        if type == 'float':
            return 'FLOAT'
        if type == 'decimal':
            return 'DECIMAL'
        exit(f'Internal Error: Unrecognised type {type}')
        return type

    def quote(string):
        return string.replace('"', "'")

    def serial():
        if Table.db_type == DbType.PostgreSQL:
            return 'SERIAL PRIMARY KEY'
        if Table.db_type == DbType.SQLite:
            return 'INTEGER PRIMARY KEY AUTOINCREMENT'
        exit(f'Internal Error: Unrecognised db type {Table.db_type}')

    def __str__(self):
        inner_tables = []
        for ((name, type), primary), foreign in \
         zip(zip(zip(self.column_names, self.types), self.primaries), self.foreigns):
            if primary:
                inner_tables.append(f'    {name} {Table.serial()}')
            elif foreign is not None:
                inner_tables.append(f'    {name} INTEGER REFERENCES {foreign[0]}({foreign[1]})')
            else:
                inner_tables.append(f'    {name} {Table.replace_type(type)} NOT NULL')
        result = [f'CREATE TABLE {self.name} (\n' + ',\n'.join(inner_tables) + '\n);\n']
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
            for (((type, value), column), primary), foreign in \
              zip(zip(zip(values, column_names), primaries), foreigns):
                if primary:
                    continue
                if foreign:
                    columns_values.append((column, str(1 + Table.variables[value][2])))
                else:
                    columns_values.append((column, Table.quote(value)))
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
    if len(argv) == 1:
        print('Please provide at least one source file')
        sys.exit()
    (fnames, flags) = get_flags(argv)
    supported = ', '.join(DbType.list())
    for (flag, value) in flags:
        if flag != '-s' and flag != '--sql':
            print(f'Unrecognised flag {flag}. Currently supported only -s and --sql.')
            exit()
        if flag == '-s' or flag == '--sql':
            if value not in DbType.list():
                print(f'Unsupported database {value}. Currently supported {supported}. '
                      f'You can try one of those. If it doesn\'t work, create an issue.')
                exit()
            Table.db_type = DbType[value]
    for fname in fnames:
        tree = syntax(fname)
        tables = semantics(tree)
        tables
