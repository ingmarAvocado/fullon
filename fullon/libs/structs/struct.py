"""
Parent instance of fullon structs.
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List

@dataclass
class Struct:

    @classmethod
    def from_dict(cls, symbol_dict: Dict[str, Any]) -> Any:
        """
        Convert a dictionary to a SymbolStruct object.

        Args:
            symbol_dict (Dict[str, Any]): A dictionary representing a SymbolStruct object.

        Returns:
            Any: A Struct object created from the dictionary.
        """
        attributes = {}
        for k, v in symbol_dict.items():
            if isinstance(v, (int, float, str)):
                attributes[k] = v
            else:
                attributes[k] = v

        return cls(**attributes)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert a SymbolStruct object to a dictionary.

        Args:
            upper (bool): If True, all keys in the dictionary will be in uppercase.

        Returns:
            Dict[str, Any]: A dictionary representation of the SymbolStruct object.
        """
        return asdict(self)
