---
title: Mongo DB exporter
weight: 400
chapter: false
---

### MongoDB BSON Validators

This exporter generates [MongoDB collection validators](https://www.mongodb.com/docs/manual/core/schema-validation/) from your S2DM schema. Each object type in your schema becomes a separate JSON file that MongoDB can use to validate documents as they are inserted or updated.

> In other words: once you export and register the validator, MongoDB will reject any document that does not match the shape defined in your GraphQL schema.

#### Usage

```bash
s2dm export mongodb \
  --schema tests/data/spec/common.graphql \
  --schema my_schema.graphql \
  --output ./validators
```

This writes one file per object type into `./validators/`. For example, a schema with `ChargingStation` and `Address` types produces `ChargingStation.json` and `Address.json`.

#### Example

Given this schema:

```graphql
type ChargingStation {
  id:         ID!
  name:       String!
  maxPowerKw: Float!
  connectors: [ConnectorKind!]!
  address:    Address
}

type Address {
  street: String
  city:   String
}

enum ConnectorKind { TYPE_A TYPE_B TYPE_C }
```

The exporter produces `ChargingStation.json`:

```json
{
  "bsonType": "object",
  "additionalProperties": true,
  "properties": {
    "id":         { "bsonType": "objectId" },
    "name":       { "bsonType": "string" },
    "maxPowerKw": { "bsonType": "double" },
    "connectors": {
      "bsonType": "array",
      "items": { "bsonType": "string", "enum": ["TYPE_A", "TYPE_B", "TYPE_C"] }
    },
    "address": {
      "bsonType": ["object", "null"],
      "additionalProperties": true,
      "properties": {
        "street": { "bsonType": ["string", "null"] },
        "city":   { "bsonType": ["string", "null"] }
      }
    }
  },
  "required": ["id", "name", "maxPowerKw", "connectors"]
}
```

Key things to notice:

- `Address` is embedded directly inside `ChargingStation` — MongoDB validators work this way by design, there are no cross-collection references
- `ConnectorKind` is embedded as an allowed-values list
- Optional fields (no `!`) do not appear in `required` and accept `null`
- `additionalProperties: true` means extra fields beyond those in the schema are allowed by default

#### Restricting Extra Fields (`--properties-config`)

By default, documents may contain fields not defined in your schema. Use `--properties-config` to nominate specific types or embedded objects that should reject unknown fields.

Create a YAML file listing which objects should be strict:

```yaml
# strict.yaml
- ChargingStation           # the top-level ChargingStation collection
- ChargingStation.address   # only the embedded address inside ChargingStation
```

Then pass it to the exporter:

```bash
s2dm export mongodb \
  --schema tests/data/spec/common.graphql \
  --schema my_schema.graphql \
  --output ./validators \
  --properties-config strict.yaml
```

Each listed entry will have `additionalProperties: false` in its output. The two forms can be mixed freely:

- `TypeName` — applies to the top-level validator for that type
- `TypeName.fieldName` — applies only to the embedded object at that field; the standalone `TypeName` validator is not affected

If a name in the config does not match any type or field in your schema, the command exits with an error before writing anything.

#### Registering with MongoDB (`--validator`)

By default the output files contain the bare schema content. To produce files ready for direct use with `db.createCollection()`, add `--validator`:

```bash
s2dm export mongodb \
  --schema tests/data/spec/common.graphql \
  --schema my_schema.graphql \
  --output ./validators \
  --validator
```

Each file is then wrapped so you can pass it directly:

```js
const schema = require("./validators/ChargingStation.json");
db.createCollection("ChargingStation", { validator: schema });
```

Without `--validator`, the files contain the inner schema only — useful for version control, schema registries, or tooling that adds the envelope itself.

#### Filtering to a Single Type (`--root-type`)

Use `--root-type` to export only one type and have all dependent types inlined into it. This is useful when you need a single self-contained validator file:

```bash
s2dm export mongodb \
  --schema tests/data/spec/common.graphql \
  --schema my_schema.graphql \
  --output ./validators \
  --root-type ChargingStation
```

Only `ChargingStation.json` is written; `Address.json` is not created separately.

#### GeoJSON Fields

If your schema uses geographic coordinates, include the GeoJSON spec file and annotate fields with `@geoType`:

```bash
s2dm export mongodb \
  --schema tests/data/spec/common.graphql \
  --schema tests/data/spec/geojson.graphql \
  --schema my_schema.graphql \
  --output ./validators
```

```graphql
type ChargingStation {
  """Geographical location of the station"""
  location: GeoJSON! @geoType(shape: POINT)
}
```

The validator for `location` will enforce that the stored value is a valid GeoJSON Point object. Supported shapes: `POINT`, `MULTIPOINT`, `LINESTRING`, `MULTILINESTRING`, `POLYGON`, `MULTIPOLYGON`.

#### All Options

```bash
s2dm export mongodb --help
```
