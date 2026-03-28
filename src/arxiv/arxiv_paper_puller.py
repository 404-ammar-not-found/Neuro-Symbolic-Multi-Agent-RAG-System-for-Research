import arxiv 
import requests
from dotenv import load_dotenv
import openrouter 

load_dotenv()
STORAGE_DIR = os.getenv("STORAGE_DIR")

class ArxivPaperPuller:
    def __init__(self, query, storage_dir = STORAGE_DIR):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.metadata_file = self.storage_dir / "metadata.jsonl"

    def construct_pdf_url(self, arxiv_id):
        """
        arxiv_id format: 2401.12345 or 2401.12345v2
        PDF URL: https://arxiv.org/pdf/2401.12345.pdf
        """
        clean_id = arxiv_id.split('v')[0]  # Remove version suffix
        return f"https://arxiv.org/pdf/{clean_id}.pdf"
