# Copyright © 2026, UChicago Argonne, LLC
# See LICENSE for terms and disclaimer.

"""Unit tests for FilterSpec.

Inputs: constructed FilterSpec instances.
Outputs: analytically known SQL WHERE clauses and parameter lists.
No I/O, no database.
"""

from datetime import UTC, datetime

import pytest

from adapt.api.selection import FilterSpec

pytestmark = pytest.mark.unit


class TestFilterSpecIsEmpty:
    def test_default_filter_spec_is_empty(self):
        assert FilterSpec().is_empty()

    def test_filter_spec_with_one_field_is_not_empty(self):
        assert not FilterSpec(lifetime_min_s=60.0).is_empty()

    def test_filter_spec_with_required_tags_is_not_empty(self):
        assert not FilterSpec(required_tags=frozenset(["supercell"])).is_empty()


class TestFilterSpecToSqlWhereNoConstraints:
    def test_empty_spec_produces_empty_clause(self):
        clause, params = FilterSpec().to_sql_where()
        assert clause == ""
        assert params == []


class TestFilterSpecLifetimeConstraints:
    def test_lifetime_min_produces_where_clause(self):
        clause, params = FilterSpec(lifetime_min_s=3600.0).to_sql_where()
        assert clause.startswith("WHERE")
        assert 3600.0 in params

    def test_lifetime_max_produces_where_clause(self):
        clause, params = FilterSpec(lifetime_max_s=7200.0).to_sql_where()
        assert clause.startswith("WHERE")
        assert 7200.0 in params

    def test_lifetime_min_and_max_both_in_params(self):
        clause, params = FilterSpec(lifetime_min_s=1800.0, lifetime_max_s=5400.0).to_sql_where()
        assert 1800.0 in params
        assert 5400.0 in params
        assert len([p for p in params if isinstance(p, float)]) == 2


class TestFilterSpecAreaConstraints:
    def test_max_area_min_produces_clause(self):
        clause, params = FilterSpec(max_area_min_km2=100.0).to_sql_where()
        assert clause.startswith("WHERE")
        assert 100.0 in params

    def test_max_area_max_produces_clause(self):
        clause, params = FilterSpec(max_area_max_km2=500.0).to_sql_where()
        assert 500.0 in params


class TestFilterSpecReflectivityConstraints:
    def test_max_refl_min_produces_clause(self):
        clause, params = FilterSpec(max_refl_min_dbz=55.0).to_sql_where()
        assert clause.startswith("WHERE")
        assert 55.0 in params

    def test_max_refl_max_produces_clause(self):
        clause, params = FilterSpec(max_refl_max_dbz=70.0).to_sql_where()
        assert 70.0 in params


class TestFilterSpecOriginTypes:
    def test_single_origin_type_uses_in_clause(self):
        clause, params = FilterSpec(origin_types=frozenset(["INITIATION"])).to_sql_where()
        assert "IN" in clause.upper()
        assert "INITIATION" in params

    def test_multiple_origin_types_all_in_params(self):
        types = frozenset(["INITIATION", "SPLIT"])
        clause, params = FilterSpec(origin_types=types).to_sql_where()
        assert "INITIATION" in params
        assert "SPLIT" in params

    def test_origin_type_placeholders_match_param_count(self):
        types = frozenset(["INITIATION", "SPLIT", "MERGE"])
        clause, params = FilterSpec(origin_types=types).to_sql_where()
        # clause must have exactly 3 '?' for origin_type IN (?, ?, ?)
        in_start = clause.upper().find("IN (")
        in_end = clause.find(")", in_start)
        placeholders = clause[in_start:in_end].count("?")
        assert placeholders == 3


class TestFilterSpecTimeConstraints:
    def test_first_seen_after_produces_clause(self):
        dt = datetime(2024, 1, 1, tzinfo=UTC)
        clause, params = FilterSpec(first_seen_after=dt).to_sql_where()
        assert clause.startswith("WHERE")
        assert any("2024" in str(p) for p in params)

    def test_first_seen_before_produces_clause(self):
        dt = datetime(2024, 6, 1, tzinfo=UTC)
        clause, params = FilterSpec(first_seen_before=dt).to_sql_where()
        assert any("2024" in str(p) for p in params)


class TestFilterSpecCombined:
    def test_multiple_constraints_combined_with_and(self):
        spec = FilterSpec(lifetime_min_s=3600.0, max_refl_min_dbz=55.0)
        clause, params = spec.to_sql_where()
        assert " AND " in clause
        assert len(params) == 2

    def test_n_scans_min_produces_clause(self):
        clause, params = FilterSpec(n_scans_min=5).to_sql_where()
        assert clause.startswith("WHERE")
        assert 5 in params


class TestFilterSpecImmutability:
    def test_filter_spec_is_hashable(self):
        spec = FilterSpec(lifetime_min_s=60.0)
        assert hash(spec) is not None

    def test_equal_filter_specs_have_same_hash(self):
        a = FilterSpec(lifetime_min_s=60.0, max_refl_min_dbz=45.0)
        b = FilterSpec(lifetime_min_s=60.0, max_refl_min_dbz=45.0)
        assert a == b
        assert hash(a) == hash(b)
