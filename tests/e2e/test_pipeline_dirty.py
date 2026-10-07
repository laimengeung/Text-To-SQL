# tests/e2e/test_pipeline_dirty.py
"""
End-to-End robustness tests for the full Text-to-SQL pipeline using dirty/edge case fixtures.

These tests use real Gemini API calls and real DuckDB execution.
Unlike clean fixture tests (which assert correctness), these tests assert ROBUSTNESS:
- The pipeline must not crash on messy data
- Results must be returned gracefully (even if empty)
- Errors must surface as typed exceptions, never raw tracebacks

Dirty fixtures live in: fixtures/edge_cases/
- sales_dirty.csv
- employees_dirty.csv
- products_dirty.csv

These are V2 tests — run after clean fixture tests pass fully.
See PRD Section 6 and CONTEXT.md for full edge case index.
"""

import pytest
import os
from database.registry import register_csv as _register_csv
from tools.duckdb_tools import execute_query
from agents.schema_agents import get_schema_agent
from agents.sql_writer import get_sql_writer_agent
from agents.validator_agent import validate_and_execute_query
from core.exceptions import SQLGenerationError
from tests.e2e.judge import llm_judge

# -------------------------------------------------------
# Fixtures — load dirty CSVs into DuckDB before each test class
# -------------------------------------------------------

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EDGE_CASES_DIR = os.path.join(PROJECT_ROOT, "fixtures", "dirty")

@pytest.fixture(scope="class")
def load_dirty_sales():
    _register_csv(os.path.join(EDGE_CASES_DIR, "sales_dirty.csv"), "sales_dirty")

@pytest.fixture(scope="class")
def load_dirty_employees():
    _register_csv(os.path.join(EDGE_CASES_DIR, "employees_dirty.csv"), "employees_dirty")

@pytest.fixture(scope="class")
def load_dirty_products():
    _register_csv(os.path.join(EDGE_CASES_DIR, "products_dirty.csv"), "products_dirty")

@pytest.fixture(scope="class")
def load_all_dirty():
    _register_csv(os.path.join(EDGE_CASES_DIR, "sales_dirty.csv"), "sales_dirty")
    _register_csv(os.path.join(EDGE_CASES_DIR, "employees_dirty.csv"), "employees_dirty")
    _register_csv(os.path.join(EDGE_CASES_DIR, "products_dirty.csv"), "products_dirty")


# -------------------------------------------------------
# Helper: same minimal pipeline as clean tests
# -------------------------------------------------------

def run_minimal_pipeline(question: str) -> list[dict]:
    """
    Runs the minimal schema → SQL → validate pipeline.
    Bypasses Orchestrator to avoid Supabase dependency.
    Returns raw query results as list[dict].
    """
    schema_agent = get_schema_agent()
    schema_response = schema_agent.run("Introspect the database and return the full schema.")
    schema_context = schema_response.content

    sql_writer = get_sql_writer_agent()
    sql_prompt = (
        f"User Question: {question}\n"
        f"Database Schema:\n{schema_context}\n\n"
        f"Write the matching DuckDB SQL query."
    )
    sql_response = sql_writer.run(sql_prompt)
    initial_sql = sql_response.content.strip()

    results = validate_and_execute_query(
        question=question,
        initial_sql=initial_sql,
        schema_context=schema_context,
        sql_writer_agent=sql_writer,
    )
    return results


# -------------------------------------------------------
# Data Quality Edge Cases — sales_dirty.csv
# -------------------------------------------------------

@pytest.mark.usefixtures("load_dirty_sales")
class TestDataQualitySales:
    """
    Tests targeting data quality issues in sales_dirty.csv:
    - Duplicate order_ids
    - Inconsistent region casing (North / north / NORTH)
    - Negative revenue rows (refunds)
    - Zero quantity rows (cancelled orders)
    - Whitespace in customer_id values
    - Mixed date formats
    """

    def test_duplicate_rows_handled_with_distinct(self):
        """
        Edge case: 5 duplicate order_ids exist in sales_dirty.
        Agent must use DISTINCT or GROUP BY — result count should reflect
        unique orders, not raw row count.
        Asserts: pipeline does not crash, returns a list.
        """
        results = run_minimal_pipeline(
            "How many unique orders are in the sales_dirty table?"
        )
        assert isinstance(results, list), "Pipeline must return a list"
        assert len(results) > 0, "Expected at least one result row"

        # The count should be less than total rows due to duplicates
        first_row = results[0]
        col_names = [c.lower() for c in first_row.keys()]
        assert any("count" in c or "unique" in c or "distinct" in c or "order" in c for c in col_names), \
            f"Expected a count column, got: {col_names}"

    def test_inconsistent_region_casing(self):
        """
        Edge case: region column has 'North', 'north', 'NORTH' for the same region.
        Agent should ideally normalize casing (LOWER() or UPPER()) for grouping.
        Asserts: pipeline does not crash, returns grouped results.
        """
        results = run_minimal_pipeline(
            "Show me total revenue by region from the sales_dirty table."
        )
        assert isinstance(results, list), "Pipeline must return a list"
        assert len(results) > 0, "Expected at least one region row"

        col_names = [c.lower() for c in results[0].keys()]
        assert any("region" in c for c in col_names), \
            f"Expected 'region' column, got: {col_names}"

    def test_negative_revenue_refunds(self):
        """
        Edge case: 10 rows with negative revenue (refunds).
        Agent must not crash on negative values in SUM/AVG.
        Asserts: pipeline returns a numeric result (could be positive or negative total).
        """
        results = run_minimal_pipeline(
            "What is the total revenue in the sales_dirty table, including refunds?"
        )
        assert isinstance(results, list), "Pipeline must return a list"
        assert len(results) == 1, "Expected a single total revenue row"

        first_row = results[0]
        col_names = [c.lower() for c in first_row.keys()]
        assert any("revenue" in c or "total" in c or "sum" in c for c in col_names), \
            f"Expected a revenue/total column, got: {col_names}"
        
        # LLM judge — verify refunds (negative rows) were included, not filtered out
        assert llm_judge(
            question="What is the total revenue in the sales_dirty table, including refunds?",
            result=str(results),
            criteria="The result must be a single row with a total revenue value. "
                    "The table contains 10 rows with negative revenue (refunds) that must be INCLUDED in the sum. "
                    "If the result is suspiciously large or positive-only, refunds may have been filtered — "
                    "verify that negative values were included in the SUM. "
                    "A result that excluded negatives is a FAIL."
        ), f"LLM judge failed — refunds may not have been included. Got: {results}"

    def test_zero_quantity_division_safety(self):
        """
        Edge case: 5 rows with quantity = 0 (cancelled orders).
        Division by quantity would cause division-by-zero error.
        Agent should handle this — either filter out zeros or use NULLIF.
        Asserts: pipeline does not raise SQLGenerationError after retries.
        """
        # This should not raise — agent must handle or filter zero quantities
        results = run_minimal_pipeline(
            "What is the average revenue per unit (revenue / quantity) "
            "for non-cancelled orders in sales_dirty?"
        )
        assert isinstance(results, list), "Pipeline must return a list without crashing"

    def test_whitespace_in_customer_id(self):
        """
        Edge case: customer_id has leading/trailing whitespace ('CUST-001 ', ' CUST-002').
        Agent should use TRIM() for accurate grouping.
        Asserts: pipeline returns grouped results without crashing.
        """
        results = run_minimal_pipeline(
            "How many orders has each customer placed in the sales_dirty table?"
        )
        assert isinstance(results, list), "Pipeline must return a list"
        assert len(results) > 0, "Expected at least one customer row"

        col_names = [c.lower() for c in results[0].keys()]
        assert any("customer" in c for c in col_names), \
            f"Expected a customer column, got: {col_names}"

    def test_mixed_date_formats(self):
        """
        Edge case: date column has mixed formats (YYYY-MM-DD, MM/DD/YYYY, DD-Mon-YYYY).
        Agent must handle or cast dates correctly to filter by date range.
        Asserts: pipeline does not crash on date operations.
        """
        results = run_minimal_pipeline(
            "How many orders were placed in 2024 in the sales_dirty table?"
        )
        assert isinstance(results, list), "Pipeline must return a list"
        assert len(results) > 0, "Expected at least one result"


# -------------------------------------------------------
# Data Quality Edge Cases — employees_dirty.csv
# -------------------------------------------------------

@pytest.mark.usefixtures("load_dirty_employees")
class TestDataQualityEmployees:
    """
    Tests targeting data quality issues in employees_dirty.csv:
    - NULL salary rows (interns)
    - NULL manager_id for top-level employees (self-join edge case)
    - Whitespace in department names
    - Zero salary rows
    - Column named 'hire date' with a space
    """

    def test_null_salary_avg_handling(self):
        """
        Edge case: 3 NULL salary rows exist (interns).
        DuckDB AVG() ignores NULLs natively, but agent must not crash.
        Asserts: returns average salary per department without crashing.
        """
        results = run_minimal_pipeline(
            "What is the average salary by department in employees_dirty? "
            "Exclude NULL salaries."
        )
        assert isinstance(results, list), "Pipeline must return a list"
        assert len(results) > 0, "Expected at least one department row"

        col_names = [c.lower() for c in results[0].keys()]
        assert any("department" in c for c in col_names), \
            f"Expected 'department' column, got: {col_names}"
        assert any("salary" in c or "avg" in c for c in col_names), \
            f"Expected a salary/avg column, got: {col_names}"

    def test_self_join_with_null_manager(self):
        """
        Edge case: manager_id is NULL for 5 top-level employees.
        Self-join must use LEFT JOIN (not INNER JOIN) to avoid dropping top-level employees.
        Asserts: pipeline returns results without crashing.
        """
        results = run_minimal_pipeline(
            "Which employees in employees_dirty earn more than their manager? "
            "Exclude employees with no manager."
        )
        assert isinstance(results, list), "Pipeline must return a list"
        # May return 0 rows if no such employees — that's valid
        if len(results) > 0:
            col_names = [c.lower() for c in results[0].keys()]
            assert any("name" in c or "employee" in c for c in col_names), \
                f"Expected an employee/name column, got: {col_names}"

    def test_department_whitespace_grouping(self):
        """
        Edge case: department has inconsistent whitespace ('Engineering ', ' Sales').
        Agent should TRIM() for accurate grouping.
        Asserts: returns department groups without crashing.
        """
        results = run_minimal_pipeline(
            "How many employees are in each department in employees_dirty?"
        )
        assert isinstance(results, list), "Pipeline must return a list"
        assert len(results) > 0, "Expected at least one department row"

        col_names = [c.lower() for c in results[0].keys()]
        assert any("department" in c for c in col_names), \
            f"Expected 'department' column, got: {col_names}"

    def test_zero_salary_edge_case(self):
        """
        Edge case: 2 rows with salary = 0.
        Should not cause division-by-zero or incorrect AVG results.
        Asserts: pipeline handles zero salaries gracefully.
        """
        results = run_minimal_pipeline(
            "What is the minimum salary in the employees_dirty table?"
        )
        assert isinstance(results, list), "Pipeline must return a list"
        assert len(results) == 1, "Expected a single minimum salary row"

    def test_column_name_with_space(self):
        """
        Edge case: column named 'hire date' (with a space) exists in employees_dirty.
        Agent must use quoted identifiers: "hire date" in DuckDB SQL.
        Asserts: pipeline can query the spaced column without crashing.
        """
        results = run_minimal_pipeline(
            "How many employees in employees_dirty were hired after 2020? "
            "Use the hire date column."
        )
        assert isinstance(results, list), "Pipeline must return a list"
        assert len(results) > 0, "Expected at least one result"


# -------------------------------------------------------
# Data Quality Edge Cases — products_dirty.csv
# -------------------------------------------------------

@pytest.mark.usefixtures("load_dirty_products")
class TestDataQualityProducts:
    """
    Tests targeting data quality issues in products_dirty.csv:
    - product_code looks numeric but is a zero-padded string ('0001', '0042')
    - NULL unit_price for discontinued products
    - Zero stock_quantity rows (division edge case)
    - Trailing whitespace in product_name
    - Category typo ('Electornics')
    - Column named 'list price' (with a space)
    """

    def test_zero_padded_string_product_code(self):
        """
        Edge case: product_code is '0001', '0042' — looks numeric but is a string.
        Casting to integer strips leading zeros and breaks joins.
        Agent must treat product_code as a string (VARCHAR).
        Asserts: pipeline returns product data without casting errors.
        """
        results = run_minimal_pipeline(
            "List all products with their product_code from products_dirty."
        )
        assert isinstance(results, list), "Pipeline must return a list"
        assert len(results) > 0, "Expected product rows"

        col_names = [c.lower() for c in results[0].keys()]
        assert any("product_code" in c or "code" in c for c in col_names), \
            f"Expected a product_code column, got: {col_names}"

    def test_null_unit_price_handling(self):
        """
        Edge case: 3 rows with NULL unit_price (discontinued products).
        AVG/SUM must not crash on NULL prices.
        Asserts: pipeline returns average price, ignoring NULLs.
        """
        results = run_minimal_pipeline(
            "What is the average unit price per category in products_dirty? "
            "Ignore products with no price."
        )
        assert isinstance(results, list), "Pipeline must return a list"
        assert len(results) > 0, "Expected at least one category row"

        col_names = [c.lower() for c in results[0].keys()]
        assert any("category" in c for c in col_names), \
            f"Expected a category column, got: {col_names}"

    def test_zero_stock_division_safety(self):
        """
        Edge case: 5 products with stock_quantity = 0.
        Any per-unit calculation must handle zero stock to avoid division-by-zero.
        Asserts: pipeline does not raise SQLGenerationError after retries.
        """
        results = run_minimal_pipeline(
            "What is the total stock value (unit_price * stock_quantity) "
            "for each product in products_dirty?"
        )
        assert isinstance(results, list), "Pipeline must return a list without crashing"
        assert len(results) > 0, "Expected at least one product row"

    def test_category_typo_variant(self):
        """
        Edge case: 'Electornics' (misspelled) appears in 2 rows alongside 'Electronics'.
        Agent should return both variants separately (not silently merge them).
        Asserts: at least one category row returned, pipeline does not crash.
        """
        results = run_minimal_pipeline(
            "How many products are in each category in products_dirty?"
        )
        assert isinstance(results, list), "Pipeline must return a list"
        assert len(results) > 0, "Expected at least one category row"

        col_names = [c.lower() for c in results[0].keys()]
        assert any("category" in c for c in col_names), \
            f"Expected a category column, got: {col_names}"

    def test_product_name_trailing_whitespace(self):
        """
        Edge case: 4 product_name values have trailing whitespace ('Widget A ').
        TRIM() should be used for accurate matching.
        Asserts: pipeline can filter by product name without crashing.
        """
        results = run_minimal_pipeline(
            "Find all products in products_dirty where the product name contains 'Widget'."
        )
        assert isinstance(results, list), "Pipeline must return a list"
        # May return 0 rows if no matches — that's valid, just must not crash


# -------------------------------------------------------
# Result Edge Cases — across all dirty tables
# -------------------------------------------------------

@pytest.mark.usefixtures("load_all_dirty")
class TestResultEdgeCases:
    """
    Tests for edge cases in the result set itself:
    - Empty result set (graceful handling)
    - Single-row result
    - Very large filter returning many rows
    """

    def test_empty_result_set_graceful(self):
        """
        Edge case: query that intentionally returns zero rows.
        Agent must not crash — must return an empty list, not raise an exception.
        Asserts: returns empty list or list with zero rows.
        """
        results = run_minimal_pipeline(
            "Show all orders from sales_dirty placed before January 1st, 1900."
        )
        assert isinstance(results, list), "Empty result must still return a list, not raise"
        assert len(results) == 0, "Expected zero rows for an impossible date filter"

    def test_single_row_result(self):
        """
        Edge case: query returning exactly one row (a single aggregate).
        Asserts: pipeline handles single-row results correctly.
        """
        results = run_minimal_pipeline(
            "What is the total number of rows in the sales_dirty table?"
        )
        assert isinstance(results, list), "Pipeline must return a list"
        assert len(results) == 1, "Expected exactly one row for a COUNT(*) query"

    def test_multi_table_join_dirty(self):
        """
        Edge case: join across sales_dirty and products_dirty.
        Both tables have data quality issues — agent must handle them in a JOIN context.
        Asserts: pipeline returns joined results without crashing.
        """
        results = run_minimal_pipeline(
            "Which products from products_dirty appear in sales_dirty? "
            "Join on product name."
        )
        assert isinstance(results, list), "Pipeline must return a list"
        # May return 0 rows due to whitespace mismatches — that's valid, just must not crash

    def test_having_clause_with_dirty_data(self):
        """
        Edge case: HAVING filter on grouped dirty data.
        Tests that agent uses HAVING (not WHERE) for aggregate filtering
        even when underlying data has NULLs and duplicates.
        Asserts: pipeline returns filtered groups without crashing.
        """
        results = run_minimal_pipeline(
            "Which regions in sales_dirty have total revenue above 10000? "
            "Account for the fact that some revenue values are negative."
        )
        assert isinstance(results, list), "Pipeline must return a list"
        if len(results) > 0:
            col_names = [c.lower() for c in results[0].keys()]
            assert any("region" in c for c in col_names), \
                f"Expected a region column, got: {col_names}"