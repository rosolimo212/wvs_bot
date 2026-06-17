#!/usr/bin/env python3
# coding: utf-8
"""Генерирует data/country_profiles.json по кодам из country_data.csv."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "country_data.csv"
OUT_PATH = ROOT / "data" / "country_profiles.json"

# Оценочные справочные значения для MVP (ВВП на душу — USD, население — чел.).
PROFILES: dict[str, dict] = {
    "AND": {"full_name": "Андорра", "government_type": "парламентская кооринция", "gdp_per_capita_usd": 42000, "population": 79000, "flight_hours_from_london": 2.0},
    "ARG": {"full_name": "Аргентина", "government_type": "президентская республика", "gdp_per_capita_usd": 14000, "population": 46000000, "flight_hours_from_london": 14.0},
    "ARM": {"full_name": "Армения", "government_type": "парламентская республика", "gdp_per_capita_usd": 7000, "population": 2800000, "flight_hours_from_london": 5.5},
    "AUS": {"full_name": "Австралия", "government_type": "конституционная монархия", "gdp_per_capita_usd": 65000, "population": 26000000, "flight_hours_from_london": 22.0},
    "BGD": {"full_name": "Бангладеш", "government_type": "парламентская республика", "gdp_per_capita_usd": 2600, "population": 170000000, "flight_hours_from_london": 10.5},
    "BOL": {"full_name": "Боливия", "government_type": "президентская республика", "gdp_per_capita_usd": 3600, "population": 12000000, "flight_hours_from_london": 14.5},
    "BRA": {"full_name": "Бразилия", "government_type": "президентская федеративная республика", "gdp_per_capita_usd": 9000, "population": 215000000, "flight_hours_from_london": 12.0},
    "CAN": {"full_name": "Канада", "government_type": "конституционная монархия", "gdp_per_capita_usd": 52000, "population": 39000000, "flight_hours_from_london": 8.0},
    "CHL": {"full_name": "Чили", "government_type": "президентская республика", "gdp_per_capita_usd": 16000, "population": 19600000, "flight_hours_from_london": 15.0},
    "CHN": {"full_name": "Китай", "government_type": "однопартийная республика", "gdp_per_capita_usd": 12500, "population": 1410000000, "flight_hours_from_london": 11.0},
    "COL": {"full_name": "Колумбия", "government_type": "президентская республика", "gdp_per_capita_usd": 6600, "population": 52000000, "flight_hours_from_london": 11.5},
    "CYP": {"full_name": "Кипр", "government_type": "президентская республика", "gdp_per_capita_usd": 32000, "population": 1200000, "flight_hours_from_london": 4.5},
    "CZE": {"full_name": "Чехия", "government_type": "парламентская республика", "gdp_per_capita_usd": 27000, "population": 10500000, "flight_hours_from_london": 2.0},
    "DEU": {"full_name": "Германия", "government_type": "федеративная парламентская республика", "gdp_per_capita_usd": 48000, "population": 84000000, "flight_hours_from_london": 1.5},
    "ECU": {"full_name": "Эквадор", "government_type": "президентская республика", "gdp_per_capita_usd": 6400, "population": 18000000, "flight_hours_from_london": 13.0},
    "ETH": {"full_name": "Эфиопия", "government_type": "федеративная парламентская республика", "gdp_per_capita_usd": 1100, "population": 120000000, "flight_hours_from_london": 8.0},
    "GBR": {"full_name": "Великобритания", "government_type": "конституционная монархия", "gdp_per_capita_usd": 46000, "population": 67000000, "flight_hours_from_london": 0.0},
    "GRC": {"full_name": "Греция", "government_type": "парламентская республика", "gdp_per_capita_usd": 21000, "population": 10400000, "flight_hours_from_london": 3.5},
    "GTM": {"full_name": "Гватемала", "government_type": "президентская республика", "gdp_per_capita_usd": 5200, "population": 18000000, "flight_hours_from_london": 11.5},
    "HKG": {"full_name": "Гонконг", "government_type": "специальный административный регион", "gdp_per_capita_usd": 49000, "population": 7500000, "flight_hours_from_london": 12.5},
    "IDN": {"full_name": "Индонезия", "government_type": "президентская республика", "gdp_per_capita_usd": 4800, "population": 275000000, "flight_hours_from_london": 14.5},
    "IND": {"full_name": "Индия", "government_type": "федеративная парламентская республика", "gdp_per_capita_usd": 2400, "population": 1400000000, "flight_hours_from_london": 9.0},
    "IRN": {"full_name": "Иран", "government_type": "теократическая республика", "gdp_per_capita_usd": 4500, "population": 87000000, "flight_hours_from_london": 6.5},
    "IRQ": {"full_name": "Ирак", "government_type": "парламентская федеративная республика", "gdp_per_capita_usd": 6000, "population": 43000000, "flight_hours_from_london": 5.5},
    "JOR": {"full_name": "Иордания", "government_type": "конституционная монархия", "gdp_per_capita_usd": 4300, "population": 11000000, "flight_hours_from_london": 5.0},
    "JPN": {"full_name": "Япония", "government_type": "конституционная монархия", "gdp_per_capita_usd": 34000, "population": 125000000, "flight_hours_from_london": 12.0},
    "KAZ": {"full_name": "Казахстан", "government_type": "президентская республика", "gdp_per_capita_usd": 11000, "population": 19000000, "flight_hours_from_london": 7.0},
    "KEN": {"full_name": "Кения", "government_type": "президентская республика", "gdp_per_capita_usd": 2100, "population": 55000000, "flight_hours_from_london": 8.5},
    "KGZ": {"full_name": "Кыргызстан", "government_type": "парламентская республика", "gdp_per_capita_usd": 1600, "population": 7000000, "flight_hours_from_london": 8.0},
    "KOR": {"full_name": "Республика Корея", "government_type": "президентская республика", "gdp_per_capita_usd": 32000, "population": 52000000, "flight_hours_from_london": 11.5},
    "LBN": {"full_name": "Ливан", "government_type": "парламентская республика", "gdp_per_capita_usd": 3500, "population": 5500000, "flight_hours_from_london": 4.5},
    "LBY": {"full_name": "Ливия", "government_type": "переходное правительство", "gdp_per_capita_usd": 6500, "population": 7000000, "flight_hours_from_london": 4.0},
    "MAC": {"full_name": "Макао", "government_type": "специальный административный регион", "gdp_per_capita_usd": 44000, "population": 700000, "flight_hours_from_london": 12.5},
    "MAR": {"full_name": "Марокко", "government_type": "конституционная монархия", "gdp_per_capita_usd": 3800, "population": 37000000, "flight_hours_from_london": 3.5},
    "MDV": {"full_name": "Мальдивы", "government_type": "президентская республика", "gdp_per_capita_usd": 12000, "population": 520000, "flight_hours_from_london": 10.5},
    "MEX": {"full_name": "Мексика", "government_type": "федеративная президентская республика", "gdp_per_capita_usd": 11000, "population": 128000000, "flight_hours_from_london": 11.0},
    "MMR": {"full_name": "Мьянма", "government_type": "военная хунта", "gdp_per_capita_usd": 1400, "population": 54000000, "flight_hours_from_london": 12.5},
    "MNG": {"full_name": "Монголия", "government_type": "полупрезидентская республика", "gdp_per_capita_usd": 5000, "population": 3400000, "flight_hours_from_london": 10.0},
    "MYS": {"full_name": "Малайзия", "government_type": "федеративная конституционная монархия", "gdp_per_capita_usd": 12000, "population": 34000000, "flight_hours_from_london": 13.0},
    "NGA": {"full_name": "Нигерия", "government_type": "федеративная президентская республика", "gdp_per_capita_usd": 2200, "population": 220000000, "flight_hours_from_london": 6.5},
    "NIC": {"full_name": "Никарагуа", "government_type": "президентская республика", "gdp_per_capita_usd": 2300, "population": 6900000, "flight_hours_from_london": 12.0},
    "NIR": {"full_name": "Северная Ирландия", "government_type": "конституционная монархия (часть Великобритании)", "gdp_per_capita_usd": 35000, "population": 1900000, "flight_hours_from_london": 1.5},
    "NLD": {"full_name": "Нидерланды", "government_type": "конституционная монархия", "gdp_per_capita_usd": 57000, "population": 17500000, "flight_hours_from_london": 1.2},
    "NZL": {"full_name": "Новая Зеландия", "government_type": "конституционная монархия", "gdp_per_capita_usd": 48000, "population": 5100000, "flight_hours_from_london": 24.0},
    "PAK": {"full_name": "Пакистан", "government_type": "федеративная исламская республика", "gdp_per_capita_usd": 1600, "population": 230000000, "flight_hours_from_london": 8.0},
    "PER": {"full_name": "Перу", "government_type": "президентская унитарная республика", "gdp_per_capita_usd": 7200, "population": 34000000, "flight_hours_from_london": 14.5},
    "PHL": {"full_name": "Филиппины", "government_type": "президентская республика", "gdp_per_capita_usd": 3800, "population": 115000000, "flight_hours_from_london": 14.5},
    "PRI": {"full_name": "Пуэрто-Рико", "government_type": "территория США", "gdp_per_capita_usd": 22000, "population": 3200000, "flight_hours_from_london": 9.0},
    "ROU": {"full_name": "Румыния", "government_type": "полупрезидентская республика", "gdp_per_capita_usd": 15000, "population": 19000000, "flight_hours_from_london": 3.0},
    "RUS": {"full_name": "Россия", "government_type": "президентская федеративная республика", "gdp_per_capita_usd": 12000, "population": 146000000, "flight_hours_from_london": 4.0},
    "SGP": {"full_name": "Сингапур", "government_type": "парламентская республика", "gdp_per_capita_usd": 65000, "population": 5900000, "flight_hours_from_london": 13.0},
    "SRB": {"full_name": "Сербия", "government_type": "парламентская республика", "gdp_per_capita_usd": 9000, "population": 6800000, "flight_hours_from_london": 3.0},
    "SVK": {"full_name": "Словакия", "government_type": "парламентская республика", "gdp_per_capita_usd": 21000, "population": 5400000, "flight_hours_from_london": 2.5},
    "THA": {"full_name": "Таиланд", "government_type": "конституционная монархия", "gdp_per_capita_usd": 7200, "population": 70000000, "flight_hours_from_london": 12.0},
    "TJK": {"full_name": "Таджикистан", "government_type": "президентская республика", "gdp_per_capita_usd": 1000, "population": 10000000, "flight_hours_from_london": 8.5},
    "TUN": {"full_name": "Тунис", "government_type": "парламентская республика", "gdp_per_capita_usd": 3800, "population": 12000000, "flight_hours_from_london": 3.5},
    "TUR": {"full_name": "Турция", "government_type": "президентская республика", "gdp_per_capita_usd": 11000, "population": 85000000, "flight_hours_from_london": 4.0},
    "TWN": {"full_name": "Тайвань", "government_type": "полупрезидентская республика", "gdp_per_capita_usd": 33000, "population": 24000000, "flight_hours_from_london": 12.5},
    "UKR": {"full_name": "Украина", "government_type": "полупрезидентская республика", "gdp_per_capita_usd": 4500, "population": 37000000, "flight_hours_from_london": 3.5},
    "URY": {"full_name": "Уругвай", "government_type": "президентская республика", "gdp_per_capita_usd": 18000, "population": 3400000, "flight_hours_from_london": 14.5},
    "USA": {"full_name": "США", "government_type": "федеративная президентская республика", "gdp_per_capita_usd": 76000, "population": 335000000, "flight_hours_from_london": 8.0},
    "UZB": {"full_name": "Узбекистан", "government_type": "президентская республика", "gdp_per_capita_usd": 2200, "population": 35000000, "flight_hours_from_london": 7.5},
    "VEN": {"full_name": "Венесуэла", "government_type": "федеративная президентская республика", "gdp_per_capita_usd": 3500, "population": 28000000, "flight_hours_from_london": 10.5},
    "VNM": {"full_name": "Вьетнам", "government_type": "социалистическая республика", "gdp_per_capita_usd": 4100, "population": 98000000, "flight_hours_from_london": 12.5},
    "ZWE": {"full_name": "Зимбабве", "government_type": "президентская республика", "gdp_per_capita_usd": 1800, "population": 16000000, "flight_hours_from_london": 11.0},
}


def main() -> None:
    codes_in_csv: list[str] = []
    with CSV_PATH.open("r", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            codes_in_csv.append(row["country_code"])

    missing = [code for code in codes_in_csv if code not in PROFILES]
    if missing:
        raise SystemExit(f"Нет профиля для: {', '.join(missing)}")

    payload = {
        "_description": "Справочник стран для экрана «Найти страну». Ключ — country_code из country_data.",
        "countries": {code: PROFILES[code] for code in codes_in_csv},
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Записано {len(codes_in_csv)} стран в {OUT_PATH}")


if __name__ == "__main__":
    main()
