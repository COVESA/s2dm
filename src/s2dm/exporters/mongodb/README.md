# MongoDB BSON Schema Exporter

Translates an S2DM GraphQL schema into MongoDB BSON validator schemas — one schema per exportable GraphQL type.

## Output

Each schema is a bare BSON object (no `$jsonSchema` wrapper) intended to be used as:

```js
db.createCollection("MyType", {
  validator: { $jsonSchema: <contents of MyType.json> }
})
```

**Default mode** writes all types to a single `output.json` dict keyed by type name.
**Modular mode** (`--modular`) writes one `TypeName.json` per type.

## BSON Type Mapping

### Built-in scalars

| GraphQL | BSON |
|---------|------|
| `String` | `string` |
| `Int` | `int` |
| `Float` | `double` |
| `Boolean` | `bool` |
| `ID` | `objectId` |

### S2DM extended scalars (`common.graphql`)

| GraphQL | BSON |
|---------|------|
| `Int8`, `UInt8`, `Int16`, `UInt16`, `UInt32` | `int` |
| `Int64`, `UInt64` | `long` |

Unknown scalars fall back to `string`.

### GeoJSON scalar (`geojson.graphql`)

The `GeoJSON` scalar with `@geoType(shape: ...)` emits a hardcoded BSON geometry schema. Without `@geoType`, a permissive object requiring only `type` and `coordinates` is emitted.

Supported shapes: `POINT`, `MULTIPOINT`, `LINESTRING`, `MULTILINESTRING`, `POLYGON`, `MULTIPOLYGON`.

> MongoDB `$jsonSchema` does not support `oneOf`, so only `POINT` can be fully validated at all nesting levels. Other shapes are validated at the first level only.

## Nullability

| GraphQL | `bsonType` | In `required`? |
|---------|-----------|----------------|
| `field: T!` | `"<type>"` | yes |
| `field: T` | `["<type>", "null"]` | no |

## Directive Mapping

| Directive | BSON output |
|-----------|------------|
| `@range(min, max)` on scalar field | `minimum` / `maximum` on the field ||
| `@range(min, max)` on list field | `minimum` / `maximum` inside `items` |
| `@noDuplicates` | `uniqueItems: true` |
| `@cardinality(min, max)` | `minItems` / `maxItems` |
| `@instanceTag` | type and its reference field on parent types both excluded |

GraphQL docstrings (`field.description`, `type.description`) are emitted as `description` automatically — `@metadata(comment)` is not used here. MongoDB does not support `$comment`; `description` is included in validation error messages since MongoDB 5.1.

### `@instanceTag` behaviour

Without `--expanded-instances` the exporter has no way to represent instance tag structures:
- `@instanceTag` types are excluded as top-level entries
- The `instanceTag` field on parent types (the reference pointing to the tag type) is also dropped

With `--expanded-instances` the schema loader unfolds the tag structure into concrete fields *before* the transformer runs, so neither the `@instanceTag` type nor the reference field appear in the transformer's input at all.

## Exclusions

Never exported as top-level entries:
- Root types (`Query`, `Mutation`, `Subscription`)
- `@instanceTag` types
- Scalars and enums (always inlined at usage site)
- GraphQL introspection types

## Circular References

MongoDB does not support `$ref`, so circular type references cannot be represented. The transformer raises a `ValueError` identifying the cycle before any output is written.

## Architecture

```
mongodb/
├── __init__.py      # Public API: translate_to_mongodb()
├── mongodb.py       # Entry points: transform(), translate_to_mongodb(), to_json_string()
└── transformer.py   # MongoDBTransformer — all GraphQL → BSON logic
```

`MongoDBTransformer.transform()` returns `dict[str, dict]`. Each value is a bare BSON schema built by recursive inlining — no `$ref`, no `$defs`. Circular reference detection is done via a `frozenset[str]` of type names currently being resolved.

## MongoDB `$jsonSchema` restrictions

This exporter deliberately avoids these unsupported keywords:

- `$ref`, `$schema`, `definitions`, `$defs`
- `default`, `format`, `id`
- `integer` type (use `int` or `long`)
- `$comment` (use `description` — supported since MongoDB 5.1)

Reference: [MongoDB JSON Schema omissions](https://www.mongodb.com/docs/manual/reference/operator/query/jsonSchema/#json-schema-omissions)
