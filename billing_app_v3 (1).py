import sys
import os
import io
import math
from datetime import datetime
from PyQt5.QtCore import Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve, QRect
from PyQt5.QtGui import (QFont, QImage, QPixmap, QColor, QPalette, QLinearGradient,
                         QPainter, QBrush, QPen, QIcon, QFontDatabase)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLineEdit, QLabel,
    QMessageBox, QDialog, QFormLayout, QDialogButtonBox, QDoubleSpinBox,
    QSpinBox, QFrame, QScrollArea, QStackedWidget, QGraphicsDropShadowEffect,
    QSizePolicy, QHeaderView, QAbstractItemView, QTabWidget, QComboBox
)
import sqlite3
import cv2
import qrcode
from PIL import Image


# ═══════════════════════════════════════════════════════════
#  THEME  — dark luxury POS terminal
# ═══════════════════════════════════════════════════════════
THEME = {
    "bg":        "#0D0F14",
    "panel":     "#13161E",
    "card":      "#1A1E2A",
    "border":    "#252A38",
    "accent":    "#6C63FF",
    "accent2":   "#00D4AA",
    "danger":    "#FF4757",
    "warning":   "#FFA502",
    "success":   "#2ED573",
    "text":      "#E8EAF0",
    "text2":     "#7B8298",
    "text3":     "#4A5068",
    "gold":      "#FFD700",
    "upi":       "#5A2D82",
    "cash":      "#1A6B3C",
    "card_pay":  "#1A3A6B",
}


def shadow(widget, blur=20, color="#000000", offset=(0, 4)):
    eff = QGraphicsDropShadowEffect()
    eff.setBlurRadius(blur)
    eff.setColor(QColor(color))
    eff.setOffset(*offset)
    widget.setGraphicsEffect(eff)
    return eff


def styled_btn(text, color=None, h=40, radius=10):
    btn = QPushButton(text)
    c = color or THEME["accent"]
    btn.setFixedHeight(h)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 {c}, stop:1 {c}cc);
            color: #fff;
            border: none;
            border-radius: {radius}px;
            font-weight: 700;
            font-size: 13px;
            letter-spacing: 0.5px;
            padding: 0 20px;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 {c}dd, stop:1 {c});
            border: 1px solid {c};
        }}
        QPushButton:pressed {{ background: {c}99; }}
        QPushButton:disabled {{ background: {THEME['border']}; color: {THEME['text3']}; }}
    """)
    return btn


def card_frame(radius=14):
    f = QFrame()
    f.setStyleSheet(f"""
        QFrame {{
            background: {THEME['card']};
            border: 1px solid {THEME['border']};
            border-radius: {radius}px;
        }}
    """)
    shadow(f, 30, "#00000066", (0, 6))
    return f


# ═══════════════════════════════════════════════════════════
#  PRODUCT QR DIALOG  — shows the QR code for a product ID
# ═══════════════════════════════════════════════════════════
class ProductQRDialog(QDialog):
    def __init__(self, product_id, product_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"QR Code — {product_name}")
        self.setFixedSize(340, 400)
        self.setStyleSheet(f"""
            QDialog {{ background: {THEME['bg']}; border-radius: 16px; }}
            QLabel  {{ color: {THEME['text']}; }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(30, 24, 30, 24)
        lay.setSpacing(14)

        title = QLabel(f"📦  {product_name}")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        sub = QLabel(f"ID: {product_id}")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"color: {THEME['text2']}; font-size: 12px;")
        lay.addWidget(sub)

        # Generate QR
        qr_img = qrcode.make(product_id)
        buf = io.BytesIO()
        qr_img.save(buf, format="PNG")
        buf.seek(0)
        qt_img = QImage.fromData(buf.read())
        pix = QPixmap.fromImage(qt_img).scaled(220, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        qr_label = QLabel()
        qr_label.setPixmap(pix)
        qr_label.setAlignment(Qt.AlignCenter)
        qr_label.setStyleSheet(f"""
            background: white;
            border-radius: 12px;
            padding: 10px;
            border: 2px solid {THEME['accent']};
        """)
        lay.addWidget(qr_label)

        hint = QLabel("Scan this code at the billing counter")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(f"color: {THEME['text2']}; font-size: 11px;")
        lay.addWidget(hint)

        close_btn = styled_btn("Close", THEME["accent"])
        close_btn.clicked.connect(self.accept)
        lay.addWidget(close_btn)


# ═══════════════════════════════════════════════════════════
#  ADD PRODUCT DIALOG  — with built-in QR generation
# ═══════════════════════════════════════════════════════════
class AddProductDialog(QDialog):
    def __init__(self, cursor, conn, parent=None):
        super().__init__(parent)
        self.cursor = cursor
        self.conn = conn
        self.setWindowTitle("Add New Product")
        self.setFixedSize(460, 520)
        self.setStyleSheet(f"""
            QDialog       {{ background: {THEME['bg']}; }}
            QLabel        {{ color: {THEME['text']}; font-size: 13px; }}
            QLineEdit, QDoubleSpinBox, QSpinBox {{
                background: {THEME['card']};
                color: {THEME['text']};
                border: 1px solid {THEME['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {{
                border: 1px solid {THEME['accent']};
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(12)

        title = QLabel("➕  Add New Product")
        title.setFont(QFont("Segoe UI", 15, QFont.Bold))
        lay.addWidget(title)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background: {THEME['border']}; max-height: 1px;")
        lay.addWidget(sep)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)

        self.id_input    = QLineEdit(); self.id_input.setPlaceholderText("e.g. P001")
        self.name_input  = QLineEdit(); self.name_input.setPlaceholderText("e.g. Milk 500ml")
        self.price_input = QDoubleSpinBox()
        self.price_input.setMaximum(999999); self.price_input.setPrefix("₹ ")
        self.price_input.setDecimals(2)
        self.qty_input   = QSpinBox(); self.qty_input.setMaximum(99999)
        self.qty_input.setValue(1)

        form.addRow("Product ID :", self.id_input)
        form.addRow("Name :",       self.name_input)
        form.addRow("Price :",      self.price_input)
        form.addRow("Quantity :",   self.qty_input)
        lay.addLayout(form)

        # QR preview area
        qr_frame = card_frame(12)
        qr_lay = QVBoxLayout(qr_frame)
        qr_lay.setContentsMargins(12, 12, 12, 12)

        qr_title = QLabel("QR Code Preview")
        qr_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        qr_title.setAlignment(Qt.AlignCenter)
        qr_lay.addWidget(qr_title)

        self.qr_preview = QLabel("Enter a Product ID above to preview QR")
        self.qr_preview.setFixedHeight(130)
        self.qr_preview.setAlignment(Qt.AlignCenter)
        self.qr_preview.setStyleSheet(f"color: {THEME['text2']}; font-size: 11px;")
        qr_lay.addWidget(self.qr_preview)

        gen_btn = styled_btn("🔄  Generate / Refresh QR", THEME["accent2"], h=34)
        gen_btn.clicked.connect(self.generate_qr_preview)
        qr_lay.addWidget(gen_btn)
        lay.addWidget(qr_frame)

        # Buttons
        btn_row = QHBoxLayout()
        cancel = styled_btn("Cancel", THEME["danger"], h=42)
        cancel.clicked.connect(self.reject)
        save = styled_btn("💾  Save Product", THEME["success"], h=42)
        save.clicked.connect(self.save_product)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        lay.addLayout(btn_row)

        self.id_input.textChanged.connect(self.generate_qr_preview)

    def generate_qr_preview(self):
        pid = self.id_input.text().strip()
        if not pid:
            self.qr_preview.setPixmap(QPixmap())
            self.qr_preview.setText("Enter a Product ID above to preview QR")
            return
        qr_img = qrcode.make(pid)
        buf = io.BytesIO()
        qr_img.save(buf, format="PNG")
        buf.seek(0)
        qt_img = QImage.fromData(buf.read())
        pix = QPixmap.fromImage(qt_img).scaled(110, 110, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.qr_preview.setPixmap(pix)
        self.qr_preview.setText("")

    def save_product(self):
        pid   = self.id_input.text().strip()
        name  = self.name_input.text().strip()
        price = self.price_input.value()
        qty   = self.qty_input.value()
        if not pid or not name:
            QMessageBox.warning(self, "Missing Info", "Product ID and Name are required!")
            return
        try:
            self.cursor.execute("INSERT INTO inventory VALUES (?, ?, ?, ?)",
                                (pid, name, price, qty))
            self.conn.commit()
            # Ask to show/print QR
            reply = QMessageBox.question(self, "Show QR Code",
                                         f"Product '{name}' saved!\nDo you want to view its QR code?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                dlg = ProductQRDialog(pid, name, self)
                dlg.exec_()
            self.accept()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Duplicate", f"Product ID '{pid}' already exists!")


# ═══════════════════════════════════════════════════════════
#  PAYMENT DIALOG
# ═══════════════════════════════════════════════════════════
class PaymentDialog(QDialog):
    def __init__(self, total, upi_id, parent=None):
        super().__init__(parent)
        self.total   = total
        self.upi_id  = upi_id
        self.paid    = False
        self.setWindowTitle("Payment")
        self.setFixedSize(480, 560)
        self.setStyleSheet(f"""
            QDialog {{ background: {THEME['bg']}; }}
            QLabel  {{ color: {THEME['text']}; }}
            QLineEdit, QDoubleSpinBox, QSpinBox {{
                background: {THEME['card']};
                color: {THEME['text']};
                border: 1px solid {THEME['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
            }}
            QTabWidget::pane {{
                border: 1px solid {THEME['border']};
                border-radius: 10px;
                background: {THEME['card']};
            }}
            QTabBar::tab {{
                background: {THEME['panel']};
                color: {THEME['text2']};
                padding: 10px 22px;
                border: none;
                font-size: 13px;
                font-weight: 600;
            }}
            QTabBar::tab:selected {{
                background: {THEME['accent']};
                color: white;
                border-radius: 6px;
            }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        # Header
        hdr = QLabel("💳  Select Payment Method")
        hdr.setFont(QFont("Segoe UI", 15, QFont.Bold))
        lay.addWidget(hdr)

        total_label = QLabel(f"Amount Due:  ₹{total:.2f}")
        total_label.setFont(QFont("Segoe UI", 13, QFont.Bold))
        total_label.setStyleSheet(f"color: {THEME['accent2']}; font-size: 18px;")
        lay.addWidget(total_label)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background: {THEME['border']}; max-height:1px;")
        lay.addWidget(sep)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._cash_tab(),  "💵  Cash")
        self.tabs.addTab(self._upi_tab(),   "📱  UPI")
        self.tabs.addTab(self._card_tab(),  "💳  Card")
        lay.addWidget(self.tabs)

        btn_row = QHBoxLayout()
        cancel = styled_btn("Cancel", THEME["danger"], h=44)
        cancel.clicked.connect(self.reject)
        self.confirm_btn = styled_btn("✅  Confirm Payment", THEME["success"], h=44)
        self.confirm_btn.clicked.connect(self.confirm_payment)
        btn_row.addWidget(cancel)
        btn_row.addWidget(self.confirm_btn)
        lay.addLayout(btn_row)

    # ── Cash tab ──
    def _cash_tab(self):
        w = QWidget()
        w.setStyleSheet(f"background: {THEME['card']};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(14)

        lay.addWidget(self._row_label("Amount Due", f"₹{self.total:.2f}", THEME["text"]))

        recv_lbl = QLabel("Cash Received (₹):")
        recv_lbl.setStyleSheet(f"color: {THEME['text2']}; font-size: 12px;")
        lay.addWidget(recv_lbl)

        self.cash_input = QDoubleSpinBox()
        self.cash_input.setMaximum(9999999)
        self.cash_input.setDecimals(2)
        self.cash_input.setValue(math.ceil(self.total))
        self.cash_input.setFixedHeight(46)
        self.cash_input.setPrefix("₹ ")
        self.cash_input.valueChanged.connect(self.update_change)
        lay.addWidget(self.cash_input)

        self.change_label = QLabel()
        self.change_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.change_label.setAlignment(Qt.AlignCenter)
        self.change_label.setStyleSheet(f"""
            background: {THEME['bg']};
            border-radius: 10px;
            padding: 14px;
            border: 1px solid {THEME['border']};
        """)
        lay.addWidget(self.change_label)
        self.update_change()

        # Quick-amount buttons
        quick_lbl = QLabel("Quick amounts:")
        quick_lbl.setStyleSheet(f"color:{THEME['text2']}; font-size:11px;")
        lay.addWidget(quick_lbl)

        row = QHBoxLayout()
        for amt in [20, 50, 100, 200, 500, 2000]:
            b = QPushButton(f"₹{amt}")
            b.setFixedHeight(34)
            b.setStyleSheet(f"""
                QPushButton {{
                    background: {THEME['border']};
                    color: {THEME['text']};
                    border: none; border-radius: 6px;
                    font-size: 12px; font-weight: 600;
                }}
                QPushButton:hover {{ background: {THEME['accent']}44; border:1px solid {THEME['accent']}; }}
            """)
            b.clicked.connect(lambda _, a=amt: self.cash_input.setValue(
                math.ceil(self.total / a) * a))
            row.addWidget(b)
        lay.addLayout(row)
        lay.addStretch()
        return w

    def _row_label(self, label, value, color):
        w = QWidget()
        r = QHBoxLayout(w); r.setContentsMargins(0,0,0,0)
        l = QLabel(label); l.setStyleSheet(f"color:{THEME['text2']}; font-size:12px;")
        v = QLabel(value); v.setStyleSheet(f"color:{color}; font-size:14px; font-weight:700;")
        r.addWidget(l); r.addStretch(); r.addWidget(v)
        return w

    def update_change(self):
        received = self.cash_input.value()
        change   = received - self.total
        if change >= 0:
            self.change_label.setText(f"Change to return:  ₹{change:.2f}")
            self.change_label.setStyleSheet(f"""
                background: {THEME['success']}22;
                border-radius: 10px; padding: 14px;
                border: 1px solid {THEME['success']}88;
                color: {THEME['success']}; font-size: 14px; font-weight: 700;
            """)
        else:
            self.change_label.setText(f"Short by:  ₹{abs(change):.2f}")
            self.change_label.setStyleSheet(f"""
                background: {THEME['danger']}22;
                border-radius: 10px; padding: 14px;
                border: 1px solid {THEME['danger']}88;
                color: {THEME['danger']}; font-size: 14px; font-weight: 700;
            """)

    # ── UPI tab ──
    def _upi_tab(self):
        w = QWidget()
        w.setStyleSheet(f"background: {THEME['card']};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        upi_row = QHBoxLayout()
        upi_lbl = QLabel("UPI ID:")
        upi_lbl.setStyleSheet(f"color:{THEME['text2']}; font-size:12px;")
        self.upi_id_input = QLineEdit(self.upi_id)
        self.upi_id_input.setPlaceholderText("yourname@upi")
        self.upi_id_input.setFixedHeight(40)
        gen_qr_btn = styled_btn("Generate", THEME["upi"], h=40)
        gen_qr_btn.setFixedWidth(100)
        gen_qr_btn.clicked.connect(self.generate_upi_qr)
        upi_row.addWidget(upi_lbl)
        upi_row.addWidget(self.upi_id_input)
        upi_row.addWidget(gen_qr_btn)
        lay.addLayout(upi_row)

        self.upi_qr_label = QLabel()
        self.upi_qr_label.setFixedSize(200, 200)
        self.upi_qr_label.setAlignment(Qt.AlignCenter)
        self.upi_qr_label.setStyleSheet(f"""
            background: white; border-radius: 12px;
            border: 2px solid {THEME['upi']};
        """)

        qr_wrap = QHBoxLayout()
        qr_wrap.addStretch()
        qr_wrap.addWidget(self.upi_qr_label)
        qr_wrap.addStretch()
        lay.addLayout(qr_wrap)

        self.upi_info = QLabel("Enter UPI ID and click Generate")
        self.upi_info.setAlignment(Qt.AlignCenter)
        self.upi_info.setStyleSheet(f"color:{THEME['text2']}; font-size:11px;")
        lay.addWidget(self.upi_info)

        lay.addStretch()
        if self.upi_id:
            self.generate_upi_qr()
        return w

    def generate_upi_qr(self):
        uid   = self.upi_id_input.text().strip()
        total = self.total
        if not uid:
            QMessageBox.warning(self, "No UPI ID", "Please enter a UPI ID first.")
            return
        upi_url = f"upi://pay?pa={uid}&am={total:.2f}&cu=INR"
        qr_img  = qrcode.make(upi_url)
        buf = io.BytesIO()
        qr_img.save(buf, format="PNG")
        buf.seek(0)
        qt_img = QImage.fromData(buf.read())
        pix = QPixmap.fromImage(qt_img).scaled(186, 186, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.upi_qr_label.setPixmap(pix)
        self.upi_info.setText(f"Scan to pay  ₹{total:.2f}  →  {uid}")
        self.upi_info.setStyleSheet(f"color:{THEME['accent2']}; font-size:12px; font-weight:600;")

    # ── Card tab ──
    def _card_tab(self):
        w = QWidget()
        w.setStyleSheet(f"background: {THEME['card']};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 24, 20, 24)
        lay.setSpacing(16)

        icon = QLabel("💳")
        icon.setFont(QFont("Segoe UI", 36))
        icon.setAlignment(Qt.AlignCenter)
        lay.addWidget(icon)

        msg = QLabel(f"Please swipe / tap card\nfor  ₹{self.total:.2f}")
        msg.setAlignment(Qt.AlignCenter)
        msg.setFont(QFont("Segoe UI", 14, QFont.Bold))
        msg.setStyleSheet(f"color: {THEME['text']};")
        lay.addWidget(msg)

        sub = QLabel("Use POS terminal to process card payment.\nClick Confirm once transaction is approved.")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"color:{THEME['text2']}; font-size:11px;")
        lay.addWidget(sub)
        lay.addStretch()
        return w

    def confirm_payment(self):
        idx = self.tabs.currentIndex()
        if idx == 0:   # Cash
            if self.cash_input.value() < self.total:
                QMessageBox.warning(self, "Insufficient", "Cash received is less than total amount!")
                return
        elif idx == 1:  # UPI
            if not self.upi_id_input.text().strip():
                QMessageBox.warning(self, "No UPI ID", "Please enter UPI ID and generate QR first.")
                return
        self.paid = True
        self.accept()


# ═══════════════════════════════════════════════════════════
#  MAIN APP
# ═══════════════════════════════════════════════════════════
class BillingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_db()
        self.cart          = []
        self.camera_active = False
        self.cap           = None
        self.last_scanned  = ""
        self.qr_detector   = cv2.QRCodeDetector()
        self.upi_id        = ""
        self.init_ui()

    def init_db(self):
        self.conn = sqlite3.connect('inventory.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS inventory
                             (id TEXT PRIMARY KEY, name TEXT, price REAL, quantity INTEGER)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS bills
                             (bill_id INTEGER PRIMARY KEY, date TEXT, total REAL, method TEXT)''')
        # Add method column if upgrading from old DB
        try:
            self.cursor.execute("ALTER TABLE bills ADD COLUMN method TEXT")
        except Exception:
            pass
        self.conn.commit()

    # ── Main layout ──────────────────────────────────────
    def init_ui(self):
        self.setWindowTitle("✦  POS Billing System")
        self.setGeometry(80, 60, 1400, 820)
        self.setStyleSheet(f"QMainWindow {{ background: {THEME['bg']}; }}")

        root = QWidget()
        self.setCentralWidget(root)
        root_lay = QVBoxLayout(root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        root_lay.addWidget(self._top_bar())

        body = QHBoxLayout()
        body.setContentsMargins(16, 12, 16, 16)
        body.setSpacing(14)
        body.addWidget(self._left_panel(),  48)
        body.addWidget(self._right_panel(), 52)
        root_lay.addLayout(body)

    def _top_bar(self):
        bar = QWidget()
        bar.setFixedHeight(58)
        bar.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 {THEME['panel']}, stop:1 {THEME['card']});
            border-bottom: 1px solid {THEME['border']};
        """)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(22, 0, 22, 0)

        logo = QLabel("✦  POS  SYSTEM")
        logo.setFont(QFont("Segoe UI", 16, QFont.Bold))
        logo.setStyleSheet(f"""
            color: {THEME['accent']};
            letter-spacing: 3px;
        """)
        lay.addWidget(logo)
        lay.addStretch()

        # Clock
        self.clock_lbl = QLabel()
        self.clock_lbl.setStyleSheet(f"color: {THEME['text2']}; font-size: 13px;")
        self._tick()
        clock_timer = QTimer(self)
        clock_timer.timeout.connect(self._tick)
        clock_timer.start(1000)
        lay.addWidget(self.clock_lbl)

        # UPI ID setting
        upi_lbl = QLabel("  UPI ID:")
        upi_lbl.setStyleSheet(f"color:{THEME['text2']}; font-size:12px; margin-left:20px;")
        lay.addWidget(upi_lbl)
        self.upi_bar_input = QLineEdit()
        self.upi_bar_input.setPlaceholderText("yourname@upi")
        self.upi_bar_input.setFixedWidth(180)
        self.upi_bar_input.setFixedHeight(32)
        self.upi_bar_input.setStyleSheet(f"""
            QLineEdit {{
                background: {THEME['card']};
                color: {THEME['text']};
                border: 1px solid {THEME['border']};
                border-radius: 7px;
                padding: 4px 10px;
                font-size: 12px;
            }}
            QLineEdit:focus {{ border: 1px solid {THEME['accent']}; }}
        """)
        self.upi_bar_input.textChanged.connect(lambda t: setattr(self, 'upi_id', t))
        lay.addWidget(self.upi_bar_input)

        return bar

    def _tick(self):
        self.clock_lbl.setText(datetime.now().strftime("%a, %d %b  %H:%M:%S"))

    # ── LEFT PANEL ───────────────────────────────────────
    def _left_panel(self):
        w = QWidget()
        w.setStyleSheet(f"background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        lay.addWidget(self._scanner_card())
        lay.addWidget(self._inventory_card(), 1)
        return w

    def _scanner_card(self):
        f = card_frame(14)
        lay = QVBoxLayout(f)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        hdr = QHBoxLayout()
        t = QLabel("  SCANNER")
        t.setFont(QFont("Segoe UI", 13, QFont.Bold))
        t.setStyleSheet(f"color: {THEME['text']}; letter-spacing: 1px;")
        dot = QLabel("●")
        self.cam_dot = dot
        dot.setStyleSheet(f"color: {THEME['text3']}; font-size: 10px;")
        hdr.addWidget(dot); hdr.addWidget(t); hdr.addStretch()
        lay.addLayout(hdr)

        # Camera feed
        self.camera_label = QLabel("📷  Press Start Camera")
        self.camera_label.setFixedSize(430, 260)
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setStyleSheet(f"""
            background: {THEME['bg']};
            color: {THEME['text3']};
            border: 1px solid {THEME['border']};
            border-radius: 10px;
            font-size: 13px;
        """)
        lay.addWidget(self.camera_label)

        # Cam buttons
        cam_row = QHBoxLayout()
        self.start_btn = styled_btn("▶  Start Camera", THEME["accent2"], h=36)
        self.start_btn.clicked.connect(self.start_camera)
        self.stop_btn  = styled_btn("⏹  Stop", THEME["danger"], h=36)
        self.stop_btn.clicked.connect(self.stop_camera)
        self.stop_btn.setEnabled(False)
        cam_row.addWidget(self.start_btn); cam_row.addWidget(self.stop_btn)
        lay.addLayout(cam_row)

        self.scan_status = QLabel("Status: Camera off")
        self.scan_status.setStyleSheet(f"color:{THEME['text3']}; font-size: 11px;")
        lay.addWidget(self.scan_status)

        # Manual
        sep_lbl = QLabel("── manual entry ──")
        sep_lbl.setAlignment(Qt.AlignCenter)
        sep_lbl.setStyleSheet(f"color:{THEME['text3']}; font-size: 10px;")
        lay.addWidget(sep_lbl)

        man_row = QHBoxLayout()
        self.qr_input = QLineEdit()
        self.qr_input.setPlaceholderText("Type Product ID and press Enter")
        self.qr_input.setFixedHeight(38)
        self.qr_input.setStyleSheet(f"""
            QLineEdit {{
                background: {THEME['card']};
                color: {THEME['text']};
                border: 1px solid {THEME['border']};
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{ border: 1px solid {THEME['accent']}; }}
        """)
        self.qr_input.returnPressed.connect(self.manual_add)
        man_row.addWidget(self.qr_input)
        add_btn = styled_btn("Add", THEME["accent"], h=38)
        add_btn.setFixedWidth(70)
        add_btn.clicked.connect(self.manual_add)
        man_row.addWidget(add_btn)
        lay.addLayout(man_row)

        return f

    def _inventory_card(self):
        f = card_frame(14)
        lay = QVBoxLayout(f)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        hdr = QHBoxLayout()
        t = QLabel("  INVENTORY")
        t.setFont(QFont("Segoe UI", 13, QFont.Bold))
        t.setStyleSheet(f"color: {THEME['text']}; letter-spacing: 1px;")
        hdr.addWidget(t); hdr.addStretch()

        add_btn = styled_btn("＋ Add Product", THEME["accent"], h=32)
        add_btn.setFixedWidth(130)
        add_btn.clicked.connect(self.show_add_product_dialog)
        hdr.addWidget(add_btn)
        lay.addLayout(hdr)

        self.inventory_table = self._make_table(["ID", "Name", "Price", "Qty", "QR"])
        self.inventory_table.setColumnWidth(4, 50)
        self.inventory_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.refresh_inventory()
        lay.addWidget(self.inventory_table)
        return f

    # ── RIGHT PANEL ──────────────────────────────────────
    def _right_panel(self):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        lay.addWidget(self._cart_card(), 1)
        lay.addWidget(self._total_card())
        return w

    def _cart_card(self):
        f = card_frame(14)
        lay = QVBoxLayout(f)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        hdr = QHBoxLayout()
        t = QLabel("  SHOPPING CART")
        t.setFont(QFont("Segoe UI", 13, QFont.Bold))
        t.setStyleSheet(f"color: {THEME['text']}; letter-spacing: 1px;")
        self.item_count_lbl = QLabel("0 items")
        self.item_count_lbl.setStyleSheet(f"""
            background: {THEME['accent']}33;
            color: {THEME['accent']};
            border-radius: 10px;
            padding: 2px 10px;
            font-size: 11px;
            font-weight: 700;
        """)
        hdr.addWidget(t); hdr.addStretch(); hdr.addWidget(self.item_count_lbl)
        lay.addLayout(hdr)

        self.cart_table = self._make_table(["Product", "Price", "Qty", "Total", "✕"])
        self.cart_table.setColumnWidth(4, 40)
        self.cart_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        lay.addWidget(self.cart_table)
        return f

    def _total_card(self):
        f = card_frame(14)
        lay = QVBoxLayout(f)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(10)

        row1 = QHBoxLayout()
        subtotal_lbl = QLabel("Subtotal")
        subtotal_lbl.setStyleSheet(f"color:{THEME['text2']}; font-size:13px;")
        self.subtotal_val = QLabel("₹0.00")
        self.subtotal_val.setStyleSheet(f"color:{THEME['text']}; font-size:13px;")
        row1.addWidget(subtotal_lbl); row1.addStretch(); row1.addWidget(self.subtotal_val)
        lay.addLayout(row1)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background:{THEME['border']}; max-height:1px; margin: 4px 0;")
        lay.addWidget(sep)

        total_row = QHBoxLayout()
        tot_lbl = QLabel("TOTAL")
        tot_lbl.setFont(QFont("Segoe UI", 16, QFont.Bold))
        tot_lbl.setStyleSheet(f"color:{THEME['text']};")
        self.total_display = QLabel("₹0.00")
        self.total_display.setFont(QFont("Segoe UI", 20, QFont.Bold))
        self.total_display.setStyleSheet(f"color:{THEME['accent2']};")
        total_row.addWidget(tot_lbl); total_row.addStretch(); total_row.addWidget(self.total_display)
        lay.addLayout(total_row)

        btn_row = QHBoxLayout()
        clear_btn = styled_btn("🗑  Clear Cart", THEME["danger"], h=44)
        clear_btn.clicked.connect(self.clear_cart)
        checkout_btn = styled_btn("  CHECKOUT  →", THEME["accent"], h=44)
        checkout_btn.setFont(QFont("Segoe UI", 13, QFont.Bold))
        checkout_btn.clicked.connect(self.checkout)
        btn_row.addWidget(clear_btn, 1)
        btn_row.addWidget(checkout_btn, 2)
        lay.addLayout(btn_row)
        return f

    # ── Table factory ────────────────────────────────────
    def _make_table(self, headers):
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.setStyleSheet(f"""
            QTableWidget {{
                background: {THEME['bg']};
                color: {THEME['text']};
                border: none;
                gridline-color: {THEME['border']};
                selection-background-color: {THEME['accent']}33;
                font-size: 13px;
            }}
            QHeaderView::section {{
                background: {THEME['panel']};
                color: {THEME['text2']};
                border: none;
                border-bottom: 1px solid {THEME['border']};
                padding: 6px;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }}
            QTableWidget::item {{ padding: 6px 8px; border-bottom: 1px solid {THEME['border']}22; }}
            QTableWidget::item:selected {{ background: {THEME['accent']}22; color: {THEME['text']}; }}
            QScrollBar:vertical {{
                background: {THEME['bg']}; width: 6px; border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {THEME['border']}; border-radius: 3px;
            }}
        """)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setSelectionMode(QAbstractItemView.SingleSelection)
        t.setShowGrid(True)
        t.verticalHeader().setVisible(False)
        t.setAlternatingRowColors(False)
        return t

    # ── Camera ───────────────────────────────────────────
    def start_camera(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            QMessageBox.warning(self, "Camera Error", "Cannot open camera!")
            return
        self.camera_active = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.cam_dot.setStyleSheet(f"color:{THEME['success']}; font-size:10px;")
        self.scan_status.setText("🟢 Camera ON — point QR code at camera")
        self.scan_status.setStyleSheet(f"color:{THEME['success']}; font-size:11px;")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def stop_camera(self):
        self.camera_active = False
        if hasattr(self, 'timer'): self.timer.stop()
        if self.cap: self.cap.release(); self.cap = None
        self.camera_label.clear()
        self.camera_label.setText("📷  Press Start Camera")
        self.camera_label.setStyleSheet(f"""
            background: {THEME['bg']}; color: {THEME['text3']};
            border: 1px solid {THEME['border']}; border-radius: 10px; font-size: 13px;
        """)
        self.start_btn.setEnabled(True); self.stop_btn.setEnabled(False)
        self.cam_dot.setStyleSheet(f"color:{THEME['text3']}; font-size:10px;")
        self.scan_status.setText("Status: Camera off")
        self.scan_status.setStyleSheet(f"color:{THEME['text3']}; font-size:11px;")

    def update_frame(self):
        if not self.cap: return
        ret, frame = self.cap.read()
        if not ret: return

        data, bbox, _ = self.qr_detector.detectAndDecode(frame)
        if bbox is not None and data:
            bbox = bbox.astype(int)
            for i in range(len(bbox[0])):
                cv2.line(frame, tuple(bbox[0][i]), tuple(bbox[0][(i+1) % len(bbox[0])]),
                         (0, 230, 150), 3)
            cv2.putText(frame, data, (bbox[0][0][0], bbox[0][0][1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 230, 150), 2)
            if data != self.last_scanned:
                self.last_scanned = data
                self.process_scanned_code(data)
                QTimer.singleShot(2000, lambda: setattr(self, 'last_scanned', ''))

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qt_img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qt_img).scaled(
            self.camera_label.width(), self.camera_label.height(), Qt.KeepAspectRatio)
        self.camera_label.setPixmap(pix)

    def process_scanned_code(self, code):
        self.cursor.execute("SELECT * FROM inventory WHERE id=?", (code,))
        item = self.cursor.fetchone()
        if item:
            self.add_to_cart(item)
            self.scan_status.setText(f"✅  Added: {item[1]}")
            self.scan_status.setStyleSheet(f"color:{THEME['success']}; font-size:11px; font-weight:700;")
        else:
            self.scan_status.setText(f"❌  '{code}' not found")
            self.scan_status.setStyleSheet(f"color:{THEME['danger']}; font-size:11px;")

    # ── Manual add ───────────────────────────────────────
    def manual_add(self):
        code = self.qr_input.text().strip()
        if not code: return
        self.cursor.execute("SELECT * FROM inventory WHERE id=?", (code,))
        item = self.cursor.fetchone()
        if item:
            self.add_to_cart(item)
            self.qr_input.clear()
        else:
            QMessageBox.warning(self, "Not Found", f"Product ID '{code}' not found!")

    # ── Cart ─────────────────────────────────────────────
    def add_to_cart(self, item):
        pid, name, price, qty = item
        if qty <= 0:
            QMessageBox.warning(self, "Out of Stock", f"'{name}' is out of stock!"); return
        for ci in self.cart:
            if ci["id"] == pid:
                ci["quantity"] += 1
                self.update_cart_display(); return
        self.cart.append({"id": pid, "name": name, "price": price, "quantity": 1})
        self.update_cart_display()

    def update_cart_display(self):
        self.cart_table.setRowCount(len(self.cart))
        total = 0
        for row, item in enumerate(self.cart):
            self.cart_table.setItem(row, 0, QTableWidgetItem(item["name"]))
            self.cart_table.setItem(row, 1, QTableWidgetItem(f"₹{item['price']:.2f}"))

            # Editable quantity
            qty_spin = QSpinBox()
            qty_spin.setMinimum(1); qty_spin.setMaximum(999)
            qty_spin.setValue(item["quantity"])
            qty_spin.setStyleSheet(f"""
                QSpinBox {{
                    background:{THEME['bg']}; color:{THEME['text']};
                    border:1px solid {THEME['border']}; border-radius:5px;
                    padding: 2px 4px; font-size:12px;
                }}
            """)
            qty_spin.valueChanged.connect(lambda v, r=row: self.update_qty(r, v))
            self.cart_table.setCellWidget(row, 2, qty_spin)

            item_total = item["price"] * item["quantity"]
            ti = QTableWidgetItem(f"₹{item_total:.2f}")
            ti.setForeground(QColor(THEME["accent2"]))
            self.cart_table.setItem(row, 3, ti)
            total += item_total

            rm_btn = QPushButton("✕")
            rm_btn.setFixedSize(32, 28)
            rm_btn.setStyleSheet(f"""
                QPushButton {{
                    background:{THEME['danger']}22; color:{THEME['danger']};
                    border:1px solid {THEME['danger']}55; border-radius:5px;
                    font-weight:700;
                }}
                QPushButton:hover {{ background:{THEME['danger']}55; }}
            """)
            rm_btn.clicked.connect(lambda _, r=row: self.remove_from_cart(r))
            self.cart_table.setCellWidget(row, 4, rm_btn)

        self.total_display.setText(f"₹{total:.2f}")
        self.subtotal_val.setText(f"₹{total:.2f}")
        count = sum(i["quantity"] for i in self.cart)
        self.item_count_lbl.setText(f"{count} item{'s' if count != 1 else ''}")

    def update_qty(self, row, val):
        if 0 <= row < len(self.cart):
            self.cart[row]["quantity"] = val
            self.update_cart_display()

    def remove_from_cart(self, row):
        if 0 <= row < len(self.cart):
            self.cart.pop(row); self.update_cart_display()

    def clear_cart(self):
        self.cart.clear(); self.update_cart_display()

    # ── Checkout ─────────────────────────────────────────
    def checkout(self):
        if not self.cart:
            QMessageBox.warning(self, "Empty Cart", "Cart is empty!"); return
        total = sum(i["price"] * i["quantity"] for i in self.cart)
        dlg   = PaymentDialog(total, self.upi_id, self)
        if dlg.exec_() and dlg.paid:
            method_map = {0: "Cash", 1: "UPI", 2: "Card"}
            method = method_map.get(dlg.tabs.currentIndex(), "Unknown")
            self.cursor.execute(
                "INSERT INTO bills (date, total, method) VALUES (?, ?, ?)",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), total, method))
            for item in self.cart:
                self.cursor.execute(
                    "UPDATE inventory SET quantity = quantity - ? WHERE id=?",
                    (item["quantity"], item["id"]))
            self.conn.commit()
            QMessageBox.information(self, "✅  Payment Done",
                                    f"Payment successful!\nMethod: {method}\nTotal: ₹{total:.2f}")
            self.clear_cart()
            self.refresh_inventory()

    # ── Inventory ─────────────────────────────────────────
    def refresh_inventory(self):
        self.cursor.execute("SELECT * FROM inventory")
        items = self.cursor.fetchall()
        self.inventory_table.setRowCount(len(items))
        for row, item in enumerate(items):
            self.inventory_table.setItem(row, 0, QTableWidgetItem(item[0]))
            self.inventory_table.setItem(row, 1, QTableWidgetItem(item[1]))
            p = QTableWidgetItem(f"₹{item[2]:.2f}")
            p.setForeground(QColor(THEME["accent2"]))
            self.inventory_table.setItem(row, 2, p)
            qty_item = QTableWidgetItem(str(item[3]))
            if item[3] == 0:
                qty_item.setForeground(QColor(THEME["danger"]))
            elif item[3] < 5:
                qty_item.setForeground(QColor(THEME["warning"]))
            else:
                qty_item.setForeground(QColor(THEME["success"]))
            self.inventory_table.setItem(row, 3, qty_item)

            # QR button
            qr_btn = QPushButton("⊞")
            qr_btn.setFixedSize(34, 28)
            qr_btn.setToolTip("Show QR Code")
            qr_btn.setStyleSheet(f"""
                QPushButton {{
                    background:{THEME['accent']}22; color:{THEME['accent']};
                    border:1px solid {THEME['accent']}55; border-radius:5px;
                    font-size:14px;
                }}
                QPushButton:hover {{ background:{THEME['accent']}55; }}
            """)
            qr_btn.clicked.connect(lambda _, pid=item[0], pname=item[1]:
                                   ProductQRDialog(pid, pname, self).exec_())
            self.inventory_table.setCellWidget(row, 4, qr_btn)

    def show_add_product_dialog(self):
        dlg = AddProductDialog(self.cursor, self.conn, self)
        if dlg.exec_():
            self.refresh_inventory()

    def closeEvent(self, event):
        self.stop_camera()
        self.conn.close()
        event.accept()


# ═══════════════════════════════════════════════════════════
if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window,          QColor(THEME["bg"]))
    palette.setColor(QPalette.WindowText,      QColor(THEME["text"]))
    palette.setColor(QPalette.Base,            QColor(THEME["card"]))
    palette.setColor(QPalette.AlternateBase,   QColor(THEME["panel"]))
    palette.setColor(QPalette.ToolTipBase,     QColor(THEME["card"]))
    palette.setColor(QPalette.ToolTipText,     QColor(THEME["text"]))
    palette.setColor(QPalette.Text,            QColor(THEME["text"]))
    palette.setColor(QPalette.Button,          QColor(THEME["panel"]))
    palette.setColor(QPalette.ButtonText,      QColor(THEME["text"]))
    palette.setColor(QPalette.Highlight,       QColor(THEME["accent"]))
    palette.setColor(QPalette.HighlightedText, QColor("#fff"))
    app.setPalette(palette)

    window = BillingApp()
    window.show()
    sys.exit(app.exec_())
