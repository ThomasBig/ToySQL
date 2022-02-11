<div align="center">
  <img src="logo.svg" width="200" />
  <h3>SQL Generation Tool</h3>
</div>

## ToySQL
Define your tables using friendly syntax with *type inheritence* and *variable
support*. Initialize tables with *testing data* and boost your productivity.
Moreover, ToySQL assigns *key constraints* for you. It is a human readable
version of SQL inspired by TOML and table sheets.

## Instalation
* Install `Python 3+` and Lark using `pip install Lark`.
* Use python3 to run `tsql.py [-s|--sql] [PostgreSQL|SqlLite] file1.tsql file2.tsql ...`

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

## Primary and foreign keys
* unknown variables in column make a primary key column
* known variables in column make a foreign key column
