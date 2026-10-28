import {
	type DirectiveNode,
	extendSchema,
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

const pickArgumentDefinitions = PICK_ARGUMENT_NAMES.map(
	(argumentName) => `${argumentName}: [String!]`,
);
const PICK_DIRECTIVE_DEFINITION = `directive @${PICK_DIRECTIVE_NAME}(${pickArgumentDefinitions.join(", ")}) on QUERY`;

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
	operation: OperationDefinitionNode,
): DirectiveNode | undefined {
	return operation.directives?.find(
		(directive) => directive.name.value === PICK_DIRECTIVE_NAME,
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
