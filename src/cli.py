"""AWS AI Data Migrator CLI."""

import sys
import json
from pathlib import Path
from typing import Optional
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from rich.panel import Panel

from src.utils.config import Config
from src.utils.logger import setup_logging, get_logger
from src.connectors.json_csv import JsonCsvConnector
from src.connectors.mongodb import MongoDBConnector
from src.agent.analyzer import SchemaAnalyzer
from src.agent.planner import MigrationPlanner
from src.agent.resolver import ConflictResolver
from src.agent.cost_estimator import CostEstimator
from src.migrators.dynamodb import DynamoDBMigrator
from src.migrators.s3 import S3Migrator
from src.validators.integrity import IntegrityValidator
from src.security.credential_manager import CredentialManager
from src.security.pii_scanner import PIIScanner
from src.utils.manifest import MigrationManifest

console = Console()
logger = get_logger(__name__)


@click.group()
@click.version_option(version="0.1.0")
def main():
    """AWS AI Data Migrator - LLM-powered data migration to AWS S3 and DynamoDB."""
    pass


@main.command()
@click.option(
    "--source",
    type=click.Choice(["json", "csv", "mongodb"]),
    required=True,
    help="Data source type",
)
@click.option("--path", required=True, help="Path to data source")
@click.option("--sample-size", default=10, help="Number of documents to sample")
def analyze(source: str, path: str, sample_size: int):
    """Analyze source data schema and patterns."""
    try:
        config = Config()
        setup_logging(config.log_level)
        logger.info(f"Starting analysis of {source} source at {path}")

        # Load sample data
        samples = []
        if source == "mongodb":
            # Parse MongoDB connection
            db, collection = path.split(".")
            connector = MongoDBConnector(config.source_mongodb_uri)
            samples = connector.sample_documents(db, collection, sample_size)
            connector.close()
        else:
            connector = JsonCsvConnector(path)
            samples = list(connector.stream(batch_size=sample_size))[0] if list(
                connector.stream(batch_size=sample_size)
            ) else []

        if not samples:
            console.print("[red]No data found in source[/red]")
            return

        # Analyze schema
        analyzer = SchemaAnalyzer(config.anthropic_api_key)
        analysis = analyzer.analyze_documents(samples)

        # Display results
        console.print(Panel("[bold cyan]Schema Analysis Results[/bold cyan]"))
        if analysis.get("status") == "success":
            console.print_json(data=analysis)
        else:
            console.print(f"[red]Analysis failed: {analysis.get('message')}[/red]")
            sys.exit(1)

        # Save analysis
        analysis_file = Path("analysis.json")
        with open(analysis_file, "w") as f:
            json.dump(analysis, f, indent=2, default=str)
        console.print(f"\n[green]Analysis saved to {analysis_file}[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.error(f"Analysis failed: {e}", exc_info=True)
        sys.exit(1)


@main.command()
@click.option("--analysis-file", required=True, help="Path to analysis JSON file")
@click.option("--record-count", required=True, type=int, help="Total number of records")
def plan(analysis_file: str, record_count: int):
    """Generate migration plan from schema analysis."""
    try:
        config = Config()
        setup_logging(config.log_level)
        logger.info(f"Generating migration plan from {analysis_file}")

        # Load analysis
        with open(analysis_file, "r") as f:
            analysis = json.load(f)

        # Generate plan
        planner = MigrationPlanner(config.anthropic_api_key)
        plan_result = planner.generate_plan(analysis, record_count)

        # Display results
        console.print(Panel("[bold cyan]Migration Plan[/bold cyan]"))
        if plan_result.get("status") == "success":
            console.print_json(data=plan_result)
        else:
            console.print(f"[red]Plan generation failed: {plan_result.get('message')}[/red]")
            sys.exit(1)

        # Save plan
        plan_file = Path("migration-plan.json")
        with open(plan_file, "w") as f:
            json.dump(plan_result, f, indent=2, default=str)

        # Estimate costs
        estimator = CostEstimator()
        s3_estimate = estimator.estimate_s3_costs(
            total_size_bytes=record_count * 1024, storage_class="STANDARD"
        )
        dynamodb_estimate = estimator.estimate_dynamodb_costs(
            item_count=record_count, billing_mode="PAY_PER_REQUEST"
        )

        console.print(Panel("[bold cyan]Cost Estimation[/bold cyan]"))
        cost_report = estimator.generate_cost_report(s3_estimate, dynamodb_estimate)
        console.print(cost_report)

        console.print(f"\n[green]Plan saved to {plan_file}[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.error(f"Plan generation failed: {e}", exc_info=True)
        sys.exit(1)


@main.command()
@click.option("--plan-file", required=True, help="Path to migration plan JSON")
@click.option("--source", required=True, help="Source data path")
@click.option("--s3-bucket", required=True, help="Target S3 bucket")
@click.option("--dynamodb-table", required=True, help="Target DynamoDB table")
@click.option("--dry-run", is_flag=True, help="Preview without creating resources")
def migrate(plan_file: str, source: str, s3_bucket: str, dynamodb_table: str, dry_run: bool):
    """Execute migration to S3 and DynamoDB."""
    try:
        config = Config()
        setup_logging(config.log_level)
        logger.info(f"Starting migration to {s3_bucket} and {dynamodb_table}")

        # Load plan
        with open(plan_file, "r") as f:
            plan = json.load(f)

        if dry_run:
            console.print(Panel("[bold yellow]DRY RUN MODE[/bold yellow]"))
            console.print("Migration would create:")
            console.print(f"  S3 Bucket: {s3_bucket}")
            console.print(f"  DynamoDB Table: {dynamodb_table}")
            return

        # Validate credentials
        cred_mgr = CredentialManager(aws_profile=config.aws_profile, aws_region=config.aws_region)

        # Load source data
        connector = JsonCsvConnector(source)
        samples = list(connector.load())

        # Create S3 bucket and migrate files
        console.print(Panel("[bold cyan]Migrating to S3[/bold cyan]"))
        s3_migrator = S3Migrator(region=config.aws_region)
        s3_migrator.create_bucket(s3_bucket)

        # Create DynamoDB table and migrate data
        console.print(Panel("[bold cyan]Migrating to DynamoDB[/bold cyan]"))
        dynamodb_migrator = DynamoDBMigrator(region=config.aws_region)
        dynamodb_migrator.create_table(
            table_name=dynamodb_table,
            partition_key="id",
            sort_key="timestamp",
            billing_mode="PAY_PER_REQUEST",
        )
        dynamodb_migrator.wait_for_table(dynamodb_table)

        # Batch write items
        write_result = dynamodb_migrator.batch_write_items(dynamodb_table, samples)

        # Display results
        table = Table(title="Migration Results")
        table.add_column("Destination", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="white")
        table.add_row("S3", "Created", f"Bucket: {s3_bucket}")
        table.add_row("DynamoDB", "Created", f"Table: {dynamodb_table}, Items: {write_result['written_items']}")
        console.print(table)

        # Save manifest
        manifest = MigrationManifest()
        manifest.save(config.migration_name)
        console.print(f"\n[green]Migration completed successfully[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)


@main.command()
@click.option("--manifest-file", required=True, help="Path to migration manifest")
def rollback(manifest_file: str):
    """Rollback migration by deleting all created resources."""
    try:
        config = Config()
        setup_logging(config.log_level)
        logger.info(f"Starting rollback from manifest {manifest_file}")

        # Load manifest
        manifest_data = MigrationManifest.load(manifest_file)
        resources = manifest_data.get("resources", [])

        if not resources:
            console.print("[yellow]No resources found in manifest[/yellow]")
            return

        # Confirm rollback
        if not click.confirm(f"Delete {len(resources)} resources?"):
            console.print("Rollback cancelled")
            return

        # Delete resources
        s3_migrator = S3Migrator(region=config.aws_region)
        dynamodb_migrator = DynamoDBMigrator(region=config.aws_region)

        deleted = 0
        for resource in resources:
            resource_type = resource.get("type")
            resource_id = resource.get("id")

            try:
                if resource_type == "s3_object":
                    # Parse bucket and key
                    arn = resource.get("arn")
                    if "s3://" in arn:
                        bucket, key = arn.split("//")[1].split("/", 1)
                        s3_migrator.client.delete_object(Bucket=bucket, Key=key)
                elif resource_type == "dynamodb_table":
                    dynamodb_migrator.delete_table(resource_id)
                deleted += 1
                logger.info(f"Deleted {resource_type}: {resource_id}")
            except Exception as e:
                logger.error(f"Failed to delete {resource_type} {resource_id}: {e}")

        console.print(f"[green]Rollback complete: {deleted}/{len(resources)} resources deleted[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.error(f"Rollback failed: {e}", exc_info=True)
        sys.exit(1)


@main.command()
@click.option("--s3-bucket", required=True, help="S3 bucket to validate")
@click.option("--dynamodb-table", required=True, help="DynamoDB table to validate")
@click.option("--expected-records", required=True, type=int, help="Expected record count")
def validate(s3_bucket: str, dynamodb_table: str, expected_records: int):
    """Validate migration data integrity."""
    try:
        config = Config()
        setup_logging(config.log_level)
        logger.info(f"Starting validation of {s3_bucket} and {dynamodb_table}")

        validator = IntegrityValidator(region=config.aws_region)

        # Validate S3
        s3_result = validator.validate_s3_migration(s3_bucket, expected_records, expected_records * 1024)

        # Validate DynamoDB
        dynamodb_result = validator.validate_dynamodb_migration(dynamodb_table, expected_records)

        # Generate report
        validation = validator.validate_migration(s3_result, dynamodb_result)
        report = validator.generate_validation_report(validation)

        console.print(Panel("[bold cyan]Data Integrity Validation Report[/bold cyan]"))
        console.print(report)

        if validation.get("overall_status") == "PASSED":
            console.print("\n[green]Validation PASSED[/green]")
        else:
            console.print("\n[red]Validation FAILED[/red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.error(f"Validation failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
