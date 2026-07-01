from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

from app.config import settings
from app.db.models import Order


def generate_order_pdf(order: Order) -> Path:
    settings.print_pdf_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{safe_name(order.reference)}-{int(order.updated_at.timestamp())}.pdf"
    file_path = settings.print_pdf_dir / filename

    pdf = canvas.Canvas(str(file_path), pagesize=LETTER)
    width, height = LETTER
    left = 24
    right = width - 24
    y = height - 28

    y = draw_text(pdf, "ORDERBRIDGE", left, y, size=24, font="Helvetica-Bold")
    y = draw_text(pdf, f"Pedido: {order.reference}", left, y - 6, size=15, font="Helvetica-Bold")
    y = draw_text(pdf, f"Fecha: {order.created_at}", left, y - 4, size=12)

    y = draw_divider(pdf, width, y - 8, left, right)
    y = draw_text(pdf, "Cliente", left, y, size=15, font="Helvetica-Bold")
    y = draw_text(pdf, f"Nombre: {order.customer_name or '-'}", left, y - 4, size=12)
    y = draw_text(pdf, f"Telefono: {order.customer_phone or '-'}", left, y - 2, size=12)
    y = draw_text(pdf, f"Email: {order.customer_email or '-'}", left, y - 2, size=12)
    y = draw_wrapped(pdf, f"Direccion: {order.customer_address or '-'}", left, y - 2, right - left)

    y = draw_divider(pdf, width, y - 8, left, right)
    y = draw_text(pdf, "Entrega y pago", left, y, size=15, font="Helvetica-Bold")
    y = draw_text(pdf, f"Entrega: {order.fulfillment_method or '-'}", left, y - 4, size=12)
    y = draw_text(pdf, f"Pago: {order.payment_method or '-'} ({order.payment_status or '-'})", left, y - 2, size=12)
    if order.fulfillment_notes:
        y = draw_wrapped(pdf, f"Notas: {order.fulfillment_notes}", left, y - 2, right - left)

    y = draw_divider(pdf, width, y - 8, left, right)
    y = draw_text(pdf, "Productos", left, y, size=15, font="Helvetica-Bold")
    y -= 4
    for item in order.items:
        if y < 100:
            pdf.showPage()
            y = height - 28
        total = format_money(item.quantity * item.unit_price, order.currency)
        y = draw_text(pdf, f"{item.quantity} x {item.name}", left, y, size=12, font="Helvetica-Bold")
        y = draw_text(pdf, total, right - 140, y + 12, size=12)
        if item.options:
            y = draw_wrapped(pdf, f"Opciones: {', '.join(item.options)}", left + 12, y - 4, right - left - 20, size=11)
        y -= 6

    y = draw_divider(pdf, width, y - 6, left, right)
    y = draw_text(pdf, f"Subtotal: {format_money(order.subtotal, order.currency)}", left, y, size=12)
    y = draw_text(pdf, f"Envio: {format_money(order.delivery, order.currency)}", left, y - 2, size=12)
    y = draw_text(pdf, f"Impuesto: {format_money(order.tax, order.currency)}", left, y - 2, size=12)
    y = draw_text(pdf, f"Descuento: {format_money(-order.discount, order.currency)}", left, y - 2, size=12)
    y = draw_text(pdf, f"TOTAL: {format_money(order.total, order.currency)}", left, y - 8, size=18, font="Helvetica-Bold")

    pdf.setFillColor(colors.grey)
    pdf.setFont("Helvetica", 11)
    pdf.drawCentredString(width / 2, 30, "Documento generado automaticamente por OrderBridge Python")
    pdf.save()
    return file_path


def draw_text(pdf: canvas.Canvas, text: str, x: int, y: float, size: int = 10, font: str = "Helvetica") -> float:
    pdf.setFillColor(colors.black)
    pdf.setFont(font, size)
    pdf.drawString(x, y, text)
    return y - (size + 6)


def draw_divider(pdf: canvas.Canvas, width: float, y: float, left: float = 40, right: float | None = None) -> float:
    if right is None:
        right = width - 40
    pdf.setStrokeColor(colors.HexColor("#d1d5db"))
    pdf.line(left, y, right, y)
    pdf.setStrokeColor(colors.black)
    return y - 18


def draw_wrapped(pdf: canvas.Canvas, text: str, x: int, y: float, max_width: float, size: int = 10) -> float:
    pdf.setFont("Helvetica", size)
    words = text.split()
    current = ""
    line_height = size + 5
    for word in words:
        candidate = f"{current} {word}".strip()
        if pdf.stringWidth(candidate, "Helvetica", size) > max_width and current:
            pdf.drawString(x, y, current)
            y -= line_height
            current = word
        else:
            current = candidate
    if current:
        pdf.drawString(x, y, current)
        y -= line_height
    return y


def safe_name(value: str) -> str:
    return "".join(character.lower() if character.isalnum() else "-" for character in value).strip("-")


def format_money(value: float, currency: str) -> str:
    return f"{currency} {value:,.2f}"
