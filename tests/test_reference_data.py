from __future__ import annotations

from core.reference_data import COUNTRY_DATA_COLUMNS, GEN_SAMPLE_COLUMNS, _quote_identifier, _table_columns


def test_quote_identifier_for_hyphen_column() -> None:
    assert _quote_identifier("alpha-2") == '"alpha-2"'


def test_gen_sample_columns_match_csv_header() -> None:
  assert GEN_SAMPLE_COLUMNS[0] == "D_INTERVIEW"
  assert len(GEN_SAMPLE_COLUMNS) == 19


def test_country_data_columns_include_hyphen_names() -> None:
    assert "alpha-2" in COUNTRY_DATA_COLUMNS
    sql = _table_columns(COUNTRY_DATA_COLUMNS)
    assert '"alpha-2"' in sql
    assert '"sub-region"' in sql
