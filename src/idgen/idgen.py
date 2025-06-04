import logging

from idgen.models import IDGenerationSpec

logger = logging.getLogger(__name__)


def fnv1_32_hash(identifier: bytes) -> int:
    """32-bit hash of a node according to Fowler-Noll-Vo

    @param identifier: a bytes representation of a node
    @return: hashed value for the node as int
    """
    id_hash = 2166136261
    for byte in identifier:
        id_hash = (id_hash * 16777619) & 0xFFFFFFFF
        id_hash ^= byte

    return id_hash


def fnv1_32_wrapper(field: IDGenerationSpec, strict_mode: bool) -> str:
    """A wrapper for the 32-bit hashing function if the input node
     is represented as dict instead of VSSNode

    @param node: Node object
    @param strict_mode: strict mode means case sensitivity of node qualified names
    @return: a string representation of the ID hash
    """
    return f"0x{format(fnv1_32_hash(field.get_node_identifier_bytes(strict_mode)), '08X')}"
