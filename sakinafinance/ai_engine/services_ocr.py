"""
OCR Service — SakinaFinance

Pipeline hybride production-friendly :
- PDF texte : extraction native via pypdf (rapide et fiable)
- PDF scanné / image : Gemini Vision ou OpenAI Vision si configuré
- Fallback local : binaire tesseract si installé sur le serveur
- Parsing métier : facture, reçu, relevé bancaire, contrat, bulletin
"""

from __future__ import annotations

import base64
import json
import logging
import mimetypes
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import requests
from django.conf import settings
from django.utils import timezone
from PIL import Image, ImageOps

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - depends on deployment environment
    PdfReader = None

from sakinafinance.accounting.models import Invoice
from .models import DocumentOCR

logger = logging.getLogger("sakinafinance")


MONEY_RE = re.compile(
    r"(?P<amount>(?:\d{1,3}(?:[ .,\u00a0]\d{3})+|\d+)(?:[,.]\d{1,2})?)\s*(?P<currency>XOF|FCFA|CFA|EUR|USD|€|\$)?",
    re.IGNORECASE,
)
DATE_PATTERNS = [
    re.compile(r"\b(?P<d>\d{1,2})[/-](?P<m>\d{1,2})[/-](?P<y>\d{2,4})\b"),
    re.compile(r"\b(?P<y>\d{4})[/-](?P<m>\d{1,2})[/-](?P<d>\d{1,2})\b"),
]
INVOICE_NUMBER_RE = re.compile(
    r"(?:facture|invoice|n[°o]\s*facture|num[eé]ro|ref(?:erence)?)[\s:#-]{0,8}([A-Z0-9][A-Z0-9./_-]{2,})",
    re.IGNORECASE,
)
TAX_RE = re.compile(r"(?:TVA|VAT|taxe)[^\d]{0,20}(\d{1,3}(?:[ .,\u00a0]\d{3})*(?:[,.]\d{1,2})?)", re.IGNORECASE)


@dataclass
class OCRResult:
    text: str
    engine: str
    confidence: Decimal
    pages_processed: int = 0
    warnings: list[str] | None = None


class OCRService:
    """Service principal d'OCR et d'extraction structurée."""

    def __init__(self):
        self.gemini_api_key = getattr(settings, "GEMINI_API_KEY", "")
        self.gemini_model = getattr(settings, "OCR_GEMINI_MODEL", getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash"))
        self.openai_api_key = getattr(settings, "OPENAI_API_KEY", "")
        self.openai_model = getattr(settings, "OCR_OPENAI_MODEL", "gpt-4o-mini")
        self.max_pages = int(getattr(settings, "OCR_MAX_PDF_PAGES", 6))
        self.min_pdf_text_chars = int(getattr(settings, "OCR_MIN_PDF_TEXT_CHARS", 160))
        self.provider_order = getattr(
            settings,
            "OCR_PROVIDER_ORDER",
            ["native_pdf", "gemini_vision", "openai_vision", "tesseract"],
        )

    def process_document(self, document: DocumentOCR | str) -> DocumentOCR:
        if not isinstance(document, DocumentOCR):
            document = DocumentOCR.objects.get(id=document)

        document.status = DocumentOCR.Status.PROCESSING
        document.error_message = ""
        document.save(update_fields=["status", "error_message"])

        tmp_file_path = None
        try:
            ext = Path(document.file.name).suffix
            if not ext and getattr(document, 'filename', ''):
                ext = Path(document.filename).suffix

            try:
                file_path = Path(document.file.path)
                if not file_path.suffix and ext:
                    # Si le fichier local n'a pas d'extension, forcer la création d'un fichier temporaire
                    raise NotImplementedError("Force temp file to add extension")
            except NotImplementedError:
                with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
                    with document.file.open('rb') as f:
                        shutil.copyfileobj(f, tmp_file)
                file_path = Path(tmp_file.name)
                tmp_file_path = file_path

            try:
                result = self.extract_text(file_path)
            finally:
                if tmp_file_path:
                    try:
                        tmp_file_path.unlink(missing_ok=True)
                    except OSError:
                        pass

            if not result.text.strip():
                raise ValueError(
                    "Aucun texte exploitable n'a pu être extrait. Configurez GEMINI_API_KEY/OPENAI_API_KEY ou installez tesseract pour les scans."
                )

            extracted = self.extract_structured_data(
                raw_text=result.text,
                document_type=document.document_type,
                filename=document.filename,
            )
            extracted.setdefault("ocr", {})
            extracted["ocr"].update(
                {
                    "engine": result.engine,
                    "pages_processed": result.pages_processed,
                    "warnings": result.warnings or [],
                    "processed_at": timezone.now().isoformat(),
                }
            )

            document.raw_text = result.text
            document.extracted_data = extracted
            document.confidence_score = result.confidence
            document.status = DocumentOCR.Status.EXTRACTED
            document.processed_at = timezone.now()
            document.save(
                update_fields=[
                    "raw_text",
                    "extracted_data",
                    "confidence_score",
                    "status",
                    "processed_at",
                ]
            )
            return document
        except Exception as exc:
            logger.exception("OCR processing failed for document %s", document.id)
            document.status = DocumentOCR.Status.FAILED
            document.error_message = str(exc)
            document.processed_at = timezone.now()
            document.save(update_fields=["status", "error_message", "processed_at"])
            return document

    def extract_text(self, file_path: Path) -> OCRResult:
        ext = file_path.suffix.lower()
        if ext == ".pdf":
            native = self._extract_pdf_text(file_path)
            if len(native.strip()) >= self.min_pdf_text_chars:
                return OCRResult(
                    text=native,
                    engine="native_pdf:pypdf",
                    confidence=Decimal("91.00"),
                    pages_processed=self._safe_pdf_page_count(file_path),
                )
            return self._extract_scanned_pdf(file_path, native_text=native)

        if ext in {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}:
            return self._extract_image(file_path)

        if ext in {".txt", ".csv"}:
            return OCRResult(file_path.read_text(encoding="utf-8", errors="ignore"), "text_file", Decimal("98.00"), 1)

        raise ValueError(f"Format OCR non supporté : {ext or 'sans extension'}")

    def _extract_pdf_text(self, file_path: Path) -> str:
        if PdfReader is None:
            logger.warning("pypdf is not installed; native PDF extraction disabled.")
            return ""
        try:
            reader = PdfReader(str(file_path))
            texts = []
            for page in reader.pages[: self.max_pages]:
                texts.append(page.extract_text() or "")
            return "\n\n".join(t.strip() for t in texts if t.strip()).strip()
        except Exception as exc:
            logger.warning("Native PDF extraction failed for %s: %s", file_path, exc)
            return ""

    def _safe_pdf_page_count(self, file_path: Path) -> int:
        if PdfReader is None:
            return 0
        try:
            return min(len(PdfReader(str(file_path)).pages), self.max_pages)
        except Exception:
            return 0

    def _extract_scanned_pdf(self, file_path: Path, native_text: str = "") -> OCRResult:
        if not shutil.which("pdftoppm"):
            if native_text:
                return OCRResult(native_text, "native_pdf:partial", Decimal("45.00"), 1, ["pdftoppm indisponible"])
            raise ValueError("PDF scanné détecté, mais pdftoppm n'est pas installé.")

        with tempfile.TemporaryDirectory(prefix="sakina_ocr_") as tmp:
            prefix = Path(tmp) / "page"
            cmd = [
                "pdftoppm",
                "-png",
                "-r",
                "220",
                "-f",
                "1",
                "-l",
                str(self.max_pages),
                str(file_path),
                str(prefix),
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=90)
            images = sorted(Path(tmp).glob("page-*.png"))
            if not images:
                raise ValueError("Conversion PDF vers images échouée.")

            parts = []
            engines = []
            confidences = []
            warnings = []
            for image_path in images:
                result = self._extract_image(image_path)
                if result.text:
                    parts.append(result.text)
                engines.append(result.engine)
                confidences.append(result.confidence)
                warnings.extend(result.warnings or [])

            text = "\n\n".join(parts).strip()
            if native_text:
                text = f"{native_text}\n\n{text}".strip()
            confidence = sum(confidences, Decimal("0")) / Decimal(len(confidences) or 1)
            return OCRResult(
                text=text,
                engine="+".join(sorted(set(engines))) or "scanned_pdf",
                confidence=confidence.quantize(Decimal("0.01")),
                pages_processed=len(images),
                warnings=warnings,
            )

    def _extract_image(self, file_path: Path) -> OCRResult:
        prepared = self._prepare_image(file_path)
        warnings: list[str] = []
        try:
            if "gemini_vision" in self.provider_order and self.gemini_api_key:
                text = self._ocr_with_gemini(prepared)
                if text:
                    return OCRResult(text=text, engine=f"gemini:{self.gemini_model}", confidence=Decimal("88.00"), pages_processed=1)
                warnings.append("Gemini Vision n'a pas retourné de texte.")

            if "openai_vision" in self.provider_order and self.openai_api_key:
                text = self._ocr_with_openai(prepared)
                if text:
                    return OCRResult(text=text, engine=f"openai:{self.openai_model}", confidence=Decimal("86.00"), pages_processed=1)
                warnings.append("OpenAI Vision n'a pas retourné de texte.")

            if "tesseract" in self.provider_order and shutil.which("tesseract"):
                text = self._ocr_with_tesseract(prepared)
                if text:
                    return OCRResult(text=text, engine="tesseract:local", confidence=Decimal("76.00"), pages_processed=1)
                warnings.append("Tesseract n'a pas retourné de texte.")

            return OCRResult(text="", engine="unavailable", confidence=Decimal("0.00"), pages_processed=1, warnings=warnings)
        finally:
            try:
                prepared.unlink(missing_ok=True)
            except OSError:
                pass

    def _prepare_image(self, file_path: Path) -> Path:
        image = Image.open(file_path)
        image = image.convert("L")
        image = ImageOps.autocontrast(image)
        width, height = image.size
        if max(width, height) < 1600:
            image = image.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
        image = image.point(lambda p: 255 if p > 185 else 0)

        tmp = tempfile.NamedTemporaryFile(prefix="sakina_ocr_img_", suffix=".png", delete=False)
        tmp_path = Path(tmp.name)
        tmp.close()
        image.save(tmp_path, format="PNG", optimize=True)
        return tmp_path

    def _ocr_prompt(self) -> str:
        return (
            "Tu es un moteur OCR financier. Extrais tout le texte visible du document, "
            "en conservant les lignes, montants, dates, numéros de facture, noms, taxes et tableaux. "
            "Ne commente pas. Retourne uniquement le texte brut."
        )

    def _ocr_with_gemini(self, image_path: Path) -> str:
        try:
            mime = mimetypes.guess_type(str(image_path))[0] or "image/png"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": self._ocr_prompt()},
                            {
                                "inline_data": {
                                    "mime_type": mime,
                                    "data": base64.b64encode(image_path.read_bytes()).decode("ascii"),
                                }
                            },
                        ]
                    }
                ],
                "generationConfig": {"temperature": 0, "maxOutputTokens": 8192},
            }
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent"
            response = requests.post(url, params={"key": self.gemini_api_key}, json=payload, timeout=90)
            response.raise_for_status()
            data = response.json()
            return self._extract_gemini_text(data).strip()
        except Exception as exc:
            logger.warning("Gemini OCR failed: %s", exc)
            return ""

    def _extract_gemini_text(self, data: dict[str, Any]) -> str:
        parts = []
        for candidate in data.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                if part.get("text"):
                    parts.append(part["text"])
        return "\n".join(parts)

    def _ocr_with_openai(self, image_path: Path) -> str:
        try:
            import openai

            mime = mimetypes.guess_type(str(image_path))[0] or "image/png"
            data_url = f"data:{mime};base64,{base64.b64encode(image_path.read_bytes()).decode('ascii')}"
            client = openai.OpenAI(api_key=self.openai_api_key)
            response = client.chat.completions.create(
                model=self.openai_model,
                temperature=0,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self._ocr_prompt()},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
                max_tokens=4096,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as exc:
            logger.warning("OpenAI OCR failed: %s", exc)
            return ""

    def _ocr_with_tesseract(self, image_path: Path) -> str:
        try:
            languages = getattr(settings, "OCR_TESSERACT_LANGUAGES", "fra+eng")
            result = subprocess.run(
                ["tesseract", str(image_path), "stdout", "-l", languages, "--psm", "6"],
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )
            return result.stdout.strip()
        except Exception as exc:
            logger.warning("Tesseract OCR failed: %s", exc)
            return ""

    def extract_structured_data(self, raw_text: str, document_type: str, filename: str = "") -> dict[str, Any]:
        text = self._normalize_text(raw_text)
        local = self._local_extract(text, document_type, filename)
        ai = self._ai_structured_extract(text, document_type)
        if ai:
            local = self._deep_merge(local, ai)
            local.setdefault("extraction_method", "hybrid_ai")
        else:
            local.setdefault("extraction_method", "local_regex")
        local["quality"] = self._quality_report(local, text)
        return local

    def _normalize_text(self, text: str) -> str:
        text = text.replace("\u00a0", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _local_extract(self, text: str, document_type: str, filename: str) -> dict[str, Any]:
        amounts = self._extract_amounts(text)
        dates = self._extract_dates(text)
        currency = self._detect_currency(text)
        invoice_number = self._extract_invoice_number(text, filename)
        tax_amount = self._extract_tax(text)
        total = self._best_total(text, amounts)
        invoice_date = dates[0].isoformat() if dates else None
        due_date = self._extract_due_date(text, dates)
        partner = self._extract_partner_name(text)

        data: dict[str, Any] = {
            "document_type": document_type,
            "filename": filename,
            "language": "fr",
            "currency": currency,
            "amounts": [str(a) for a in amounts[:12]],
            "dates": [d.isoformat() for d in dates[:8]],
            "summary": {
                "partner_name": partner,
                "invoice_number": invoice_number,
                "invoice_date": invoice_date,
                "due_date": due_date,
                "subtotal": None,
                "tax_amount": str(tax_amount) if tax_amount is not None else None,
                "total": str(total) if total is not None else None,
            },
            "fields": {},
            "tables": [],
            "raw_preview": text[:1200],
        }

        if document_type == DocumentOCR.DocumentType.BANK_STATEMENT:
            data["bank_statement"] = self._extract_bank_statement_lines(text)
        elif document_type in {
            DocumentOCR.DocumentType.INVOICE,
            DocumentOCR.DocumentType.SUPPLIER_INVOICE,
            DocumentOCR.DocumentType.RECEIPT,
        }:
            data["invoice"] = self._extract_invoice_lines(text)
            data["line_items"] = data["invoice"]
        elif document_type in {
            DocumentOCR.DocumentType.PURCHASE_ORDER,
            DocumentOCR.DocumentType.DELIVERY_NOTE,
            DocumentOCR.DocumentType.RECEIPT_NOTE,
            DocumentOCR.DocumentType.STOCK_COUNT,
        }:
            data["inventory"] = self._extract_inventory_lines(text)
            data["line_items"] = data["inventory"]

        return data

    def _ai_structured_extract(self, text: str, document_type: str) -> dict[str, Any]:
        if not self.gemini_api_key or len(text) < 40:
            return {}
        try:
            prompt = f"""
Tu es un extracteur de donnees financieres OHADA. Retourne un JSON strict, sans markdown.
Type document: {document_type}
Texte OCR:
{text[:12000]}

Schema:
{{
  "summary": {{
    "partner_name": null,
    "invoice_number": null,
    "invoice_date": null,
    "due_date": null,
    "subtotal": null,
    "tax_amount": null,
    "total": null
  }},
  "fields": {{"tax_id": null, "address": null, "payment_terms": null}},
  "line_items": [{{"sku": null, "description": "", "quantity": null, "unit": null, "unit_price": null, "total": null}}],
  "risks": [],
  "recommended_accounting": {{"journal_type": null, "invoice_type": null}}
}}
"""
            payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0, "maxOutputTokens": 4096}}
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent"
            response = requests.post(url, params={"key": self.gemini_api_key}, json=payload, timeout=60)
            response.raise_for_status()
            raw = self._extract_gemini_text(response.json())
            return self._parse_json_object(raw)
        except Exception as exc:
            logger.info("AI structured extraction unavailable: %s", exc)
            return {}

    def _parse_json_object(self, raw: str) -> dict[str, Any]:
        raw = raw.strip()
        raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.IGNORECASE | re.MULTILINE).strip()
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            raw = match.group(0)
        try:
            value = json.loads(raw)
            return value if isinstance(value, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _deep_merge(self, base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
        for key, value in extra.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                base[key] = self._deep_merge(base[key], value)
            elif value not in (None, "", [], {}):
                base[key] = value
        return base

    def _extract_amounts(self, text: str) -> list[Decimal]:
        amounts = []
        for match in MONEY_RE.finditer(text):
            amount = self._to_decimal(match.group("amount"))
            if amount is not None and amount >= Decimal("0"):
                amounts.append(amount)
        return sorted(set(amounts), reverse=True)

    def _to_decimal(self, value: str | None) -> Decimal | None:
        if not value:
            return None
        cleaned = value.replace("\u00a0", " ").replace(" ", "").replace(".", "")
        if "," in cleaned and "." not in cleaned:
            cleaned = cleaned.replace(",", ".")
        try:
            return Decimal(cleaned).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            return None

    def _extract_dates(self, text: str) -> list[date]:
        dates = []
        for pattern in DATE_PATTERNS:
            for match in pattern.finditer(text):
                y = int(match.group("y"))
                if y < 100:
                    y += 2000
                try:
                    dates.append(date(y, int(match.group("m")), int(match.group("d"))))
                except ValueError:
                    continue
        return sorted(set(dates))

    def _detect_currency(self, text: str) -> str:
        upper = text.upper()
        if "EUR" in upper or "€" in text:
            return "EUR"
        if "USD" in upper or "$" in text:
            return "USD"
        return "XOF"

    def _extract_invoice_number(self, text: str, filename: str) -> str | None:
        match = INVOICE_NUMBER_RE.search(text)
        if match:
            return match.group(1).strip(" .:-_")
        stem = Path(filename).stem
        fallback = re.search(r"([A-Z]{0,4}[-_]?\d{3,})", stem, re.IGNORECASE)
        return fallback.group(1) if fallback else None

    def _extract_tax(self, text: str) -> Decimal | None:
        match = TAX_RE.search(text)
        return self._to_decimal(match.group(1)) if match else None

    def _best_total(self, text: str, amounts: list[Decimal]) -> Decimal | None:
        total_patterns = [
            r"(?:net\s+a\s+payer|net\s+à\s+payer|total\s+ttc|montant\s+total|total)[^\d]{0,30}(\d{1,3}(?:[ .,\u00a0]\d{3})*(?:[,.]\d{1,2})?)",
            r"(?:amount\s+due|balance\s+due)[^\d]{0,30}(\d{1,3}(?:[ .,\u00a0]\d{3})*(?:[,.]\d{1,2})?)",
        ]
        for pattern in total_patterns:
            matches = re.findall(pattern, text, flags=re.IGNORECASE)
            if matches:
                amount = self._to_decimal(matches[-1])
                if amount:
                    return amount
        return amounts[0] if amounts else None

    def _extract_due_date(self, text: str, dates: list[date]) -> str | None:
        match = re.search(r"(?:echeance|échéance|due date|date limite)[^\d]{0,25}(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", text, re.IGNORECASE)
        if match:
            found = self._extract_dates(match.group(1))
            if found:
                return found[0].isoformat()
        if len(dates) >= 2:
            return dates[-1].isoformat()
        if dates:
            return (dates[0] + timedelta(days=30)).isoformat()
        return None

    def _extract_partner_name(self, text: str) -> str:
        lines = [line.strip(" -:\t") for line in text.splitlines() if line.strip()]
        stopwords = {"facture", "invoice", "recu", "reçu", "devis", "date", "total"}
        for line in lines[:10]:
            clean = re.sub(r"\s+", " ", line).strip()
            if len(clean) >= 3 and not any(s in clean.lower() for s in stopwords) and not re.fullmatch(r"[\d\s./:-]+", clean):
                return clean[:160]
        return ""

    def _extract_invoice_lines(self, text: str) -> list[dict[str, Any]]:
        items = []
        for line in text.splitlines():
            amounts = self._extract_amounts(line)
            if amounts and len(line) > 12 and not re.search(r"total|tva|taxe|subtotal|sous-total", line, re.IGNORECASE):
                items.append({"description": line.strip()[:220], "total": str(amounts[0])})
            if len(items) >= 20:
                break
        return items

    def _extract_bank_statement_lines(self, text: str) -> list[dict[str, Any]]:
        rows = []
        for line in text.splitlines():
            dates = self._extract_dates(line)
            amounts = self._extract_amounts(line)
            if dates and amounts:
                rows.append({"date": dates[0].isoformat(), "description": line.strip()[:260], "amount": str(amounts[0])})
            if len(rows) >= 80:
                break
        return rows

    def _extract_inventory_lines(self, text: str) -> list[dict[str, Any]]:
        rows = []
        for line in text.splitlines():
            clean = re.sub(r"\s+", " ", line).strip()
            if len(clean) < 8:
                continue
            amounts = self._extract_amounts(clean)
            qty_match = re.search(r"\b(?:qt[eé]|quantit[eé]|qty|qte|nombre)?\s*[:x]?\s*(\d+(?:[,.]\d{1,3})?)\s*(?:pcs|piece|pi[eè]ce|unit[eé]|kg|l|m|carton|boite|boîte)?\b", clean, re.IGNORECASE)
            sku_match = re.search(r"\b(?:sku|ref|réf|code|article)\s*[:#-]?\s*([A-Z0-9._/-]{2,})", clean, re.IGNORECASE)
            looks_like_item = qty_match or sku_match or len(amounts) >= 1
            if not looks_like_item:
                continue
            row = {
                "sku": sku_match.group(1) if sku_match else None,
                "description": clean[:240],
                "quantity": qty_match.group(1).replace(",", ".") if qty_match else None,
                "unit": self._extract_unit(clean),
                "unit_price": str(amounts[-1]) if len(amounts) >= 2 else None,
                "total": str(amounts[0]) if amounts else None,
            }
            rows.append(row)
            if len(rows) >= 80:
                break
        return rows

    def _extract_unit(self, text: str) -> str | None:
        match = re.search(r"\b(pcs|pieces|pi[eè]ces|unit[eé]s?|kg|l|m|cartons?|bo[iî]tes?)\b", text, re.IGNORECASE)
        return match.group(1) if match else None

    def _quality_report(self, data: dict[str, Any], text: str) -> dict[str, Any]:
        summary = data.get("summary", {})
        checks = {
            "has_text": len(text) >= 40,
            "has_amount": bool(summary.get("total") or data.get("amounts")),
            "has_date": bool(summary.get("invoice_date") or data.get("dates")),
            "has_partner": bool(summary.get("partner_name")),
            "has_reference": bool(summary.get("invoice_number")),
        }
        score = sum(1 for ok in checks.values() if ok) / len(checks) * 100
        return {
            "score": round(score, 1),
            "checks": checks,
            "needs_review": score < 70,
        }

    def create_invoice_from_ocr(self, document: DocumentOCR, invoice_type: str = Invoice.InvoiceType.SUPPLIER) -> Invoice:
        data = document.extracted_data or {}
        summary = data.get("summary", {})
        invoice_number = summary.get("invoice_number") or f"OCR-{str(document.id)[:8]}"
        invoice_date = self._date_or_today(summary.get("invoice_date"))
        due_date = self._date_or_today(summary.get("due_date"), default=invoice_date + timedelta(days=30))
        total = self._to_decimal(str(summary.get("total") or "0")) or Decimal("0.00")
        tax_amount = self._to_decimal(str(summary.get("tax_amount") or "0")) or Decimal("0.00")
        subtotal = self._to_decimal(str(summary.get("subtotal") or "")) or max(total - tax_amount, Decimal("0.00"))

        original_number = invoice_number
        i = 2
        while Invoice.objects.filter(company=document.company, invoice_number=invoice_number).exists():
            invoice_number = f"{original_number}-{i}"
            i += 1

        invoice = Invoice.objects.create(
            company=document.company,
            invoice_number=invoice_number,
            invoice_type=invoice_type,
            partner_name=summary.get("partner_name") or "Partenaire OCR",
            invoice_date=invoice_date,
            due_date=due_date,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total=total,
            amount_due=total,
            currency=data.get("currency") or "XOF",
            status=Invoice.InvoiceStatus.DRAFT,
            notes=f"Créée depuis OCR : {document.filename}",
        )
        document.linked_invoice = invoice
        document.status = DocumentOCR.Status.VALIDATED
        document.save(update_fields=["linked_invoice", "status"])
        return invoice

    def _date_or_today(self, value: str | None, default: date | None = None) -> date:
        if isinstance(value, date):
            return value
        if value:
            try:
                return datetime.fromisoformat(value).date()
            except ValueError:
                pass
        return default or timezone.now().date()
