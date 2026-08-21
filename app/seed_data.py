"""Static demo/seed data. Kept separate from app/cli.py so the command stays readable."""

# (name, category, description, price, vat_rate, estimated_minutes)
CATALOG_SEED = [
    ("Trouser hem (machine stitch)", "hems", None, "12.00", "21", 20),
    ("Trouser hem (blind stitch)", "hems", "Invisible finish, no visible stitching.", "16.00", "21", 25),
    ("Jeans original hem (keep factory hem)", "hems", "Preserves the original hem and fading.", "18.00", "21", 30),
    ("Skirt hem", "hems", None, "14.00", "21", 20),
    ("Dress hem", "hems", None, "18.00", "21", 30),
    ("Curtain hem (per panel)", "hems", None, "15.00", "21", 25),
    ("Take in waist (trousers)", "waist", None, "16.00", "21", 25),
    ("Let out waist (trousers)", "waist", None, "18.00", "21", 30),
    ("Take in waist (skirt)", "waist", None, "16.00", "21", 25),
    ("Take in sides (dress)", "waist", None, "22.00", "21", 40),
    ("Add elastic waistband", "waist", None, "14.00", "21", 20),
    ("Resize jacket waist", "waist", None, "24.00", "21", 45),
    ("Replace trouser zipper", "zippers", None, "14.00", "6", 25),
    ("Replace jacket zipper", "zippers", None, "22.00", "6", 40),
    ("Replace dress zipper (invisible)", "zippers", None, "20.00", "6", 35),
    ("Replace skirt zipper", "zippers", None, "16.00", "6", 25),
    ("Shorten sleeves (shirt)", "sleeves", None, "14.00", "21", 20),
    ("Shorten sleeves (jacket, with cuff)", "sleeves", None, "26.00", "21", 45),
    ("Take in sleeves (jacket)", "sleeves", None, "22.00", "21", 35),
    ("Shorten sleeves (coat)", "sleeves", None, "24.00", "21", 40),
    ("Patch small tear", "repairs", None, "10.00", "6", 15),
    ("Reinforce seam", "repairs", None, "8.00", "6", 10),
    ("Replace button (each)", "repairs", None, "3.00", "6", 5),
    ("Repair lining", "repairs", None, "16.00", "6", 25),
    ("Darn moth hole", "repairs", None, "12.00", "6", 20),
    ("Reattach pocket", "repairs", None, "10.00", "6", 15),
    ("Curtain resize (width)", "curtains", None, "20.00", "21", 35),
    ("Add curtain tape/hooks", "curtains", None, "12.00", "21", 20),
    ("Tablecloth hem", "curtains", None, "14.00", "21", 20),
    ("Custom alteration (priced at intake)", "other", "Use for one-off work not covered above.", "0.00", "21", 15),
    ("Express/rush surcharge", "other", "Add-on for expedited turnaround.", "10.00", "21", 0),
]

# (name, sku, category, description, unit, price, vat_rate, initial_quantity, low_stock_threshold)
INVENTORY_SEED = [
    ("Polyester thread — black (spool)", "THR-BLK-001", "thread", None, "spool", "3.50", "21", "40", "10"),
    ("Polyester thread — white (spool)", "THR-WHT-001", "thread", None, "spool", "3.50", "21", "35", "10"),
    ("Polyester thread — navy (spool)", "THR-NVY-001", "thread", None, "spool", "3.50", "21", "18", "10"),
    ("Invisible zipper 20cm — black", "ZIP-INV-20-BLK", "zippers", None, "pcs", "2.20", "6", "25", "8"),
    ("Trouser zipper 15cm — black", "ZIP-TRS-15-BLK", "zippers", None, "pcs", "1.80", "6", "30", "8"),
    ("Shirt buttons 11mm — white (each)", "BTN-SHT-11-WHT", "closures", None, "pcs", "0.15", "6", "200", "50"),
    ("Suit buttons 18mm — horn look (each)", "BTN-SUIT-18", "closures", None, "pcs", "0.60", "6", "60", "20"),
    ("Hook & eye set", "CLO-HOOK-001", "closures", None, "set", "0.90", "6", "40", "10"),
    ("Fusible interfacing — medium (per meter)", "INT-MED-001", "interfacing", None, "m", "4.00", "21", "22.5", "5"),
    ("Fusible interfacing — light (per meter)", "INT-LGT-001", "interfacing", None, "m", "3.50", "21", "15.0", "5"),
    ("Lining fabric — black (per meter)", "FAB-LIN-BLK", "fabric", None, "m", "6.50", "21", "12.0", "4"),
    ("Lining fabric — beige (per meter)", "FAB-LIN-BGE", "fabric", None, "m", "6.50", "21", "3.0", "4"),
    ("Elastic waistband — 25mm (per meter)", "NOT-ELA-25", "notions", None, "m", "1.20", "21", "18.0", "5"),
    ("Bias binding tape (roll)", "NOT-BIAS-001", "notions", None, "roll", "2.80", "21", "9", "3"),
    ("Curtain hooks (per box of 50)", "NOT-CURH-050", "notions", None, "box", "4.00", "21", "6", "2"),
]

# (name, phone, email, preferred_language, notes, consent_notifications)
DEMO_CLIENTS = [
    ("Sofie Peeters", "+32 470 12 34 56", "sofie.peeters@example.com", "nl", "Always hems 2 cm shorter than measured.", True),
    ("Marie Lefebvre", "+32 471 22 33 44", "marie.lefebvre@example.com", "fr", None, True),
    ("Ahmed El Amrani", "+32 472 55 66 77", "ahmed.elamrani@example.com", "nl", None, True),
    ("Els Van Damme", "+32 473 88 99 00", "els.vandamme@example.com", "nl", "Prefers pickup after 17:00.", False),
    ("Julien Moreau", "+32 474 11 22 33", "julien.moreau@example.com", "fr", None, True),
    ("Anna Kowalski", "+32 475 44 55 66", "anna.kowalski@example.com", "en", None, True),
    ("Peter Janssens", "+32 476 77 88 99", None, "nl", "Regular customer, tailoring for work suits.", True),
    ("Camille Petit", "+32 477 00 11 22", "camille.petit@example.com", "fr", None, True),
]

# Demo orders exercising every status. catalog_item names must match CATALOG_SEED entries.
DEMO_ORDERS = [
    {
        "client": "Sofie Peeters",
        "status": "ready",
        "payment_status": "unpaid",
        "promised_offset_days": -1,
        "express": False,
        "garments": [
            {
                "type": "trousers",
                "color": "Navy",
                "brand": "Zara",
                "lines": ["Trouser hem (machine stitch)"],
            }
        ],
    },
    {
        "client": "Marie Lefebvre",
        "status": "in_progress",
        "payment_status": "unpaid",
        "promised_offset_days": 2,
        "express": True,
        "garments": [
            {
                "type": "dress",
                "color": "Emerald green",
                "brand": None,
                "lines": [
                    "Dress hem",
                    "Replace dress zipper (invisible)",
                    ("inventory", "Invisible zipper 20cm — black"),
                ],
            }
        ],
    },
    {
        "client": "Ahmed El Amrani",
        "status": "received",
        "payment_status": "unpaid",
        "promised_offset_days": 5,
        "express": False,
        "garments": [
            {
                "type": "jacket",
                "color": "Charcoal",
                "brand": "Suitsupply",
                "lines": ["Shorten sleeves (jacket, with cuff)", "Take in sleeves (jacket)"],
            }
        ],
    },
    {
        "client": "Els Van Damme",
        "status": "picked_up",
        "payment_status": "paid",
        "promised_offset_days": -6,
        "express": False,
        "garments": [
            {
                "type": "curtain",
                "color": "Cream",
                "brand": None,
                "lines": ["Curtain hem (per panel)", "Add curtain tape/hooks"],
            }
        ],
    },
    {
        "client": "Julien Moreau",
        "status": "cancelled",
        "payment_status": "unpaid",
        "promised_offset_days": 3,
        "express": False,
        "garments": [
            {
                "type": "trousers",
                "color": "Grey",
                "brand": None,
                "lines": ["Take in waist (trousers)"],
            }
        ],
    },
    {
        "client": "Peter Janssens",
        "status": "in_progress",
        "payment_status": "partially_paid",
        "promised_offset_days": -2,
        "express": False,
        "garments": [
            {
                "type": "jacket",
                "color": "Navy",
                "brand": "Hugo Boss",
                "lines": ["Resize jacket waist"],
            },
            {
                "type": "trousers",
                "color": "Navy",
                "brand": "Hugo Boss",
                "lines": ["Take in waist (trousers)", "Trouser hem (blind stitch)"],
            },
        ],
    },
]
