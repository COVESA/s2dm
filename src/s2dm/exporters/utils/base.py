import os
from pathlib import Path


def read_file(file_path: Path) -> str:
    """
    Read the content of a file.
    Args:
        file_path (str): The path to the file.
    Returns:
        str: The content of the file.
    Raises:
        Exception: If the file does not exist.
    """
    if not os.path.exists(file_path):
        raise Exception(f"The provided file does not exist: {file_path}")

    with open(file_path, encoding="utf-8") as file:
        return file.read()


def is_built_in_type(type_name: str) -> bool:
    return type_name.startswith("__") or type_name in {
        "String",
        "Int",
        "Float",
        "Boolean",
        "ID",
        "Query",
        "Mutation",
        "Subscription",
    }
