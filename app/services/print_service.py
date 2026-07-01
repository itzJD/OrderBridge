from pathlib import Path
from tempfile import NamedTemporaryFile

import pypdfium2 as pdfium
import win32print
import win32ui
from win32con import HORZRES, VERTRES
from PIL import Image, ImageOps, ImageWin
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

from app.config import settings
from app.db.models import Order
from app.services.pdf_service import generate_order_pdf
from app.services.settings_service import get_selected_printer


PRINT_RENDER_DPI = 216


def list_printers() -> dict:
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    printers = []
    for printer in win32print.EnumPrinters(flags):
        printers.append({"name": printer[2]})

    default_printer = None
    try:
        default_printer = win32print.GetDefaultPrinter()
    except Exception:
        default_printer = None

    return {"printers": printers, "default_printer": default_printer}


def print_order(order: Order) -> dict:
    pdf_path = generate_order_pdf(order)
    printer_name = settings.printer_name.strip() or get_selected_printer_name()
    print_pdf_as_images(pdf_path, printer_name)
    return {
        "mode": "pdf-to-image",
        "printer": printer_name,
        "file_path": str(pdf_path),
    }


def print_test_page(printer_name: str | None = None) -> dict:
    resolved_printer = printer_name or settings.printer_name.strip() or get_selected_printer_name()
    if not resolved_printer:
        raise RuntimeError("No printer configured and no default Windows printer was found")

    with NamedTemporaryFile(prefix="orderbridge-test-", suffix=".pdf", delete=False) as tmp_file:
        pdf_path = Path(tmp_file.name)

    try:
        pdf = canvas.Canvas(str(pdf_path), pagesize=LETTER)
        width, height = LETTER
        pdf.setFont("Helvetica-Bold", 26)
        pdf.drawString(36, height - 60, "ORDERBRIDGE TEST PRINT")
        pdf.setFont("Helvetica", 15)
        pdf.drawString(36, height - 100, f"Printer: {resolved_printer}")
        pdf.drawString(36, height - 130, "This page is a local print test.")
        pdf.drawString(36, height - 160, "If this looks small, the printer driver scaling is still active.")
        pdf.save()
        print_pdf_as_images(pdf_path, resolved_printer)
    finally:
        try:
            pdf_path.unlink(missing_ok=True)
        except Exception:
            pass

    return {"mode": "test-page", "printer": resolved_printer}


def print_pdf_as_images(pdf_path: Path, printer_name: str | None) -> None:
    if not printer_name:
        raise RuntimeError("No printer configured and no default Windows printer was found")

    pdf_document = pdfium.PdfDocument(str(pdf_path))
    try:
        hdc = create_printer_dc(printer_name)
        try:
            start_print_job(hdc, pdf_path.name)
            try:
                for page_number in range(len(pdf_document)):
                    page = pdf_document.get_page(page_number)
                    image = render_pdf_page(page)
                    page.close()
                    draw_image_to_printer(hdc, image)
            finally:
                end_print_job(hdc)
        finally:
            hdc.DeleteDC()
    finally:
        pdf_document.close()


def create_printer_dc(printer_name: str) -> win32ui.CreateDC:
    hdc = win32ui.CreateDC()
    hdc.CreatePrinterDC(printer_name)
    return hdc


def start_print_job(hdc: win32ui.CreateDC, document_name: str) -> None:
    hdc.StartDoc(document_name)


def end_print_job(hdc: win32ui.CreateDC) -> None:
    hdc.EndDoc()


def render_pdf_page(page: pdfium.PdfPage) -> Image.Image:
    zoom = PRINT_RENDER_DPI / 72.0
    bitmap = page.render(scale=zoom)
    image = bitmap.to_pil().convert("RGB")
    return ImageOps.expand(image, border=0, fill="white")


def draw_image_to_printer(hdc: win32ui.CreateDC, image: Image.Image) -> None:
    printable_width = hdc.GetDeviceCaps(HORZRES)
    printable_height = hdc.GetDeviceCaps(VERTRES)

    image = image.copy()
    image_ratio = image.width / image.height
    printable_ratio = printable_width / printable_height

    if image_ratio > printable_ratio:
        target_width = printable_width
        target_height = max(1, round(printable_width / image_ratio))
    else:
        target_height = printable_height
        target_width = max(1, round(printable_height * image_ratio))

    image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)

    left = (printable_width - image.width) // 2
    top = (printable_height - image.height) // 2
    right = left + image.width
    bottom = top + image.height

    hdc.StartPage()
    dib = ImageWin.Dib(image)
    dib.draw(hdc.GetHandleOutput(), (left, top, right, bottom))
    hdc.EndPage()


def get_default_printer() -> str | None:
    try:
        return win32print.GetDefaultPrinter()
    except Exception:
        return None


def get_selected_printer_name() -> str | None:
    # Fallback order: persisted selection, then Windows default printer.
    printer_name = None
    try:
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            printer_name = get_selected_printer(db).strip() or None
        finally:
            db.close()
    except Exception:
        printer_name = None

    return printer_name or get_default_printer()
