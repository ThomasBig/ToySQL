from sys import exit, argv
from lark import Lark # ONLINE: https://www.lark-parser.org/ide/
from enum import Enum, auto

class DbType(Enum):
    SQLite = auto(), # uses as in returning clauses
    PostgresSQL = auto(), # uses into in returning clauses

#TODO: ADD COMMANDLINE OPTION
DB_TYPE = DbType.SQLite

class Error(Enum):
    # TODO: ADD CHECK FOR ONLY ONE PRIMARY KEY IN THE TABLE
    WrongColumnsCount = auto(),
    ColumnsCountInconsistent = auto(),
    DifferentTypesInColumn = auto(),
    KnownVariableInPrimaryColumn = auto(),
    UnknownVariableInForeignColumn = auto(),
    WrongVariableInForeignColumn = auto(),

# TODO: ADD NULL SUPPORT AND DATETIME/TIMESTAMP SUPPORT
grammar = Lark(r'''
// A bunch of tables
start: table+

// Each table is defined from name in curly brackets, columns and values
table: "{" WORD "}" "\n" columns "\n" data "\n"?
columns: ("[" WORD "]")+
data: row+
row: value+ "\n"
?value: variable | string | number
variable: WORD
string: ESCAPED_STRING
?number: float | decimal | int
float: FLOAT
decimal: DECIMAL
int: SIGNED_INT

// imports from common library
WORD: ("a".."z" | "A".."Z" | "_")+
%import common.WS
%import common.ESCAPED_STRING
%import common.SIGNED_INT
%import common.SQL_COMMENT
%import common.FLOAT
%import common.DECIMAL

// disregard spaces and comments in text
%ignore " "
%ignore "\n\n"
%ignore SQL_COMMENT
''')

def syntax(fname):
    with open(fname, 'r') as file:
        return grammar.parse(file.read())

class Table:
    variables = {}

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
        return type

    def into():
        global DB_TYPE
        if DB_TYPE == DbType.SQLite:
            return 'AS'
        if DB_TYPE == DbType.PostgresSQL:
            return 'INTO'

    def __str__(self):
        inner_tables = []
        for ((name, type), primary), foreign in \
         zip(zip(zip(self.column_names, self.types), self.primaries), self.foreigns):
            if primary:
                inner_tables.append(f'    {name} SERIAL PRIMARY KEY')
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
            primary_identifier = None
            for (((type, value), column), primary), foreign in \
              zip(zip(zip(values, column_names), primaries), foreigns):
                if primary:
                    primary_identifier = (value, column)
                    continue
                if foreign:
                    columns_values.append((column, value))
                else:
                    columns_values.append((column, value))
            unzipped = list(zip(*columns_values))
            columns = ', '.join(unzipped[0])
            values = ', '.join(unzipped[1])
            returning = ''
            if primary_identifier is not None:
                identifier, column = primary_identifier
                returning = f' RETURNING {column} {Table.into()} {identifier}'
            result.append(f'INSERT INTO {self.name} ({columns}) VALUES ({values}){returning};')
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

if __name__ == "__main__":
    if len(argv) == 1:
        print("Please provide at least one source file")

    for fname in argv[1:]:
        tree = syntax(fname)
        tables = semantics(tree)
        tables
