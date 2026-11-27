"""Map columns of a CSV file to properties of a Health-RI model class, as specified by the user.

The user specifies the mapping in the configuration, as a table from the header of a CSV column to the name of a
property of the model, e.g.::

    [xds.column_mapping]
    "Beschrijving" = "description"
    "Trefwoorden" = "keyword"

The text in a cell is converted to the type of the property: lists are split on a separator, values of a
vocabulary (an enumeration) are looked up, and the model class itself converts the rest, like numbers and URLs.
"""

import logging
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Tuple, Type, Union, get_args, get_origin

import pandas as pd
from pydantic import AnyHttpUrl, BaseModel
from rdflib import URIRef
from sempyro import LiteralField

logger = logging.getLogger(__name__)

DEFAULT_LIST_SEPARATOR = ";"

# Types of which the model class reads a number, date or text from plain text itself
TEXT_READING_TYPES = (str, int, float, date, datetime)


class ColumnMappingError(ValueError):
    """The column mapping in the configuration cannot be used."""


def _members(annotation: Any) -> Tuple[bool, List[Any]]:
    """Return whether an annotation is a list, and the types that one value (or list item) can have."""
    types = list(get_args(annotation)) if get_origin(annotation) is Union else [annotation]
    is_list = any(get_origin(t) is list for t in types)
    members: List[Any] = []
    for t in types:
        if get_origin(t) is list:
            for item in get_args(t):
                members.extend(get_args(item) if get_origin(item) is Union else [item])
        elif t is not type(None):
            members.append(t)
    return is_list, members


def _is_model(member: Any) -> bool:
    """Whether a type is a class of its own, like a contact point, which a cell cannot fill.

    A literal (text with a language or datatype) is a class too, but the model class creates it from a text.
    """
    return isinstance(member, type) and issubclass(member, BaseModel) and not issubclass(member, LiteralField)


def _is_enum(member: Any) -> bool:
    return isinstance(member, type) and issubclass(member, Enum)


def _property_info(model: Type[BaseModel], property_name: str) -> Tuple[bool, List[Any]]:
    """Return whether the property is a list, and the types that one value (or list item) can have."""
    return _members(model.model_fields[property_name].annotation)


def validate_column_mapping(column_mapping: Dict[str, str], model: Type[BaseModel]) -> None:
    """Check that the properties in the column mapping can be filled from a single column.

    Raises
    ------
    ColumnMappingError
        If a property does not exist in the model, is a class of its own (like a contact point) that cannot be
        filled from one cell, or is filled from more than one column.
    """
    columns_per_property: Dict[str, str] = {}
    for column, property_name in column_mapping.items():
        if not isinstance(property_name, str) or property_name not in model.model_fields:
            raise ColumnMappingError(
                f"Column '{column}' is mapped to '{property_name}', which is not a property of {model.__name__}. "
                f"Properties: {', '.join(sorted(model.model_fields))}"
            )
        _, members = _members(model.model_fields[property_name].annotation)
        if members and all(_is_model(m) for m in members):
            raise ColumnMappingError(
                f"Column '{column}' is mapped to '{property_name}', which consists of other properties "
                "and cannot be filled from one column"
            )
        if property_name in columns_per_property:
            raise ColumnMappingError(
                f"Columns '{columns_per_property[property_name]}' and '{column}' are both mapped to '{property_name}'"
            )
        columns_per_property[property_name] = column


def _looks_like_url(text: str) -> bool:
    return text.lower().startswith(("http://", "https://"))


def _convert(value: str, members: List[Any]) -> Any:
    """Convert the text of a cell to a value that the property accepts.

    Values of a vocabulary (an enumeration) are looked up by their URI. A property that holds a literal and nothing
    that can read plain text (e.g. rights, which is a literal or a URL) gets a literal for text, and the URL as it is.
    The model class converts the rest (numbers, dates, URLs) and refuses what does not fit.
    """
    vocabulary = next((m for m in members if _is_enum(m)), None)
    if vocabulary is not None:
        try:
            return vocabulary(URIRef(value))
        except ValueError as e:
            allowed = ", ".join(str(member.value) for member in vocabulary)
            # repr() escapes control characters in the text of the cell, which would otherwise reach the terminal as is
            raise ValueError(f"{value!r} is not one of: {allowed}") from e
    if LiteralField in members and not any(m in TEXT_READING_TYPES for m in members):
        if AnyHttpUrl in members and _looks_like_url(value):
            return value
        return LiteralField(value=value)
    return value


def map_columns_to_properties(
    row: pd.Series,
    column_mapping: Dict[str, str],
    model: Type[BaseModel],
    list_separator: str = DEFAULT_LIST_SEPARATOR,
) -> Dict[str, Any]:
    """Read the mapped columns of a row as properties of the model.

    Columns that are not in the row, and empty cells, are left out, so that the properties they would fill keep
    their other value, e.g. from the configuration.

    Parameters
    ----------
    row : pd.Series
        A row of the CSV file.
    column_mapping : Dict[str, str]
        Header of a CSV column to the name of a property of the model, see :func:`validate_column_mapping`.
    model : Type[BaseModel]
        The model class with the properties.
    list_separator : str
        Separates the items in a cell for a property that is a list.

    Returns
    -------
    Dict[str, Any]
        The values per property, to be given as arguments to the model class.

    Raises
    ------
    ValueError
        If the text in a cell is not a value of the vocabulary of its property.
    """
    properties: Dict[str, Any] = {}
    for column, property_name in column_mapping.items():
        if column not in row.index or pd.isna(row[column]):
            continue
        text = str(row[column]).strip()
        if not text:
            continue
        is_list, members = _property_info(model, property_name)
        try:
            if is_list:
                properties[property_name] = [
                    _convert(item.strip(), members) for item in text.split(list_separator) if item.strip()
                ]
            else:
                properties[property_name] = _convert(text, members)
        except ValueError as e:
            raise ValueError(f"Column '{column}' (property '{property_name}'): {e}") from e
    return properties
