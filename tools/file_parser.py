"""File parser for extracting text from uploaded documents."""
import os
import csv
import io

# Max chars to extract from a file to avoid blowing context window
MAX_FILE_CHARS = 6000


def parse_file(filepath: str, filename: str) -> dict:
    """
    Parse an uploaded file and return structured text content.
    Returns: {"filename": str, "type": str, "content": str, "error": str|None}
    """
    ext = os.path.splitext(filename)[1].lower()

    try:
        if ext in (".csv",):
            return _parse_csv(filepath, filename)
        elif ext in (".txt", ".md", ".log"):
            return _parse_text(filepath, filename)
        elif ext in (".json",):
            return _parse_json(filepath, filename)
        elif ext in (".pdf",):
            return _parse_pdf(filepath, filename)
        elif ext in (".xlsx", ".xls"):
            return _parse_excel(filepath, filename)
        elif ext in (".docx",):
            return _parse_docx(filepath, filename)
        else:
            return {"filename": filename, "type": ext, "content": "",
                    "error": f"Unsupported file type: {ext}. Supported: CSV, TXT, JSON, PDF, XLSX, DOCX"}
    except Exception as e:
        return {"filename": filename, "type": ext, "content": "",
                "error": f"Error parsing {filename}: {str(e)}"}


def _parse_csv(filepath: str, filename: str) -> dict:
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        return {"filename": filename, "type": "csv", "content": "Empty CSV file.", "error": None}

    # Format as readable table
    lines = []
    headers = rows[0]
    lines.append(" | ".join(headers))
    lines.append("-" * len(lines[0]))
    for row in rows[1:]:
        lines.append(" | ".join(row))

    content = "\n".join(lines)
    if len(content) > MAX_FILE_CHARS:
        # Show row count and truncate
        content = content[:MAX_FILE_CHARS] + f"\n... [truncated, {len(rows)-1} total rows]"

    return {"filename": filename, "type": "csv", "content": content, "error": None}


def _parse_text(filepath: str, filename: str) -> dict:
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read(MAX_FILE_CHARS + 100)

    if len(content) > MAX_FILE_CHARS:
        content = content[:MAX_FILE_CHARS] + "\n... [truncated]"

    return {"filename": filename, "type": "text", "content": content, "error": None}


def _parse_json(filepath: str, filename: str) -> dict:
    import json
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read(MAX_FILE_CHARS * 2)

    try:
        data = json.loads(raw)
        content = json.dumps(data, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        content = raw

    if len(content) > MAX_FILE_CHARS:
        content = content[:MAX_FILE_CHARS] + "\n... [truncated]"

    return {"filename": filename, "type": "json", "content": content, "error": None}


def _parse_pdf(filepath: str, filename: str) -> dict:
    """Parse PDF using PyMuPDF (fitz) — fast, handles tables and scanned text better."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        # Fallback chain: pdfplumber → PyPDF2
        try:
            import pdfplumber
            text_parts = []
            with pdfplumber.open(filepath) as pdf:
                for i, page in enumerate(pdf.pages):
                    if len("\n".join(text_parts)) > MAX_FILE_CHARS:
                        break
                    # Try table extraction first
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            for row in table:
                                vals = [str(c) if c else "" for c in row]
                                text_parts.append(" | ".join(vals))
                    else:
                        page_text = page.extract_text() or ""
                        if page_text.strip():
                            text_parts.append(f"[Page {i+1}]\n{page_text}")
            content = "\n\n".join(text_parts)
            if len(content) > MAX_FILE_CHARS:
                content = content[:MAX_FILE_CHARS] + "\n... [truncated]"
            return {"filename": filename, "type": "pdf", "content": content, "error": None}
        except ImportError:
            try:
                import PyPDF2
                text_parts = []
                with open(filepath, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for i, page in enumerate(reader.pages):
                        if len("\n".join(text_parts)) > MAX_FILE_CHARS:
                            break
                        page_text = page.extract_text() or ""
                        if page_text.strip():
                            text_parts.append(f"[Page {i+1}]\n{page_text}")
                content = "\n\n".join(text_parts)
                if len(content) > MAX_FILE_CHARS:
                    content = content[:MAX_FILE_CHARS] + "\n... [truncated]"
                return {"filename": filename, "type": "pdf", "content": content, "error": None}
            except ImportError:
                return {"filename": filename, "type": "pdf", "content": "",
                        "error": "PDF support requires: pip install PyMuPDF or pdfplumber or PyPDF2"}

    text_parts = []
    doc = fitz.open(filepath)
    num_pages = len(doc)

    for i, page in enumerate(doc):
        if len("\n".join(text_parts)) > MAX_FILE_CHARS:
            text_parts.append(f"... [{num_pages - i} more pages truncated]")
            break

        page_text = page.get_text("text")

        # Also try to extract tables via text blocks
        blocks = page.get_text("blocks")
        table_lines = []
        for block in blocks:
            if block[6] == 0:  # text block (not image)
                text = block[4].strip()
                if text and "\t" in text:
                    # Tab-separated = likely table data
                    table_lines.append(text.replace("\t", " | "))

        if table_lines:
            text_parts.append(f"[Page {i+1} — Table Data]\n" + "\n".join(table_lines))
        elif page_text.strip():
            text_parts.append(f"[Page {i+1}]\n{page_text.strip()}")

    doc.close()

    content = "\n\n".join(text_parts)
    if len(content) > MAX_FILE_CHARS:
        content = content[:MAX_FILE_CHARS] + "\n... [truncated]"

    return {"filename": filename, "type": "pdf", "content": content, "error": None}


def _parse_excel(filepath: str, filename: str) -> dict:
    try:
        import openpyxl
    except ImportError:
        return {"filename": filename, "type": "excel", "content": "",
                "error": "Excel support requires: pip install openpyxl"}

    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    all_sheets = []

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        lines = [f"[Sheet: {sheet_name}]"]
        for row in ws.iter_rows(values_only=True):
            vals = [str(c) if c is not None else "" for c in row]
            lines.append(" | ".join(vals))
            if len("\n".join(lines)) > MAX_FILE_CHARS:
                lines.append("... [truncated]")
                break
        all_sheets.append("\n".join(lines))
        if sum(len(s) for s in all_sheets) > MAX_FILE_CHARS:
            break

    wb.close()
    content = "\n\n".join(all_sheets)
    if len(content) > MAX_FILE_CHARS:
        content = content[:MAX_FILE_CHARS] + "\n... [truncated]"

    return {"filename": filename, "type": "excel", "content": content, "error": None}


def _parse_docx(filepath: str, filename: str) -> dict:
    """Parse Word documents (.docx) — salary slips, bank statements, offer letters."""
    try:
        from docx import Document
    except ImportError:
        return {"filename": filename, "type": "docx", "content": "",
                "error": "Word document support requires: pip install python-docx"}

    doc = Document(filepath)
    parts = []
    total_len = 0

    # Extract paragraphs
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            parts.append(text)
            total_len += len(text)
            if total_len > MAX_FILE_CHARS:
                break

    # Extract tables (common in salary slips, bank statements)
    for table in doc.tables:
        if total_len > MAX_FILE_CHARS:
            break
        table_lines = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            table_lines.append(" | ".join(cells))
        if table_lines:
            parts.append("[Table]\n" + "\n".join(table_lines))
            total_len += sum(len(l) for l in table_lines)

    content = "\n".join(parts)
    if len(content) > MAX_FILE_CHARS:
        content = content[:MAX_FILE_CHARS] + "\n... [truncated]"

    return {"filename": filename, "type": "docx", "content": content, "error": None}
