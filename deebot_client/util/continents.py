"""Continents module."""
from __future__ import annotations

from deebot_client.const import COUNTRY_CHINA


def get_continent(country: str | None) -> str:
    """Return the continent for the given country or ww."""
    if not country:
        return "ww"
    return COUNTRIES_TO_CONTINENTS.get(country.upper(), "ww")


def get_continent_url_postfix(country: str) -> str:
    """Return the url contintent postfix for the given country."""
    if country == COUNTRY_CHINA:
        return ""

    return f"-{get_continent(country)}"


# Copied from https://github.com/mrbungle64/ecovacs-deebot.js/blob/master/countries.json on 11.01.2024
COUNTRIES_TO_CONTINENTS = {
    "AD": "eu",
    "AE": "as",
    "AF": "as",
    "AG": "na",
    "AI": "na",
    "AL": "eu",
    "AM": "as",
    "AO": "ww",
    "AQ": "ww",
    "AR": "ww",
    "AS": "ww",
    "AT": "eu",
    "AU": "ww",
    "AW": "na",
    "AX": "eu",
    "AZ": "as",
    "BA": "eu",
    "BB": "na",
    "BD": "as",
    "BE": "eu",
    "BF": "ww",
    "BG": "eu",
    "BH": "as",
    "BI": "ww",
    "BJ": "ww",
    "BL": "na",
    "BM": "na",
    "BN": "as",
    "BO": "ww",
    "BQ": "na",
    "BR": "ww",
    "BS": "na",
    "BT": "as",
    "BV": "ww",
    "BW": "ww",
    "BY": "eu",
    "BZ": "na",
    "CA": "na",
    "CC": "as",
    "CD": "ww",
    "CF": "ww",
    "CG": "ww",
    "CH": "eu",
    "CI": "ww",
    "CK": "ww",
    "CL": "ww",
    "CM": "ww",
    COUNTRY_CHINA: "ww",
    "CO": "ww",
    "CR": "na",
    "CU": "na",
    "CV": "ww",
    "CW": "na",
    "CX": "as",
    "CY": "eu",
    "CZ": "eu",
    "DE": "eu",
    "DJ": "ww",
    "DK": "eu",
    "DM": "na",
    "DO": "na",
    "DZ": "ww",
    "EC": "ww",
    "EE": "eu",
    "EG": "ww",
    "EH": "ww",
    "ER": "ww",
    "ES": "eu",
    "ET": "ww",
    "FI": "eu",
    "FJ": "ww",
    "FK": "ww",
    "FM": "ww",
    "FO": "eu",
    "FR": "eu",
    "GA": "ww",
    "GB": "eu",
    "GD": "na",
    "GE": "as",
    "GF": "ww",
    "GG": "eu",
    "GH": "ww",
    "GI": "eu",
    "GL": "na",
    "GM": "ww",
    "GN": "ww",
    "GP": "na",
    "GQ": "ww",
    "GR": "eu",
    "GS": "ww",
    "GT": "na",
    "GU": "ww",
    "GW": "ww",
    "GY": "ww",
    "HK": "as",
    "HM": "ww",
    "HN": "na",
    "HR": "eu",
    "HT": "na",
    "HU": "eu",
    "ID": "as",
    "IE": "eu",
    "IL": "as",
    "IM": "eu",
    "IN": "as",
    "IO": "as",
    "IQ": "as",
    "IR": "as",
    "IS": "eu",
    "IT": "eu",
    "JE": "eu",
    "JM": "na",
    "JO": "as",
    "JP": "as",
    "KE": "ww",
    "KG": "as",
    "KH": "as",
    "KI": "ww",
    "KM": "ww",
    "KN": "na",
    "KP": "as",
    "KR": "as",
    "KW": "as",
    "KY": "na",
    "KZ": "as",
    "LA": "as",
    "LB": "as",
    "LC": "na",
    "LI": "eu",
    "LK": "as",
    "LR": "ww",
    "LS": "ww",
    "LT": "eu",
    "LU": "eu",
    "LV": "eu",
    "LY": "ww",
    "MA": "ww",
    "MC": "eu",
    "MD": "eu",
    "ME": "eu",
    "MF": "na",
    "MG": "ww",
    "MH": "ww",
    "MK": "eu",
    "ML": "ww",
    "MM": "as",
    "MN": "as",
    "MO": "as",
    "MP": "ww",
    "MQ": "na",
    "MR": "ww",
    "MS": "na",
    "MT": "eu",
    "MU": "ww",
    "MV": "as",
    "MW": "ww",
    "MX": "na",
    "MY": "as",
    "MZ": "ww",
    "na": "ww",
    "NC": "ww",
    "NE": "ww",
    "NF": "ww",
    "NG": "ww",
    "NI": "na",
    "NL": "eu",
    "NO": "eu",
    "NP": "as",
    "NR": "ww",
    "NU": "ww",
    "NZ": "ww",
    "OM": "as",
    "PA": "na",
    "PE": "ww",
    "PF": "ww",
    "PG": "ww",
    "PH": "as",
    "PK": "as",
    "PL": "eu",
    "PM": "na",
    "PN": "ww",
    "PR": "na",
    "PS": "as",
    "PT": "eu",
    "PW": "ww",
    "PY": "ww",
    "QA": "as",
    "RE": "ww",
    "RO": "eu",
    "RS": "eu",
    "RU": "eu",
    "RW": "ww",
    "SA": "as",
    "SB": "ww",
    "SC": "ww",
    "SD": "ww",
    "SE": "eu",
    "SG": "as",
    "SH": "ww",
    "SI": "eu",
    "SJ": "eu",
    "SK": "eu",
    "SL": "ww",
    "SM": "eu",
    "SN": "ww",
    "SO": "ww",
    "SR": "ww",
    "SS": "ww",
    "ST": "ww",
    "SV": "na",
    "SX": "na",
    "SY": "as",
    "SZ": "ww",
    "TC": "na",
    "TD": "ww",
    "TF": "ww",
    "TG": "ww",
    "TH": "as",
    "TJ": "as",
    "TK": "ww",
    "TL": "ww",
    "TM": "as",
    "TN": "ww",
    "TO": "ww",
    "TR": "as",
    "TT": "na",
    "TV": "ww",
    "TW": "as",
    "TZ": "ww",
    "UA": "eu",
    "UG": "ww",
    "UK": "eu",
    "UM": "ww",
    "US": "na",
    "UY": "ww",
    "UZ": "as",
    "VA": "eu",
    "VC": "na",
    "VE": "ww",
    "VG": "na",
    "VI": "na",
    "VN": "as",
    "VU": "ww",
    "WF": "ww",
    "WS": "ww",
    "XK": "eu",
    "YE": "as",
    "YT": "ww",
    "ZA": "ww",
    "ZM": "ww",
    "ZW": "ww",
}
