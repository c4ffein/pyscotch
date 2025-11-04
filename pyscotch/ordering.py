"""
Ordering class for PT-Scotch ordering operations.
"""

import numpy as np
from pathlib import Path
from typing import Union, Tuple, Optional


class Ordering:
    """
    Represents an ordering of graph vertices.

    An ordering is a permutation of vertices, typically used for sparse matrix
    factorization to reduce fill-in.
    """

    def __init__(self, permutation: np.ndarray, inverse_permutation: Optional[np.ndarray] = None):
        """
        Initialize an ordering from permutation arrays.

        Args:
            permutation: Forward permutation (new_pos = perm[old_pos])
            inverse_permutation: Inverse permutation (old_pos = invp[new_pos])
        """
        self.permutation = np.asarray(permutation, dtype=np.int64)
        self.size = len(self.permutation)

        if inverse_permutation is not None:
            self.inverse_permutation = np.asarray(inverse_permutation, dtype=np.int64)
        else:
            # Compute inverse if not provided
            self.inverse_permutation = np.zeros(self.size, dtype=np.int64)
            for i, p in enumerate(self.permutation):
                self.inverse_permutation[p] = i

    def save(self, filename: Union[str, Path]) -> None:
        """
        Save the ordering to a file.

        Args:
            filename: Output file path
        """
        filename = Path(filename)
        with open(filename, "w") as f:
            f.write(f"{self.size}\n")
            for i in range(self.size):
                f.write(f"{i}\t{self.permutation[i]}\t{self.inverse_permutation[i]}\n")

    @staticmethod
    def load(filename: Union[str, Path]) -> "Ordering":
        """
        Load an ordering from a file.

        Args:
            filename: Path to the ordering file

        Returns:
            New Ordering instance

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        filename = Path(filename)
        if not filename.exists():
            raise FileNotFoundError(f"Ordering file not found: {filename}")

        with open(filename, "r") as f:
            lines = f.readlines()
            size = int(lines[0].strip())
            permutation = np.zeros(size, dtype=np.int64)
            inverse_permutation = np.zeros(size, dtype=np.int64)

            for line in lines[1:]:
                if line.strip():
                    parts = line.strip().split()
                    idx = int(parts[0])
                    perm_val = int(parts[1])
                    inv_val = int(parts[2])
                    permutation[idx] = perm_val
                    inverse_permutation[idx] = inv_val

        return Ordering(permutation, inverse_permutation)

    def apply(self, array: np.ndarray) -> np.ndarray:
        """
        Apply the ordering to an array.

        Args:
            array: Input array to reorder

        Returns:
            Reordered array
        """
        return array[self.permutation]

    def apply_inverse(self, array: np.ndarray) -> np.ndarray:
        """
        Apply the inverse ordering to an array.

        Args:
            array: Input array to reorder

        Returns:
            Reordered array using inverse permutation
        """
        return array[self.inverse_permutation]

    def __len__(self) -> int:
        """Get the size of the ordering."""
        return self.size

    def __getitem__(self, idx: int) -> int:
        """Get the permutation value for an index."""
        return int(self.permutation[idx])

    def __repr__(self) -> str:
        """String representation of the ordering."""
        return f"Ordering(size={self.size})"
