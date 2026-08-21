ROLE_ADMIN = "admin"
ROLE_STAFF = "staff"
STAFF_ROLES = (ROLE_ADMIN, ROLE_STAFF)

# Each language's own name in itself, not translated — a language picker
# needs to stay legible to someone who can't currently read the UI language.
LANGUAGE_CHOICES = [
    ("nl", "Nederlands"),
    ("fr", "Français"),
    ("en", "English"),
]

CATALOG_CATEGORIES = [
    ("hems", "Hems"),
    ("waist", "Waist & Fit"),
    ("zippers", "Zippers"),
    ("sleeves", "Sleeves"),
    ("repairs", "Repairs"),
    ("curtains", "Curtains & Home Textiles"),
    ("other", "Other"),
]

CATALOG_CATEGORY_LABELS = dict(CATALOG_CATEGORIES)

VAT_RATE_CHOICES = [
    ("21", "21% (standard)"),
    ("12", "12% (reduced)"),
    ("6", "6% (reduced)"),
    ("0", "0% (exempt)"),
]

INVENTORY_CATEGORIES = [
    ("thread", "Thread & Yarn"),
    ("closures", "Buttons & Closures"),
    ("zippers", "Zippers"),
    ("fabric", "Fabric & Lining"),
    ("interfacing", "Interfacing & Stabilizers"),
    ("notions", "Notions & Trim"),
    ("other", "Other"),
]
INVENTORY_CATEGORY_LABELS = dict(INVENTORY_CATEGORIES)

INVENTORY_UNIT_CHOICES = [
    ("pcs", "Pieces"),
    ("m", "Meters"),
    ("spool", "Spool"),
    ("roll", "Roll"),
    ("set", "Set"),
    ("box", "Box"),
]
INVENTORY_UNIT_LABELS = dict(INVENTORY_UNIT_CHOICES)

STOCK_MOVEMENT_REASON_RECEIVED = "received"
STOCK_MOVEMENT_REASON_CONSUMPTION = "consumption"
STOCK_MOVEMENT_REASON_ADJUSTMENT = "adjustment"
STOCK_MOVEMENT_REASON_WASTE = "waste"

STOCK_MOVEMENT_REASONS = [
    (STOCK_MOVEMENT_REASON_RECEIVED, "Stock received"),
    (STOCK_MOVEMENT_REASON_CONSUMPTION, "Used on order"),
    (STOCK_MOVEMENT_REASON_ADJUSTMENT, "Manual adjustment"),
    (STOCK_MOVEMENT_REASON_WASTE, "Waste / damaged"),
]
STOCK_MOVEMENT_REASON_LABELS = dict(STOCK_MOVEMENT_REASONS)

# Reasons selectable from the manual "Adjust stock" form — received has its
# own dedicated form, consumption is only ever written by order-line code.
STOCK_ADJUST_REASONS = [
    (STOCK_MOVEMENT_REASON_ADJUSTMENT, "Manual adjustment"),
    (STOCK_MOVEMENT_REASON_WASTE, "Waste / damaged"),
]

STOCK_MOVEMENT_REASON_BADGE = {
    STOCK_MOVEMENT_REASON_RECEIVED: "success",
    STOCK_MOVEMENT_REASON_CONSUMPTION: "info",
    STOCK_MOVEMENT_REASON_ADJUSTMENT: "warning",
    STOCK_MOVEMENT_REASON_WASTE: "danger",
}

GARMENT_TYPES = [
    ("trousers", "Trousers"),
    ("dress", "Dress"),
    ("jacket", "Jacket"),
    ("curtain", "Curtain"),
    ("other", "Other"),
]
GARMENT_TYPE_LABELS = dict(GARMENT_TYPES)

ORDER_STATUS_RECEIVED = "received"
ORDER_STATUS_IN_PROGRESS = "in_progress"
ORDER_STATUS_READY = "ready"
ORDER_STATUS_PICKED_UP = "picked_up"
ORDER_STATUS_CANCELLED = "cancelled"

# Linear happy-path progression; cancellation is a separate, always-available branch.
ORDER_STATUS_FLOW = [
    ORDER_STATUS_RECEIVED,
    ORDER_STATUS_IN_PROGRESS,
    ORDER_STATUS_READY,
    ORDER_STATUS_PICKED_UP,
]

ORDER_STATUSES = [
    (ORDER_STATUS_RECEIVED, "Received"),
    (ORDER_STATUS_IN_PROGRESS, "In progress"),
    (ORDER_STATUS_READY, "Ready for pickup"),
    (ORDER_STATUS_PICKED_UP, "Picked up"),
    (ORDER_STATUS_CANCELLED, "Cancelled"),
]
ORDER_STATUS_LABELS = dict(ORDER_STATUSES)

ORDER_STATUS_BADGE = {
    ORDER_STATUS_RECEIVED: "info",
    ORDER_STATUS_IN_PROGRESS: "warning",
    ORDER_STATUS_READY: "success",
    ORDER_STATUS_PICKED_UP: "secondary",
    ORDER_STATUS_CANCELLED: "danger",
}

# Orders still "in the shop" — not yet handed back and not abandoned. Used to
# scope planning/dashboard queries to work that's actually outstanding.
ACTIVE_ORDER_STATUSES = (ORDER_STATUS_RECEIVED, ORDER_STATUS_IN_PROGRESS, ORDER_STATUS_READY)


def next_order_status(current_status):
    """The next status in the linear happy-path flow, or None if there isn't one."""
    if current_status in ORDER_STATUS_FLOW:
        idx = ORDER_STATUS_FLOW.index(current_status)
        if idx + 1 < len(ORDER_STATUS_FLOW):
            return ORDER_STATUS_FLOW[idx + 1]
    return None

PAYMENT_STATUS_UNPAID = "unpaid"
PAYMENT_STATUS_PARTIALLY_PAID = "partially_paid"
PAYMENT_STATUS_PAID = "paid"

PAYMENT_STATUSES = [
    (PAYMENT_STATUS_UNPAID, "Unpaid"),
    (PAYMENT_STATUS_PARTIALLY_PAID, "Partially paid"),
    (PAYMENT_STATUS_PAID, "Paid"),
]
PAYMENT_STATUS_LABELS = dict(PAYMENT_STATUSES)

PAYMENT_STATUS_BADGE = {
    PAYMENT_STATUS_UNPAID: "danger",
    PAYMENT_STATUS_PARTIALLY_PAID: "warning",
    PAYMENT_STATUS_PAID: "success",
}

INVOICE_STATUS_DRAFT = "draft"
INVOICE_STATUS_SENT = "sent"
INVOICE_STATUS_PAID = "paid"
INVOICE_STATUS_OVERDUE = "overdue"

INVOICE_STATUSES = [
    (INVOICE_STATUS_DRAFT, "Draft"),
    (INVOICE_STATUS_SENT, "Sent"),
    (INVOICE_STATUS_PAID, "Paid"),
    (INVOICE_STATUS_OVERDUE, "Overdue"),
]
INVOICE_STATUS_LABELS = dict(INVOICE_STATUSES)

INVOICE_STATUS_BADGE = {
    INVOICE_STATUS_DRAFT: "secondary",
    INVOICE_STATUS_SENT: "info",
    INVOICE_STATUS_PAID: "success",
    INVOICE_STATUS_OVERDUE: "danger",
}
