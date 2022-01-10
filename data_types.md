# DATA TYPES
## Null type
| example | explanation | enforcement rules |
| - | - | - |
| `NULL` | absence of value | one NULL value in column will change the whole column to accept NULLs, however tsql needs to have at least one other value to assign type.

## Character types
| examples | sql names | explanation | enforcement rules |
| - | - | - | - |
| `'C'` | char | single ascii char | column is single character long and contains only ascii characters
| `'chars'` | varchars | multiple ascii chars | column contains only ascii characters
| `'😊'` | nchar | single unicode char | column is single character long
| `'أحبك'` | nchar varying | multiple unicode chars | -
| `"many chars"` | clob, text | character large object | -
| `"コンピューター"` | nlob, unicode text | national character large object | -

## Booleans and binary types
| examples | sql names | explanation | enforcement rules |
| - | - | - | - |
| `TRUE`, `FALSE` | boolean | logic states | -
| `0b100`, `0o773`, `0xFF00BB` | binary | binary string of fixed size | column has fixed size
| `0b1110110`, `0o1553`, `0x1FFBCD` | varbinary | binary text | -
| `<0x001101>` | BLOB | binary large object | -

## Number types
| examples | sql names | explanation | enforcement rules |
| - | - | - | - |
|`32120` | smallint | small whole number | range [-32_768;32_767]
|`163752` | int, integer, mediumint | medium sized whole number | range [-2_147_483_648;2_147_483_647]
|`5e30` | bigint | large whole number | column contains integers
|`5.14` | decimal, numeric | precise base 10 fraction | -
|`5.14'` | real | imprecise floating point number float[24] | range [-3.40e+38;-1.18e-38] or [1.18e-38;3.40e+38]
|`1.5e-20'` | double, double precision | higher precise floating point numbers float[53] | -

## Dates and times
| examples | sql names | format |
| - | - | - |
| `2030-6-10`, `2025-12-15` | date | YYYY-[M]M-[D]D |
|`10:30:15`, `8:45:20.155` | time | [H]H:[M]M:[S]S[.F] |
|`2025-12-15T`, `2025-12-15T10:30:15` | datetime | YYYY-[M]M-[D]DT[[H]H:[M]M:[S]S[.F]] |
| `2025-12-15P`, `2025-12-15P10:30:15` | timestamp | YYYY-[M]M-[D]DP[[H]H:[M]M:[S]S[.F]] |
| `-0-0-5I`, `+8-10-15I10:20:00` | interval | [sign]Ys-Ms-DsI[Hs:Ms:Ss[.Fs]]

## Special types
* at the moment anything is not checked and outer xml tag is not used in insert
* at the moment content in brackets is not checked and is used in insert statement without these brackets

| examples | sql names | valid type, valid tsql | invalid type, valid tsql |
| - | - | - | - |
| `<xml>anything</xml>`, `<xml/>` | xml | `<xml><recipe>Margarita pizza</recipe></xml>` | `<xml><title>basketball</xml>`
| `{anything}` | json | `{2.56}`, `{[-2,3]}`, `{{"name":"tom"}}` | `{[5.89, 5}}`
