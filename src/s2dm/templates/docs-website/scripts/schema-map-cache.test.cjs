const assert = require("node:assert/strict");
const path = require("node:path");
const { test } = require("node:test");
const { buildSchema, GraphQLObjectType } = require("graphql");
const { Printer } = require("@graphql-markdown/printer-legacy");

const graphqlDirectory = path.dirname(require.resolve("@graphql-markdown/graphql"));
const introspection = require(path.join(graphqlDirectory, "introspection.js"));
const printerDirectory = path.dirname(require.resolve("@graphql-markdown/printer-legacy"));
const { printRelations } = require(path.join(printerDirectory, "relation.js"));

test("builds one relation map for all pages without changing their relations", async (context) => {
  const schema = buildSchema(`
    interface Node { id: ID! }
    enum Color { RED BLUE }
    type Item implements Node { id: ID!, color: Color }
    type Basket { item: Item }
    type Query { item: Item, basket: Basket }
  `);
  Printer.options = undefined;
  await Printer.init(schema);
  const types = ["Node", "Color", "Item", "Basket", "ID"].map((name) => schema.getType(name));
  const expected = types.map((type) => printRelations(type, Printer.options));
  assert.match(expected[2], /Returned By/);
  assert.match(expected[2], /Member Of/);
  assert.match(expected[0], /Implemented By/);

  const schemaMap = context.mock.method(introspection, "getSchemaMap");
  const actual = types.map((type) => Printer.printRelations(type, Printer.options));
  assert.deepEqual(actual, expected);
  assert.equal(schemaMap.mock.callCount(), 1);
});

test("keeps relation maps separate for different schema objects", async () => {
  const first = buildSchema(`
    type Item { id: ID }
    type FirstOwner { item: Item }
    type Query { item: Item }
  `);
  const second = buildSchema(`
    type Item { id: ID }
    type SecondOwner { item: Item }
    type Query { item: Item }
  `);
  Printer.options = undefined;
  await Printer.init(first);

  const firstOutput = Printer.printRelations(first.getType("Item"), Printer.options);
  const secondOutput = Printer.printRelations(second.getType("Item"), {
    ...Printer.options,
    schema: second,
  });
  assert.match(firstOutput, /FirstOwner/);
  assert.doesNotMatch(firstOutput, /SecondOwner/);
  assert.match(secondOutput, /SecondOwner/);
  assert.doesNotMatch(secondOutput, /FirstOwner/);
});

test("rebuilds the map on initialization even when the schema object is reused", async (context) => {
  const schema = buildSchema(`
    type Item { id: ID }
    type Query { item: Item }
  `);
  Printer.options = undefined;
  await Printer.init(schema);
  const schemaMap = context.mock.method(introspection, "getSchemaMap");
  const before = Printer.printRelations(schema.getType("Item"), Printer.options);
  assert.doesNotMatch(before, /NewOwner/);

  // Simulate a caller extending the same schema between documentation generations.
  schema.getTypeMap().NewOwner = new GraphQLObjectType({
    name: "NewOwner",
    fields: { item: { type: schema.getType("Item") } },
  });
  await Printer.init(schema);
  const after = Printer.printRelations(schema.getType("Item"), Printer.options);
  assert.match(after, /NewOwner/);
  assert.equal(schemaMap.mock.callCount(), 2);
});
