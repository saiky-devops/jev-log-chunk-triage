"""Mock observability backend — simulates fetching logs from a scenario."""

from __future__ import annotations

from scenarios.loader import LogChunk, Scenario


class MockLogStore:
    """In-memory log store backed by scenario chunks (stand-in for Loki/Datadog)."""

    def __init__(self, scenario: Scenario):
        self.scenario = scenario
        self._chunks: list[LogChunk] = list(scenario.log_chunks)
        self._returned: set[str] = set()

    @property
    def total_chunks(self) -> int:
        return len(self._chunks)

    def fetch_logs(
        self,
        severity: str = "ALL",
        time_start: str = "",
        time_end: str = "",
        limit: int = 4,
    ) -> list[tuple[str, str, bool]]:
        """
        Return up to `limit` chunks matching filters.
        Each result is (chunk_id, content, is_signal).
        """
        severity = severity.upper()
        limit = max(1, min(limit, 8))
        matched: list[LogChunk] = []

        for chunk in self._chunks:
            if chunk.id in self._returned:
                continue
            if not self._matches_severity(chunk.content, severity):
                continue
            if time_start and not self._chunk_after(chunk.content, time_start):
                continue
            if time_end and not self._chunk_before(chunk.content, time_end):
                continue
            matched.append(chunk)

        selected = matched[:limit]
        for chunk in selected:
            self._returned.add(chunk.id)

        return [(c.id, c.content, c.is_signal) for c in selected]

    def remaining_count(self) -> int:
        return sum(1 for c in self._chunks if c.id not in self._returned)

    @staticmethod
    def _matches_severity(content: str, severity: str) -> bool:
        upper = content.upper()
        if severity == "ALL":
            return True
        if severity == "ERROR":
            return "ERROR" in upper or "FATAL" in upper
        if severity == "WARN":
            return "WARN" in upper
        if severity == "INFO":
            return "INFO" in upper or "DEBUG" in upper
        return True

    @staticmethod
    def _chunk_after(content: str, time_start: str) -> bool:
        """True if any line timestamp is >= time_start (string compare on ISO prefix)."""
        ts = time_start.strip()
        if not ts:
            return True
        for line in content.splitlines():
            if "T" in line[:30]:
                line_ts = line.split()[0] if line.split() else ""
                if line_ts >= ts:
                    return True
        return False

    @staticmethod
    def _chunk_before(content: str, time_end: str) -> bool:
        ts = time_end.strip()
        if not ts:
            return True
        for line in content.splitlines():
            if "T" in line[:30]:
                line_ts = line.split()[0] if line.split() else ""
                if line_ts <= ts:
                    return True
        return False
