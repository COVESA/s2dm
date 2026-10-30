"""Names of the GraphQL directives and arguments used across the tool."""

from enum import Enum


class Directive(str, Enum):
    """Names of the custom GraphQL directives used across the tool."""

    INSTANCE_TAG = "instanceTag"
    RANGE = "range"
    CARDINALITY = "cardinality"
    NO_DUPLICATES = "noDuplicates"
    METADATA = "metadata"
    REFERENCE = "reference"
    VSPEC = "vspec"
    MODL = "modl"
    PICK = "pick"


class BuiltInDirective(str, Enum):
    """Names of the built-in GraphQL directives the tool reasons about."""

    DEPRECATED = "deprecated"
    SPECIFIED_BY = "specifiedBy"


class DirectiveArgument(str, Enum):
    """Names of the arguments accepted by the directives the tool reads."""

    EXCLUDE = "exclude"
    MIN = "min"
    MAX = "max"
    COMMENT = "comment"
    VSS_TYPE = "vssType"
    URI = "uri"
    SOURCE = "source"
    ELEMENT = "element"
    METADATA = "metadata"
    CONCEPT = "concept"
    CONTRACT = "contract"
