"""Synthetic corporate-style accounts for the hackathon demonstration only.

These credentials do not represent an Active Directory integration and must
not be reused in a production environment.
"""

DEMO_CORPORATE_ACCOUNTS: tuple[tuple[str, str], ...] = (
    ("Matveev.AD@gazprom-neft.ru", "GpnDemo#Mat26"),
    ("Voronov.NK@gazprom-neft.ru", "GpnDemo#Vor26"),
    ("Sokolov.IV@gazprom-neft.ru", "GpnDemo#Sok26"),
    ("Kuznetsov.MA@gazprom-neft.ru", "GpnDemo#Kuz26"),
    ("Popov.ES@gazprom-neft.ru", "GpnDemo#Pop26"),
    ("Smirnova.OV@gazprom-neft.ru", "GpnDemo#Smi26"),
    ("Petrova.AN@gazprom-neft.ru", "GpnDemo#Pet26"),
    ("Volkov.DS@gazprom-neft.ru", "GpnDemo#Vol26"),
    ("Fedorov.PM@gazprom-neft.ru", "GpnDemo#Fed26"),
    ("Morozova.EV@gazprom-neft.ru", "GpnDemo#Mor26"),
    ("Lebedev.RA@gazprom-neft.ru", "GpnDemo#Leb26"),
    ("Novikova.TS@gazprom-neft.ru", "GpnDemo#Nov26"),
    ("Orlov.KV@gazprom-neft.ru", "GpnDemo#Orl26"),
    ("Pavlov.SI@gazprom-neft.ru", "GpnDemo#Pav26"),
    ("Semenova.NA@gazprom-neft.ru", "GpnDemo#Sem26"),
    ("Golubev.VP@gazprom-neft.ru", "GpnDemo#Gol26"),
    ("Vinogradova.MI@gazprom-neft.ru", "GpnDemo#Vin26"),
    ("Bogdanov.AL@gazprom-neft.ru", "GpnDemo#Bog26"),
    ("Komarova.ER@gazprom-neft.ru", "GpnDemo#Kom26"),
    ("Zakharov.DN@gazprom-neft.ru", "GpnDemo#Zak26"),
)


def _validate_demo_accounts() -> None:
    if len(DEMO_CORPORATE_ACCOUNTS) != 20:
        raise RuntimeError("exactly 20 demo corporate accounts are required")
    logins = [login for login, _password in DEMO_CORPORATE_ACCOUNTS]
    if len(logins) != len(set(logins)):
        raise RuntimeError("demo corporate account logins must be unique")
    if any(len(password) < 12 for _login, password in DEMO_CORPORATE_ACCOUNTS):
        raise RuntimeError("demo corporate account password is shorter than 12")


_validate_demo_accounts()
