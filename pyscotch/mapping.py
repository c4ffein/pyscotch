"""
Mapping class for PT-Scotch mapping operations.
"""

import numpy as np
from pathlib import Path
from typing import Union


class Mapping:
    """
    Represents a mapping of graph vertices to architecture domains.

    A mapping assigns each vertex of a source graph to a domain of a target
    architecture, typically used for domain decomposition and load balancing.
    """

    def __init__(self, mapping_array: np.ndarray):
        """
        Initialize a mapping from an array.

        Args:
            mapping_array: Array of domain assignments for each vertex

        Raises:
            ValueError: If mapping_array is empty or contains negative values
        """
        if len(mapping_array) == 0:
            raise ValueError("mapping_array cannot be empty")

        self.mapping = np.asarray(mapping_array, dtype=np.int64)

        if np.any(self.mapping < 0):
            raise ValueError("mapping_array cannot contain negative domain values")

        self.size = len(self.mapping)

    def save(self, filename: Union[str, Path]) -> None:
        """
        Save the mapping to a file.

        Args:
            filename: Output file path
        """
        filename = Path(filename)
        with open(filename, "w") as f:
            f.write(f"{self.size}\n")
            for i, domain in enumerate(self.mapping):
                f.write(f"{i}\t{domain}\n")

    @staticmethod
    def load(filename: Union[str, Path]) -> "Mapping":
        """
        Load a mapping from a file.

        Args:
            filename: Path to the mapping file

        Returns:
            New Mapping instance

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        filename = Path(filename)
        if not filename.exists():
            raise FileNotFoundError(f"Mapping file not found: {filename}")

        with open(filename, "r") as f:
            lines = f.readlines()
            size = int(lines[0].strip())
            mapping = np.zeros(size, dtype=np.int64)

            for line in lines[1:]:
                if line.strip():
                    parts = line.strip().split()
                    idx = int(parts[0])
                    domain = int(parts[1])
                    mapping[idx] = domain

        return Mapping(mapping)

    def get_partition_sizes(self) -> np.ndarray:
        """
        Get the size of each partition.

        Returns:
            Array of partition sizes
        """
        num_parts = int(np.max(self.mapping)) + 1
        sizes = np.zeros(num_parts, dtype=np.int64)
        for domain in self.mapping:
            sizes[domain] += 1
        return sizes

    def get_partition(self, domain: int) -> np.ndarray:
        """
        Get the vertices assigned to a specific domain.

        Args:
            domain: Domain index

        Returns:
            Array of vertex indices in the domain

        Raises:
            ValueError: If domain is invalid
        """
        if domain < 0:
            raise ValueError(f"domain must be non-negative, got {domain}")

        max_domain = int(np.max(self.mapping))
        if domain > max_domain:
            raise ValueError(
                f"domain {domain} exceeds maximum domain {max_domain}"
            )

        return np.where(self.mapping == domain)[0]

    def num_partitions(self) -> int:
        """
        Get the number of partitions.

        Returns:
            Number of distinct partitions
        """
        return int(np.max(self.mapping)) + 1

    def balance(self) -> float:
        """
        Compute the load balance of the mapping.

        Returns:
            Balance ratio (max_size / avg_size)
        """
        sizes = self.get_partition_sizes()
        avg_size = np.mean(sizes)
        max_size = np.max(sizes)
        return float(max_size / avg_size) if avg_size > 0 else 0.0

    def __len__(self) -> int:
        """Get the size of the mapping."""
        return self.size

    def __getitem__(self, idx: int) -> int:
        """Get the domain assignment for a vertex."""
        return int(self.mapping[idx])

    def __repr__(self) -> str:
        """String representation of the mapping."""
        return f"Mapping(size={self.size}, num_partitions={self.num_partitions()}, balance={self.balance():.3f})"
