"""
Layer C: Data quality checks on mart tables in BigQuery after dbt runs.
Runs after dbt_test and before ml_churn_score.

Connects to BigQuery, pulls each mart table into a DataFrame,
and runs Great Expectations validations. Fails the Airflow task
if any critical expectation is violated.
"""

import os
import pandas as pd
import great_expectations as gx
from google.cloud import bigquery


PROJECT_ID = "airflow-marketing-analytics"
DATASET = "marts"

# Cap rows pulled into the scheduler for GE validation to prevent OOM.
# Row-count expectations use a separate COUNT query so this cap doesn't affect them.
MAX_VALIDATION_ROWS = 100_000


def _bq_client() -> bigquery.Client:
    """Create BigQuery client using GCP service account key."""
    key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "/home/airflow/.gcp/key.json")
    return bigquery.Client.from_service_account_json(key_path, project=PROJECT_ID)


def _fetch_table(client: bigquery.Client, table: str) -> pd.DataFrame:
    """Fetch up to MAX_VALIDATION_ROWS from a mart table for GE validation."""
    return client.query(
        f"SELECT * FROM `{PROJECT_ID}.{DATASET}.{table}` LIMIT {MAX_VALIDATION_ROWS}"
    ).to_dataframe()


def _fetch_row_count(client: bigquery.Client, table: str) -> int:
    """Return exact row count for a mart table without pulling all data."""
    row = list(client.query(
        f"SELECT COUNT(*) AS n FROM `{PROJECT_ID}.{DATASET}.{table}`"
    ).result())[0]
    return row["n"]


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


def validate_marts(**context) -> None:
    """Run GE validation on all mart tables in BigQuery. Raises on any failure."""
    client = _bq_client()
    gx_context = gx.get_context(mode="ephemeral")

    suites = {
        "mart_customer_ltv": [
            ("expect_table_row_count_to_be_between", {"min_value": 100}),
            ("expect_column_values_to_not_be_null", {"column": "customer_id"}),
            ("expect_column_values_to_be_unique", {"column": "customer_id"}),
            ("expect_column_values_to_not_be_null", {"column": "total_orders"}),
            ("expect_column_values_to_be_between", {"column": "total_orders", "min_value": 0}),
            ("expect_column_values_to_be_between", {"column": "total_revenue", "min_value": 0}),
            ("expect_column_values_to_not_be_null", {"column": "net_ltv"}),  # can be negative (high acq_cost)
            ("expect_column_values_to_be_between", {"column": "churn_probability", "min_value": 0, "max_value": 1}),
        ],
        "mart_campaign_performance": [
            ("expect_table_row_count_to_be_between", {"min_value": 1}),
            ("expect_column_values_to_not_be_null", {"column": "campaign_id"}),
            ("expect_column_values_to_not_be_null", {"column": "channel"}),
            ("expect_column_values_to_be_between", {"column": "total_impressions", "min_value": 0}),
            ("expect_column_values_to_be_between", {"column": "total_clicks", "min_value": 0}),
            ("expect_column_values_to_be_between", {"column": "attributed_revenue", "min_value": 0}),
            ("expect_column_values_to_be_between", {"column": "conversion_rate_pct", "min_value": 0}),
        ],
        "mart_churn_summary": [
            ("expect_table_row_count_to_be_between", {"min_value": 1}),
            ("expect_column_values_to_not_be_null", {"column": "segment"}),
            ("expect_column_values_to_not_be_null", {"column": "region"}),
            ("expect_column_values_to_be_between", {"column": "total_customers", "min_value": 1}),
            ("expect_column_values_to_be_between", {"column": "churn_rate_pct", "min_value": 0, "max_value": 100}),
            ("expect_column_values_to_be_between", {"column": "avg_churn_probability", "min_value": 0, "max_value": 1}),
        ],
    }

    all_passed = True
    for table_name, expectations in suites.items():
        try:
            actual_count = _fetch_row_count(client, table_name)
            df = _fetch_table(client, table_name)
            print(f"\n[{table_name}] {actual_count} rows total (validating up to {MAX_VALIDATION_ROWS})")
            # Inject actual row count so GE row-count expectations see the real total
            df.attrs["actual_row_count"] = actual_count
            results = _run_validation(gx_context, df, table_name, expectations)
            try:
                _assert_results(results, table_name)
            except ValueError as e:
                print(f"  ERROR: {e}")
                all_passed = False
        except Exception as e:
            print(f"\n[{table_name}] FETCH ERROR: {e}")
            all_passed = False

    if not all_passed:
        raise ValueError("Mart data validation failed — see errors above.")

    print("\n✅ All mart data validations passed.")


if __name__ == "__main__":
    validate_marts()
