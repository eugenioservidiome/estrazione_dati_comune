"""Configuration management with dataclass, env, CLI, and YAML support."""

import os
import yaml
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional


@dataclass
class Config:
    """Configuration for comune_extractor pipeline."""
    
    # Target configuration
    base_url: str
    comune: str
    years: List[int] = field(default_factory=list)
    
    # Directories
    input_dir: Path = field(default_factory=lambda: Path("./input"))
    output_dir: Path = field(default_factory=lambda: Path("./output"))
    workspace: Path = field(default_factory=lambda: Path("./workspace"))
    
    # Crawler settings
    max_pages: int = 500
    max_pdfs: int = 2000
    respect_robots: bool = True
    crawl_delay: float = 1.0
    user_agent: str = "comune_extractor/2.0 (Educational/Research)"
    
    # Extraction settings
    concurrency_download: int = 8
    concurrency_extract: int = 4
    
    # Indexing settings
    top_k: int = 10
    min_score: float = 0.0
    
    # LLM settings (optional)
    use_llm: bool = False
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    llm_confidence_threshold: float = 0.7
    llm_max_chunks_per_doc: int = 3
    llm_max_docs: int = 3
    llm_chunk_size: int = 2000
    
    # External sources
    allow_external: bool = False
    
    def __post_init__(self):
        """Convert paths to Path objects and load env variables."""
        self.input_dir = Path(self.input_dir)
        self.output_dir = Path(self.output_dir)
        self.workspace = Path(self.workspace)
        
        # Load OpenAI key from env if not provided
        if self.use_llm and not self.openai_api_key:
            self.openai_api_key = os.getenv("OPENAI_API_KEY")
    
    @classmethod
    def from_yaml(cls, path: Path) -> "Config":
        """Load configuration from YAML file."""
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            base_url=os.getenv("COMUNE_BASE_URL", ""),
            comune=os.getenv("COMUNE_NAME", ""),
            years=[int(y) for y in os.getenv("COMUNE_YEARS", "").split(",") if y],
            input_dir=Path(os.getenv("COMUNE_INPUT_DIR", "./input")),
            output_dir=Path(os.getenv("COMUNE_OUTPUT_DIR", "./output")),
            workspace=Path(os.getenv("COMUNE_WORKSPACE", "./workspace")),
            max_pages=int(os.getenv("COMUNE_MAX_PAGES", "500")),
            max_pdfs=int(os.getenv("COMUNE_MAX_PDFS", "2000")),
            use_llm=os.getenv("COMUNE_USE_LLM", "").lower() == "true",
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        )
    
    def to_yaml(self, path: Path):
        """Save configuration to YAML file."""
        data = asdict(self)
        # Convert Path objects to strings
        data['input_dir'] = str(data['input_dir'])
        data['output_dir'] = str(data['output_dir'])
        data['workspace'] = str(data['workspace'])
        
        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
    
    @property
    def data_dir(self) -> Path:
        """Base data directory for all comune data."""
        return self.workspace / "data" / self.comune.lower()
    
    @property
    def catalog_path(self) -> Path:
        """Path to SQLite catalog database."""
        return self.data_dir / "catalog.sqlite"
    
    @property
    def index_dir(self) -> Path:
        """Directory for BM25 index files."""
        return self.data_dir / "index"
