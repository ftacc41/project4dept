"""
Layer A: Data quality checks on raw CSVs before loading to BigQuery.
Runs after data generation and before load_to_bigquery.

Fails the Airflow task if any critical expectation is violated.
"""

import pandas as pd
import great_expectations as gx
from pathlib import Path


DATA_DIR = Path("/tmp/airflow_data")


def _build_suite(validator, expectations: list[tuple]) -> None:
    """Apply a list of (method, kwargs) expectations to a validator."""
    for method, kwargs in expectations:
        getattr(validator, method)(**kwargs)


def _run_validation(context, df: pd.DataFrame, suite_name: str, expectations: list[tuple]) -> gx.core.ExpectationSuiteValidationResult:
    """Create a validator from a dataframe, apply expectations, and return results."""
    ds = context.sources.add_or_update_pandas(f"pandas_{suite_name}")
    asset = ds.add_dataframe_asset(suite_name)
    batch_request = asset.build_batch_request(dataframe=df)
    context.add_or_update_expectation_suite(suite_name)
    validator = context.get_validator(
        batch_request=batch_request,
        expectation_suite_name=suite_name,
    )
    _build_suite(validator, expectations)
    return validator.validate()


def _assert_results(results: gx.core.ExpectationSuiteValidationResult, name: str) -> None:
    """Print results and raise if any expectation failed."""
    failed = [r for r in results.results if not r.success]
    for r in results.results:
        status = "✓" if r.success else "✗"
        print(f"  {status} {r.expectation_config.expectation_type}({list(r.expectation_config.kwargs.values())[0]})")
    if failed:
        msgs = [f"{r.expectation_config.expectation_type}: {r.result}" for r in failed]
        raise ValueError(f"[{name}] {len(failed)} expectation(s) failed:\n" + "\n".join(msgs))


def validate(**context) -> None:
    """Run GE validation on all 4 raw CSV files. Raises on any failure."""
    gx_context = gx.get_context(mode="ephemeral")

    files = {
        "customers": DATA_DIR / "customers.csv",
        "events":    DATA_DIR / "events.csv",
        "orders":    DATA_DIR / "orders.csv",
        "churn_labels": DATA_DIR / "churn_labels.csv",
    }

    suites = {
        "customers": [
            ("expect_table_row_count_to_be_between", {"min_value": 100}),
            ("expect_column_values_to_not_be_null", {"column": "customer_id"}),
            ("expect_column_values_to_not_be_null", {"column": "email"}),
            ("expect_column_values_to_be_unique", {"column": "customer_id"}),
            ("expect_column_values_to_be_in_set", {"column": "segment", "value_set": ["enterprise", "smb", "consumer", "startup"]}),
            ("expect_column_values_to_be_between", {"column": "age", "min_value": 0, "max_value": 120}),
            ("expect_column_values_to_be_between", {"column": "acquisition_cost", "min_value": 0}),
        ],
        "events": [
            ("expect_table_row_count_to_be_between", {"min_value": 1000}),
            ("expect_column_values_to_not_be_null", {"column": "event_id"}),
            ("expect_column_values_to_not_be_null", {"column": "customer_id"}),
            ("expect_column_values_to_be_unique", {"column": "event_id"}),
            ("expect_column_values_to_not_be_null", {"column": "event_type"}),
            ("expect_column_values_to_be_between", {"column": "session_duration_seconds", "min_value": 0}),
        ],
        "orders": [
            ("expect_table_row_count_to_be_between", {"min_value": 100}),
            ("expect_column_values_to_not_be_null", {"column": "order_id"}),
            ("expect_column_values_to_not_be_null", {"column": "customer_id"}),
            ("expect_column_values_to_be_unique", {"column": "order_id"}),
            ("expect_column_values_to_be_between", {"column": "order_amount", "min_value": 0}),
            ("expect_column_values_to_be_in_set", {"column": "status", "value_set": ["completed", "pending", "cancelled", "refunded"]}),
        ],
        "churn_labels": [
            ("expect_table_row_count_to_be_between", {"min_value": 100}),
            ("expect_column_values_to_not_be_null", {"column": "customer_id"}),
            ("expect_column_values_to_be_unique", {"column": "customer_id"}),
            ("expect_column_values_to_be_between", {"column": "churn_probability", "min_value": 0, "max_value": 1}),
            ("expect_column_values_to_not_be_null", {"column": "days_since_last_order"}),
        ],
    }

    all_passed = True
    for name, path in files.items():
        df = pd.read_csv(path)
        print(f"\n[{name}] {len(df)} rows")
        results = _run_validation(gx_context, df, name, suites[name])
        try:
            _assert_results(results, name)
        except ValueError as e:
            print(f"  ERROR: {e}")
            all_passed = False

    if not all_passed:
        raise ValueError("Raw data validation failed — see errors above.")

    print("\n✅ All raw data validations passed.")


if __name__ == "__main__":
    validate()
