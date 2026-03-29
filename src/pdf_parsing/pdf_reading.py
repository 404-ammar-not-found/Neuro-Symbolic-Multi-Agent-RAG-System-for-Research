from pathlib import Path
from typing import Iterable, Optional

import fitz


class PdfReader:
    """Utility class for extracting text from PDF files."""

    def __init__(self, pdf_dir: Optional[Path | str] = None) -> None:
        self.pdf_dir = Path(pdf_dir) if pdf_dir else None

    def extract_text(
        self,
        pdf_path: Path | str,
        max_pages: int | None = None,
        log_every: int = 10,
    ) -> str:
        """
        Extract text from a single PDF file with optional page cap and progress logs.

        Args:
            pdf_path: Path to the PDF file.
            max_pages: Maximum pages to read; None reads all pages.
            log_every: Print progress every N pages (when > 0).

        Returns:
            Extracted text content. Returns an empty string on failure.
        """

        try:
            return "".join(
                self._iter_pages(pdf_path, max_pages=max_pages, log_every=log_every)
            )
        except Exception as exc:  # pragma: no cover - thin wrapper over library
            print(f"Error reading PDF {pdf_path}: {exc}")
            return ""

    def iter_text(
        self,
        pdf_path: Path | str,
        max_pages: int | None = None,
        log_every: int = 10,
    ):
        """Yield page-level text with optional cap and progress logs."""

        try:
            yield from self._iter_pages(
                pdf_path, max_pages=max_pages, log_every=log_every
            )
        except Exception as exc:  # pragma: no cover - thin wrapper over library
            print(f"Error reading PDF {pdf_path}: {exc}")

    def extract_texts(self, pdf_dir: Optional[Path | str] = None) -> list[str]:
        """
        Extract text from all PDF files in a directory.

        Args:
            pdf_dir: Directory containing PDF files. Falls back to the
                directory provided at initialization when omitted.

        Returns:
            List of extracted texts, one entry per PDF file.

        Raises:
            ValueError: If no directory is provided or configured.
        """

        target_dir = Path(pdf_dir) if pdf_dir else self.pdf_dir
        if target_dir is None:
            raise ValueError("PDF directory is not set.")

        pdf_files: Iterable[Path] = target_dir.glob("*.pdf")
        return [self.extract_text(pdf_file) for pdf_file in pdf_files]

    def _iter_pages(
        self,
        pdf_path: Path | str,
        max_pages: int | None = None,
        log_every: int = 10,
    ):
        """Yield page texts while logging progress."""

        with fitz.open(pdf_path) as document:
            total_pages = len(document)
            last_log = -1
            for index, page in enumerate(document):
                if max_pages is not None and index >= max_pages:
                    print(
                        f"  reached page limit ({max_pages}); stopping early for {pdf_path}"
                    )
                    break

                yield page.get_text("text")

                if log_every > 0:
                    current_page = index + 1
                    if current_page % log_every == 0 and current_page != last_log:
                        print(
                            f"  processed page {current_page}/{total_pages} of {Path(pdf_path).name}"
                        )
                        last_log = current_page