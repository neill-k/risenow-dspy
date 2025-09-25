"""Log all Tavily search results to flat files for persistence and debugging."""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import hashlib


class SourceLogger:
    """Log all Tavily results to flat files for persistence and debugging."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or self._generate_session_id()
        self.base_dir = Path(f"data/sources/{self.session_id}")
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Track file handles for efficiency (optional, currently using append mode)
        self.file_handles = {}

    def _generate_session_id(self) -> str:
        """Generate unique session ID based on timestamp."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def log_tavily_results(self,
                          results: List[Dict],
                          query: str,
                          tool_name: str,
                          agent_name: str) -> None:
        """Append Tavily results to appropriate flat file.

        Parameters
        ----------
        results : List[Dict]
            List of Tavily search/extract results
        query : str
            The search query or extraction request
        tool_name : str
            Name of the tool (tavily_search, tavily_extract, etc.)
        agent_name : str
            Name of the calling agent (vendor_agent, pestle_agent, etc.)
        """

        # Create file for this agent/tool combination
        file_key = f"{agent_name}_{tool_name}"
        file_path = self.base_dir / f"{file_key}.jsonl"

        # Write each result as a JSONL line
        with open(file_path, 'a', encoding='utf-8') as f:
            for result in results:
                record = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'query': query,
                    'tool': tool_name,
                    'agent': agent_name,
                    'url': result.get('url', ''),
                    'title': result.get('title', ''),
                    'content': result.get('content', result.get('snippet', '')),
                    'raw_result': result  # Keep full original for debugging
                }
                f.write(json.dumps(record, ensure_ascii=False) + '\n')

    def read_all_sources(self) -> List[Dict]:
        """Read all sources from flat files for this session.

        Returns
        -------
        List[Dict]
            All logged sources from all agents/tools
        """
        all_sources = []

        # Read all JSONL files in session directory
        for jsonl_file in self.base_dir.glob("*.jsonl"):
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            all_sources.append(json.loads(line))
                        except json.JSONDecodeError as e:
                            print(f"Warning: Failed to parse line in {jsonl_file}: {e}")
                            continue

        return all_sources

    def get_session_manifest(self) -> Dict:
        """Get summary of logged sources.

        Returns
        -------
        Dict
            Summary with session_id, file counts, and total sources
        """
        manifest = {
            'session_id': self.session_id,
            'directory': str(self.base_dir),
            'files': {},
            'total_sources': 0
        }

        for jsonl_file in self.base_dir.glob("*.jsonl"):
            line_count = sum(1 for _ in open(jsonl_file))
            manifest['files'][jsonl_file.name] = line_count
            manifest['total_sources'] += line_count

        return manifest

    def read_sources_by_agent(self, agent_name: str) -> List[Dict]:
        """Read sources for a specific agent.

        Parameters
        ----------
        agent_name : str
            Name of the agent to filter by

        Returns
        -------
        List[Dict]
            Sources logged by the specified agent
        """
        agent_sources = []

        # Read files matching this agent
        for jsonl_file in self.base_dir.glob(f"{agent_name}_*.jsonl"):
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            agent_sources.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue

        return agent_sources


# Global logger instance (singleton pattern)
_global_logger: Optional[SourceLogger] = None


def get_source_logger(session_id: Optional[str] = None) -> SourceLogger:
    """Get or create the global source logger.

    Parameters
    ----------
    session_id : str, optional
        Session ID for the logger. Only used when creating new logger.

    Returns
    -------
    SourceLogger
        The global source logger instance
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = SourceLogger(session_id)
    return _global_logger


def reset_source_logger(session_id: Optional[str] = None) -> SourceLogger:
    """Reset logger for new session.

    Parameters
    ----------
    session_id : str, optional
        Session ID for the new logger

    Returns
    -------
    SourceLogger
        The newly created source logger instance
    """
    global _global_logger
    _global_logger = SourceLogger(session_id)
    return _global_logger