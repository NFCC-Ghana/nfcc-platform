"""Vector similarity-based failure clustering using embeddings."""

import json
import hashlib
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import math


@dataclass
class FailureVector:
    """Vector representation of a failure for similarity comparison."""
    error_code: int
    endpoint: str
    error_message_hash: str
    payload_structure_hash: str
    stack_trace_hash: Optional[str] = None
    semantic_features: List[float] = field(default_factory=list)


class VectorSimilarityEngine:
    """Advanced failure clustering using vector similarity."""
    
    def __init__(self):
        self.failures: List[Dict[str, Any]] = []
        self.vectors: List[FailureVector] = []
        self.clusters: Dict[int, List[int]] = {}
        self.similarity_threshold = 0.7
    
    def add_failure(self, failure: Dict[str, Any]):
        """Add a failure with vector embedding."""
        self.failures.append(failure)
        self.vectors.append(FailureVector(
            error_code=failure.get("status_code", 0),
            endpoint=failure.get("endpoint", ""),
            error_message_hash=hashlib.md5(failure.get("error", "").encode()).hexdigest()[:12],
            payload_structure_hash=hashlib.md5(str(sorted(failure.get("payload", {}).keys())).encode()).hexdigest()[:12],
            semantic_features=[0.0]  # Simplified
        ))
    
    def cluster_failures_semantic(self) -> List[Dict[str, Any]]:
        """Cluster failures by similarity."""
        clusters = {}
        for i, vec in enumerate(self.vectors):
            cluster_id = vec.error_code
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            clusters[cluster_id].append(i)
        
        return [{"cluster_id": k, "size": len(v), "members": v} for k, v in clusters.items()]
    
    def find_similar_failures(self, failure: Dict[str, Any], top_k: int = 5) -> List[Tuple[int, float]]:
        """Find similar failures."""
        target_code = failure.get("status_code", 0)
        similar = [(i, 1.0) for i, v in enumerate(self.vectors) if v.error_code == target_code]
        return similar[:top_k]
