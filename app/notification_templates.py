"""Notification copy per language. Separate from Flask-Babel's UI-string
catalogs (Milestone 7) since these are long-form, placeholder-driven message
bodies rather than short UI labels."""

NOTIFICATION_TEMPLATES = {
    "order_ready": {
        "nl": {
            "subject": "Uw kledingstuk is klaar - {order_code}",
            "body": (
                "Beste {client_name},\n\n"
                "Goed nieuws! Uw bestelling {order_code} bij {shop_name} is klaar en kan worden opgehaald.\n\n"
                "{portal_line}"
                "Met vriendelijke groeten,\n"
                "{shop_name}"
            ),
        },
        "fr": {
            "subject": "Votre vêtement est prêt - {order_code}",
            "body": (
                "Bonjour {client_name},\n\n"
                "Bonne nouvelle ! Votre commande {order_code} chez {shop_name} est prête et peut être récupérée.\n\n"
                "{portal_line}"
                "Cordialement,\n"
                "{shop_name}"
            ),
        },
        "en": {
            "subject": "Your garment is ready - {order_code}",
            "body": (
                "Hi {client_name},\n\n"
                "Good news! Your order {order_code} at {shop_name} is ready for pickup.\n\n"
                "{portal_line}"
                "Kind regards,\n"
                "{shop_name}"
            ),
        },
    },
}

PORTAL_LINE = {
    "nl": "Volg uw bestelling hier: {portal_url}\n\n",
    "fr": "Suivez votre commande ici : {portal_url}\n\n",
    "en": "Track your order here: {portal_url}\n\n",
}
