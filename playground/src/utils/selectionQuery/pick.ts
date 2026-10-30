import {
	type ArgumentNode,
	type DirectiveNode,
	extendSchema,
	type FieldNode,
	type GraphQLSchema,
	isEnumType,
	isIntrospectionType,
	isScalarType,
	isSpecifiedDirective,
	isSpecifiedScalarType,
	Kind,
	type OperationDefinitionNode,
	parse,
	type StringValueNode,
	type ValueNode,
} from "graphql";

export const PICK_DIRECTIVE_NAME = "pick";

export const PICK_ARGUMENT_NAMES = ["enums", "scalars", "directives"] as const;

export type PickArgumentName = (typeof PICK_ARGUMENT_NAMES)[number];

export type PickGroup = {
	argumentName: PickArgumentName;
	names: string[];
};

const pickGroupArgumentDefinitions = PICK_ARGUMENT_NAMES.map(
	(argumentName) => `${argumentName}: [String!]`,
);
// The field-level form, which picks instances on an instance tag field. It is not a selection tree
// group, so it stays out of PICK_ARGUMENT_NAMES.
export const PICK_INSTANCES_ARGUMENT_NAME = "instances";
const PICK_INSTANCES_ARGUMENT_DEFINITION = `${PICK_INSTANCES_ARGUMENT_NAME}: [String!]`;
const pickArgumentDefinitions = [
	...pickGroupArgumentDefinitions,
	PICK_INSTANCES_ARGUMENT_DEFINITION,
];
const PICK_DIRECTIVE_DEFINITION = `directive @${PICK_DIRECTIVE_NAME}(${pickArgumentDefinitions.join(", ")}) on QUERY | FIELD`;

/**
 * Declares the `@pick` directive on a schema that lacks it, so selection
 * queries that use it pass validation.
 *
 * @param schema The schema.
 * @returns The schema itself when it already declares `@pick`, otherwise an
 * extended copy.
 */
export function withPickDirective(schema: GraphQLSchema): GraphQLSchema {
	if (schema.getDirective(PICK_DIRECTIVE_NAME)) {
		return schema;
	}

	const pickDirectiveDocument = parse(PICK_DIRECTIVE_DEFINITION);
	return extendSchema(schema, pickDirectiveDocument);
}

export function findPickDirective(
	node: OperationDefinitionNode | FieldNode,
): DirectiveNode | undefined {
	return node.directives?.find(
		(directive) => directive.name.value === PICK_DIRECTIVE_NAME,
	);
}

export function findPickArgument(
	node: OperationDefinitionNode | FieldNode,
	argumentName: string,
): ArgumentNode | undefined {
	const pickDirective = findPickDirective(node);
	return pickDirective?.arguments?.find(
		(argument) => argument.name.value === argumentName,
	);
}

/**
 * Lists the string items of an argument value. A single string counts as a
 * one-item list, as GraphQL input coercion allows.
 *
 * @param value The argument value.
 * @returns The string items; empty for any other kind of value.
 */
export function getStringValues(value: ValueNode): StringValueNode[] {
	if (value.kind === Kind.STRING) {
		return [value];
	}

	if (value.kind !== Kind.LIST) {
		return [];
	}

	return value.values.filter(
		(item): item is StringValueNode => item.kind === Kind.STRING,
	);
}

/**
 * Reads the names listed in each argument of an operation's `@pick` directive.
 * Arguments whose value is neither a string nor a list are skipped.
 *
 * @param operation The query operation.
 * @returns The listed names by argument name; an empty set stands for an
 * empty list, which picks every name. Empty when there is no `@pick`.
 */
export function readListedNames(
	operation: OperationDefinitionNode,
): Map<string, Set<string>> {
	const listedNamesByArgument = new Map<string, Set<string>>();
	const pickDirective = findPickDirective(operation);
	for (const argument of pickDirective?.arguments ?? []) {
		const { value } = argument;
		if (value.kind !== Kind.STRING && value.kind !== Kind.LIST) {
			continue;
		}
		const stringValues = getStringValues(value);
		const names = stringValues.map((stringValue) => stringValue.value);
		listedNamesByArgument.set(argument.name.value, new Set(names));
	}

	return listedNamesByArgument;
}

/**
 * Resolves which names a `@pick` argument picks, expanding an empty list to
 * every pickable name.
 *
 * @param listedNamesByArgument The listed names, as read from the text.
 * @param argumentName The `@pick` argument.
 * @param pickableNames Every name the argument can take.
 * @returns The picked names; empty when the argument is absent.
 */
export function resolvePickedNames(
	listedNamesByArgument: Map<string, Set<string>>,
	argumentName: PickArgumentName,
	pickableNames: string[],
): Set<string> {
	const listedNames = listedNamesByArgument.get(argumentName);
	if (!listedNames) {
		return new Set();
	}

	if (listedNames.size === 0) {
		return new Set(pickableNames);
	}

	return listedNames;
}

/**
 * Reads the names listed in the `instances` argument of a field's `@pick`.
 *
 * @param field The query field.
 * @returns The listed names; `undefined` when the field has no `@pick` or its
 * `@pick` has no `instances` argument.
 */
export function readListedInstances(field: FieldNode): Set<string> | undefined {
	const instancesArgument = findPickArgument(
		field,
		PICK_INSTANCES_ARGUMENT_NAME,
	);
	if (!instancesArgument) {
		return undefined;
	}

	const stringValues = getStringValues(instancesArgument.value);
	const names = stringValues.map((stringValue) => stringValue.value);
	return new Set(names);
}

/**
 * Resolves which instances, or dimension values, a field-level `@pick` keeps.
 * Unlike the query-level arguments, a field without `@pick` keeps everything.
 *
 * @param listedNames The listed names; `undefined` when the field has no
 * `@pick`.
 * @param pickableNames Every name the field can take.
 * @returns The kept names; every pickable name when the list is missing or
 * empty.
 */
export function resolveFieldPickedNames(
	listedNames: Set<string> | undefined,
	pickableNames: string[],
): Set<string> {
	if (!listedNames || listedNames.size === 0) {
		return new Set(pickableNames);
	}

	return listedNames;
}

/**
 * Applies a toggle to the picked names.
 *
 * @param pickableNames Every name that can be picked, in display order.
 * @param pickedNames The names picked now.
 * @param toggledNames The names to toggle.
 * @param isChecked Whether the names are being picked or unpicked.
 * @returns The names picked after the toggle, in display order.
 */
export function toggleNames(
	pickableNames: string[],
	pickedNames: Set<string>,
	toggledNames: string[],
	isChecked: boolean,
): string[] {
	return pickableNames.filter((name) => {
		if (toggledNames.includes(name)) {
			return isChecked;
		}
		return pickedNames.has(name);
	});
}

/**
 * Lists the schema's names that a `@pick` argument can take, leaving out the
 * built-in scalars, directives and introspection types.
 *
 * @param schema The schema.
 * @param argumentName The `@pick` argument.
 * @returns The names, sorted alphabetically.
 */
export function getPickableNames(
	schema: GraphQLSchema,
	argumentName: PickArgumentName,
): string[] {
	let names: string[];
	if (argumentName === "directives") {
		const directives = schema.getDirectives();
		const customDirectives = directives.filter(
			(directive) =>
				!isSpecifiedDirective(directive) &&
				directive.name !== PICK_DIRECTIVE_NAME,
		);
		names = customDirectives.map((directive) => directive.name);
	} else {
		const typeMap = schema.getTypeMap();
		const types = Object.values(typeMap);
		const pickableTypes = types.filter((type) => {
			if (isIntrospectionType(type)) {
				return false;
			}
			if (argumentName === "enums") {
				return isEnumType(type);
			}
			return isScalarType(type) && !isSpecifiedScalarType(type);
		});
		names = pickableTypes.map((type) => type.name);
	}

	return names.sort((first, second) => first.localeCompare(second));
}
