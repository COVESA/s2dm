from typing import cast

from graphql import parse
from graphql.language.ast import DirectiveDefinitionNode, ScalarTypeDefinitionNode

from s2dm.utils import schema_definitions


def test_required_input_value_definition_uses_non_null_without_default() -> None:
    document = parse(
        """
        directive @meta(
          required: String!
          nonNullWithDefault: String! = "fallback"
          optional: String
        ) on FIELD_DEFINITION
        """
    )
    directive = cast(DirectiveDefinitionNode, document.definitions[0])
    assert directive.arguments is not None
    arguments = {argument.name.value: argument for argument in directive.arguments}

    assert schema_definitions.is_required_input_value_definition(arguments["required"])
    assert not schema_definitions.is_required_input_value_definition(arguments["nonNullWithDefault"])
    assert not schema_definitions.is_required_input_value_definition(arguments["optional"])


def test_directive_definition_superset_allows_optional_added_arguments_and_locations() -> None:
    subset_document = parse("directive @meta(comment: String) on FIELD_DEFINITION")
    superset_document = parse("directive @meta(comment: String, source: String) on FIELD_DEFINITION | OBJECT")
    subset = cast(DirectiveDefinitionNode, subset_document.definitions[0])
    superset = cast(DirectiveDefinitionNode, superset_document.definitions[0])

    assert schema_definitions.is_directive_definition_superset(superset, subset)
    assert not schema_definitions.is_directive_definition_superset(subset, superset)


def test_directive_definition_superset_rejects_required_added_arguments() -> None:
    subset_document = parse("directive @meta(comment: String) on FIELD_DEFINITION")
    candidate_document = parse("directive @meta(comment: String, source: String!) on FIELD_DEFINITION")
    subset = cast(DirectiveDefinitionNode, subset_document.definitions[0])
    candidate = cast(DirectiveDefinitionNode, candidate_document.definitions[0])

    assert not schema_definitions.is_directive_definition_superset(candidate, subset)


def test_scalar_definition_superset_compares_applied_directive_arguments() -> None:
    subset_document = parse(
        """
        directive @format(value: String!) on SCALAR
        scalar DateTime @format(value: "iso")
        """
    )
    superset_document = parse(
        """
        directive @format(value: String!, source: String) on SCALAR
        scalar DateTime @format(value: "iso", source: "system")
        """
    )
    conflicting_document = parse(
        """
        directive @format(value: String!) on SCALAR
        scalar DateTime @format(value: "epoch")
        """
    )
    subset = cast(ScalarTypeDefinitionNode, subset_document.definitions[1])
    superset = cast(ScalarTypeDefinitionNode, superset_document.definitions[1])
    conflicting = cast(ScalarTypeDefinitionNode, conflicting_document.definitions[1])

    assert schema_definitions.is_scalar_definition_superset(superset, subset)
    assert not schema_definitions.is_scalar_definition_superset(conflicting, subset)
