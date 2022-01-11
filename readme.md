# ToySQL
ToySQL is code generation tool for SQL. Define your sql tables and initialize
them with testing data. ToySQL automatically assigns correct types and key
constraints. It is a more human readable version of SQL with variable support.

## Instalation
* Install `Python 3+` and Lark using `pip install Lark`.
* Use python3 to run `tsql.py [-s|--sql] [PostgreSQL|SqlLite] file1.tsql file2.tsql ...`

## Example
ToySQL Input
```sql
{ Category }
[ id ] [ name ]
america "America"
na "North America"
sa "South America"

{ CategoryAdjecencies }
[ parent_id ] [ child_id ]
america na
america sa

{ Product }
[ id ] [ name ] [ category_id ] [ price ]
"Tomato" na 24
"Ananas" sa 12
"Apple" america 30  -- grows in both
```

SQL Output (default is PostgreSQL)
```sql
CREATE TABLE Category (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);

INSERT INTO Category (name) VALUES ('America');
INSERT INTO Category (name) VALUES ('North America');
INSERT INTO Category (name) VALUES ('South America');

CREATE TABLE CategoryAdjacencies (
    parent_id INTEGER REFERENCES Category(id),
    child_id INTEGER REFERENCES Category(id)
);

INSERT INTO CategoryAdjacencies (parent_id, child_id) VALUES (1, 2);
INSERT INTO CategoryAdjacencies (parent_id, child_id) VALUES (1, 3);

CREATE TABLE Product (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category_id INTEGER REFERENCES Category(id),
    price INTEGER NOT NULL
);

INSERT INTO Product (name, category_id, price) VALUES ('Tomato', 2, 24);
INSERT INTO Product (name, category_id, price) VALUES ('Ananas', 3, 12);
INSERT INTO Product (name, category_id, price) VALUES ('Apple', 1, 30);
```

## Syntax
* `--` comment
* `{ name }` defines new table with name.
* `[ name ]` defines new column with a name, must succeed *table* or *column* definition.
* `lowerCase` defines new variable
* `UpperCase` defines new constant (enumeration)
* `"String"` defines a new string
* `5` defines an integer
`5.6` defines an decimal
`3.14'` defines a real number
* `1999-5-28T` defines date
`1999T10:50` defines datetime
* `NULL` defines nullable field
* All [supported types](data_types.md)

## Primary and foreign keys
* new unknown variables in column make column be a primary serial key
* already known variables in column make column be a foreign key
