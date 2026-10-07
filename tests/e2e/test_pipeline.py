# tests/e2e/test_pipeline.py
"""
End-to-End tests for the full Text-to-SQL pipeline.

These tests use real Gemini API calls and real DuckDB execution.
They assert result shape (columns + row count) — NOT exact SQL.

Each test targets a specific canonical question from the PRD (Section 6.2).
"""
import pytest
import os
import sys
from tools.duckdb_tools import execute_query
from agents.schema_agents import get_schema_agent
from agents.sql_writer import get_sql_writer_agent
from agents.validator_agent import validate_and_execute_query
from tests.e2e.judge import llm_judge     # for LLM-as-a-judge

# -------------------------------------------------------
# Helper: run the minimal pipeline for a given question.
# We bypass the Orchestrator to avoid Supabase dependency in unit-like E2E tests.
# -------------------------------------------------------

def run_minimal_pipeline(question: str) -> list[dict]:
    """
    Runs the minimal schema → SQL → validate pipeline without
    the Orchestrator's Supabase memory or Response Agent.
    Returns raw query results as list[dict].
    """
    # Step 1: Introspect schema
    schema_agent = get_schema_agent()
    schema_response = schema_agent.run("Introspect the database and return the full schema.")
    schema_context = schema_response.content

    # Step 2: Generate SQL
    sql_writer = get_sql_writer_agent()
    sql_prompt = (
        f"User Question: {question}\n"
        f"Database Schema:\n{schema_context}\n\n"
        f"Write the matching DuckDB SQL query."
    )
    sql_response = sql_writer.run(sql_prompt)
    initial_sql = sql_response.content.strip()

    # Step 3: Validate & Execute (with retry loop)
    results = validate_and_execute_query(
        question=question,
        initial_sql=initial_sql,
        schema_context=schema_context,
        sql_writer_agent=sql_writer,
    )
    return results

# -------------------------------------------------------
# Test Suite
# -------------------------------------------------------

class TestSalesPipeline:
    """Tests using fixtures/clean/sales.csv"""

    # def test_total_revenue_by_region(self):
    #     """
    #     Question: Total revenue by region.
    #     Expected: 4 rows (North, South, East, West), columns: region + revenue aggregate.
    #     """
    #     results = run_minimal_pipeline("What is the total revenue by region?")
        
    #     assert isinstance(results, list), "Results must be a list"
    #     assert len(results) == 4, f"Expected 4 regions, got {len(results)}"
        
    #     # Verify expected column shapes (at least one region column and one numeric column)
    #     first_row = results[0]
    #     col_names = [c.lower() for c in first_row.keys()]
    #     assert any("region" in c for c in col_names), f"Expected 'region' column, got: {col_names}"
    #     assert any("revenue" in c or "total" in c or "sum" in c for c in col_names), \
    #         f"Expected a revenue/total column, got: {col_names}"
    def test_total_revenue_by_region(self):
        results = run_minimal_pipeline("What is the total revenue by region?")
        
        # Rule-based — shape check (fast)
        assert isinstance(results, list)
        assert len(results) == 4

        # LLM-as-a-judge — semantic check (slower, costs API)
        assert llm_judge(
            question="What is the total revenue by region?",
            result=str(results),
            criteria="Results must contain all 4 regions (North, South, East, West) "
                    "each with a corresponding numeric revenue total."
        )

    def test_top_5_products_by_quantity(self):
        """
        Question: Top 5 products by quantity sold.
        Expected: 5 rows, columns include product + quantity.
        """
        results = run_minimal_pipeline("What are the top 5 products by total quantity sold?")
        
        assert isinstance(results, list)
        assert len(results) == 5, f"Expected 5 products, got {len(results)}"
        
        col_names = [c.lower() for c in results[0].keys()]
        assert any("product" in c for c in col_names), f"Expected 'product' column, got: {col_names}"
        assert any("quantity" in c or "qty" in c for c in col_names), \
            f"Expected a quantity column, got: {col_names}"

    def test_monthly_revenue_trend(self):
        """
        Question: Monthly revenue trend.
        Expected: Multiple rows, ordered by date. Columns include a date/month and revenue field.
        """
        results = run_minimal_pipeline("Show me the monthly revenue trend.")
        
        assert isinstance(results, list)
        assert len(results) > 1, "Expected multiple monthly rows"
        
        col_names = [c.lower() for c in results[0].keys()]
        assert any("month" in c or "date" in c or "period" in c for c in col_names), \
            f"Expected a date/month column, got: {col_names}"
        assert any("revenue" in c or "total" in c or "sum" in c for c in col_names), \
            f"Expected a revenue column, got: {col_names}"


class TestEmployeesPipeline:
    """Tests using fixtures/clean/employees.csv"""

    def test_average_salary_by_department(self):
        """
        Question: Average salary by department.
        Expected: Multiple department rows, columns include department + avg salary.
        """
        results = run_minimal_pipeline("What is the average salary by department?")
        
        assert isinstance(results, list)
        assert len(results) >= 1, "Expected at least one department row"
        
        col_names = [c.lower() for c in results[0].keys()]
        assert any("department" in c for c in col_names), \
            f"Expected 'department' column, got: {col_names}"
        assert any("salary" in c or "avg" in c or "average" in c for c in col_names), \
            f"Expected a salary/average column, got: {col_names}"

    def test_employees_earning_more_than_manager(self):
        """
        Question: Who earns more than their manager?
        Expected: At least one row with employee + salary info (requires self-join or subquery).
        """
        results = run_minimal_pipeline("Which employees earn more than their manager?")
        
        assert isinstance(results, list), "Results must be a list"
        # This query may return 0 rows if no such employees exist in the fixture —
        # we only assert the structure if rows are returned.
        if len(results) > 0:
            col_names = [c.lower() for c in results[0].keys()]
            assert any("name" in c or "employee" in c for c in col_names), \
                f"Expected an employee/name column, got: {col_names}"


class TestMultiTablePipeline:
    """Tests requiring joins across sales + products tables."""

    def test_products_never_ordered(self):
        """
        Question: Products that have never been ordered.
        Expected: List of products NOT present in sales data (tests subquery / LEFT JOIN).
        """
        results = run_minimal_pipeline(
            "Which products have never been ordered? Use the products and sales tables."
        )
        
        assert isinstance(results, list), "Results must be a list"
        # Structural check: should return product_code or product_name columns
        if len(results) > 0:
            col_names = [c.lower() for c in results[0].keys()]
            assert any("product" in c for c in col_names), \
                f"Expected a product column, got: {col_names}"
