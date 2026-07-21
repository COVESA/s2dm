"use strict";

const DocusaurusMDX = require("@graphql-markdown/docusaurus/mdx");
const {
  isObjectType,
  isInterfaceType,
  isEnumType,
  isNonNullType,
  isListType,
  getNamedType,
} = require("graphql");

/** True if the named type should become an arrow (object, interface, or enum). */
function isRelated(namedType) {
  return (
    isObjectType(namedType) ||
    isInterfaceType(namedType) ||
    isEnumType(namedType)
  );
}

/**
 * Determines the right-hand cardinality of a relation from the GraphQL field type.
 *   Type!      → "1"
 *   Type       → "0..1"
 *   [Type!]!   → "1..*"
 *   [Type]     → "0..*"
 */
function getCardinality(fieldType) {
  const isRequired = isNonNullType(fieldType);
  const inner = isRequired ? fieldType.ofType : fieldType;
  const isList = isListType(inner);
  if (isList) {
    return isRequired ? '"1..*"' : '"0..*"';
  }
  return isRequired ? '"1"' : '"0..1"';
}

/**
 * Injects a Mermaid classDiagram (left-to-right) into each object type page:
 * - Scalar fields appear as plain field names inside the class box.
 * - Enum, object, and interface fields become directed arrows with cardinality.
 * - Enum target boxes are annotated with <<enumeration>>.
 */
const beforeComposePageTypeHook = async (event) => {
  const { type } = event.data;

  if (!isObjectType(type)) return;

  const fields = Object.values(type.getFields());
  if (fields.length === 0) return;

  const scalarFields = fields.filter((f) => !isRelated(getNamedType(f.type)));
  const relatedFields = fields.filter((f) => isRelated(getNamedType(f.type)));

  const lines = ["classDiagram", "    direction LR"];

  // Class box — only rendered when there are scalar fields to show
  if (scalarFields.length > 0) {
    lines.push(`    class ${type.name} {`);
    for (const f of scalarFields) {
      // Plain field name — no type prefix avoids the unwanted "+" UML visibility marker
      lines.push(`        ${f.name}`);
    }
    lines.push("    }");
  }

  // Annotate each distinct enum target with <<enumeration>>
  const seenEnums = new Set();
  for (const f of relatedFields) {
    const named = getNamedType(f.type);
    if (isEnumType(named) && !seenEnums.has(named.name)) {
      seenEnums.add(named.name);
      lines.push(`    class ${named.name} {`);
      lines.push(`        <<enumeration>>`);
      lines.push(`    }`);
    }
  }

  // Arrows with cardinality for every related field
  for (const f of relatedFields) {
    const relatedType = getNamedType(f.type);
    const cardinality = getCardinality(f.type);
    lines.push(
      `    ${type.name} "1" --> ${cardinality} ${relatedType.name} : ${f.name}`,
    );
  }

  if (lines.length <= 1) return;

  const mermaidConfig =
    "---\nconfig:\n  class:\n    hideEmptyMembersBox: true\n---";
  const diagram =
    "```mermaid\n" + mermaidConfig + "\n" + lines.join("\n") + "\n```";

  event.data.sections["mermaidDiagram"] = { content: diagram };

  const codeIdx = event.output.indexOf("code");
  const descIdx = event.output.indexOf("description");
  const insertAfter = codeIdx > -1 ? codeIdx : descIdx > -1 ? descIdx : -1;

  if (insertAfter > -1) {
    event.output.splice(insertAfter + 1, 0, "mermaidDiagram");
  } else {
    event.output.unshift("mermaidDiagram");
  }
};

module.exports = {
  ...DocusaurusMDX,
  beforeComposePageTypeHook,
};
