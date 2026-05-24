"""Async load engine for high-concurrency testing."""

import asyncio
import aiohttp
import time
import statistics
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class AsyncLoadResult:
    """Async load test result."""
    timestamp: float
    concurrent_users: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    rps: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    error_rate: float


class AsyncLoadEngine:
    """Async load testing with asyncio for high concurrency."""
    
    def __init__(self, base_url: str = "http://testserver"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _create_session(self):
        """Create aiohttp session."""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def _close_session(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> tuple:
        """Make single async request."""
        start = time.time()
        try:
            async with self.session.post(f"{self.base_url}{endpoint}", json=payload) as response:
                latency = (time.time() - start) * 1000
                status = response.status
                return status, latency, None
        except Exception as e:
            latency = (time.time() - start) * 1000
            return 0, latency, str(e)
    
    async def run_load_test(self, endpoint: str, payload: Dict[str, Any],
                            concurrent_users: int, duration_seconds: float,
                            target_rps: Optional[float] = None) -> AsyncLoadResult:
        """Run async load test with specified concurrency."""
        await self._create_session()
        
        results = []
        latencies = []
        errors = 0
        successes = 0
        
        # Calculate delay between request batches
        delay = 1.0 / target_rps if target_rps else 0
        
        async def worker():
            nonlocal successes, errors
            end_time = time.time() + duration_seconds
            while time.time() < end_time:
                status, latency, error = await self._make_request(endpoint, payload)
                latencies.append(latency)
                if status and 200 <= status < 500:
                    successes += 1
                else:
                    errors += 1
                if delay > 0:
                    await asyncio.sleep(delay)
        
        start_time = time.time()
        tasks = [asyncio.create_task(worker()) for _ in range(concurrent_users)]
        await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        await self._close_session()
        
        total_requests = successes + errors
        rps = total_requests / total_time if total_time > 0 else 0
        
        latencies_sorted = sorted(latencies) if latencies else [0]
        
        return AsyncLoadResult(
            timestamp=time.time(),
            concurrent_users=concurrent_users,
            total_requests=total_requests,
            successful_requests=successes,
            failed_requests=errors,
            rps=round(rps, 2),
            p50_latency_ms=round(statistics.median(latencies_sorted), 2) if latencies else 0,
            p95_latency_ms=round(latencies_sorted[int(len(latencies_sorted) * 0.95)], 2) if latencies else 0,
            p99_latency_ms=round(latencies_sorted[int(len(latencies_sorted) * 0.99)], 2) if latencies else 0,
            error_rate=round(errors / total_requests * 100, 2) if total_requests > 0 else 0
        )
    
    async def run_ramp_test(self, endpoint: str, payload: Dict[str, Any],
                            start_users: int, end_users: int, step: int,
                            duration_per_step: float) -> List[AsyncLoadResult]:
        """Run ramp-up load test."""
        results = []
        for users in range(start_users, end_users + 1, step):
            result = await self.run_load_test(endpoint, payload, users, duration_per_step)
            results.append(result)
            await asyncio.sleep(1)  # Cooldown between steps
        return results
    
    async def run_spike_test(self, endpoint: str, payload: Dict[str, Any],
                             base_users: int, spike_users: int,
                             spike_duration: float, recovery_duration: float) -> List[AsyncLoadResult]:
        """Run spike load test."""
        results = []
        
        # Baseline
        baseline = await self.run_load_test(endpoint, payload, base_users, 30)
        results.append(baseline)
        
        # Spike
        spike = await self.run_load_test(endpoint, payload, spike_users, spike_duration)
        results.append(spike)
        
        # Recovery
        recovery = await self.run_load_test(endpoint, payload, base_users, recovery_duration)
        results.append(recovery)
        
        return results
    
    def run_sync_wrapper(self, endpoint: str, payload: Dict[str, Any],
                         concurrent_users: int, duration_seconds: float) -> AsyncLoadResult:
        """Synchronous wrapper for async load test."""
        return asyncio.run(self.run_load_test(endpoint, payload, concurrent_users, duration_seconds))
