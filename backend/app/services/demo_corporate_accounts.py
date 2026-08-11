"""Synthetic corporate-style accounts for the hackathon demonstration only.

These credentials do not represent an Active Directory integration and must
not be reused in a production environment.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DemoCorporateTrainee:
    login: str
    password: str
    full_name: str


DEMO_CORPORATE_TRAINEES: tuple[DemoCorporateTrainee, ...] = (
    DemoCorporateTrainee(
        "Matveev.AD@gazprom-neft.ru",
        "GpnDemo#Mat26",
        "Матвеев Александр Дмитриевич",
    ),
    DemoCorporateTrainee(
        "Voronov.NK@gazprom-neft.ru",
        "GpnDemo#Vor26",
        "Воронов Николай Константинович",
    ),
    DemoCorporateTrainee(
        "Sokolov.IV@gazprom-neft.ru",
        "GpnDemo#Sok26",
        "Соколов Иван Викторович",
    ),
    DemoCorporateTrainee(
        "Kuznetsov.MA@gazprom-neft.ru",
        "GpnDemo#Kuz26",
        "Кузнецов Михаил Андреевич",
    ),
    DemoCorporateTrainee(
        "Popov.ES@gazprom-neft.ru",
        "GpnDemo#Pop26",
        "Попов Евгений Сергеевич",
    ),
    DemoCorporateTrainee(
        "Smirnova.OV@gazprom-neft.ru",
        "GpnDemo#Smi26",
        "Смирнова Ольга Викторовна",
    ),
    DemoCorporateTrainee(
        "Petrova.AN@gazprom-neft.ru",
        "GpnDemo#Pet26",
        "Петрова Анна Николаевна",
    ),
    DemoCorporateTrainee(
        "Volkov.DS@gazprom-neft.ru",
        "GpnDemo#Vol26",
        "Волков Дмитрий Сергеевич",
    ),
    DemoCorporateTrainee(
        "Fedorov.PM@gazprom-neft.ru",
        "GpnDemo#Fed26",
        "Федоров Павел Михайлович",
    ),
    DemoCorporateTrainee(
        "Morozova.EV@gazprom-neft.ru",
        "GpnDemo#Mor26",
        "Морозова Елена Викторовна",
    ),
    DemoCorporateTrainee(
        "Lebedev.RA@gazprom-neft.ru",
        "GpnDemo#Leb26",
        "Лебедев Роман Александрович",
    ),
    DemoCorporateTrainee(
        "Novikova.TS@gazprom-neft.ru",
        "GpnDemo#Nov26",
        "Новикова Татьяна Сергеевна",
    ),
    DemoCorporateTrainee(
        "Orlov.KV@gazprom-neft.ru",
        "GpnDemo#Orl26",
        "Орлов Кирилл Викторович",
    ),
    DemoCorporateTrainee(
        "Pavlov.SI@gazprom-neft.ru",
        "GpnDemo#Pav26",
        "Павлов Сергей Игоревич",
    ),
    DemoCorporateTrainee(
        "Semenova.NA@gazprom-neft.ru",
        "GpnDemo#Sem26",
        "Семенова Наталья Александровна",
    ),
    DemoCorporateTrainee(
        "Golubev.VP@gazprom-neft.ru",
        "GpnDemo#Gol26",
        "Голубев Виктор Павлович",
    ),
    DemoCorporateTrainee(
        "Vinogradova.MI@gazprom-neft.ru",
        "GpnDemo#Vin26",
        "Виноградова Мария Игоревна",
    ),
    DemoCorporateTrainee(
        "Bogdanov.AL@gazprom-neft.ru",
        "GpnDemo#Bog26",
        "Богданов Алексей Леонидович",
    ),
    DemoCorporateTrainee(
        "Komarova.ER@gazprom-neft.ru",
        "GpnDemo#Kom26",
        "Комарова Екатерина Романовна",
    ),
    DemoCorporateTrainee(
        "Zakharov.DN@gazprom-neft.ru",
        "GpnDemo#Zak26",
        "Захаров Дмитрий Николаевич",
    ),
)

DEMO_CORPORATE_ACCOUNTS: tuple[tuple[str, str], ...] = tuple(
    (trainee.login, trainee.password)
    for trainee in DEMO_CORPORATE_TRAINEES
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
