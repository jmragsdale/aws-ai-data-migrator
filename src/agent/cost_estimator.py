"""Cost estimation for AWS resources."""

from typing import Dict, Any
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CostEstimator:
    """Estimates costs for S3 and DynamoDB migrations."""

    # AWS pricing (simplified, for estimation only)
    S3_PRICING = {
        "STANDARD": 0.023,  # per GB per month
        "INTELLIGENT_TIERING": 0.0125,
        "STANDARD_IA": 0.0125,
        "GLACIER": 0.004,
    }

    DYNAMODB_PRICING = {
        "on_demand": {
            "write": 1.25e-6,  # per write unit
            "read": 0.25e-6,  # per read unit
        },
        "provisioned": {
            "write": 0.00000125,  # per write unit per second
            "read": 0.00000025,  # per read unit per second
        },
    }

    def __init__(self):
        """Initialize cost estimator."""
        self.estimates = {}

    def estimate_s3_costs(
        self, total_size_bytes: int, storage_class: str = "STANDARD", months: int = 12
    ) -> Dict[str, Any]:
        """
        Estimate S3 storage costs.

        Args:
            total_size_bytes: Total data size in bytes
            storage_class: S3 storage class
            months: Number of months to estimate

        Returns:
            Cost breakdown
        """
        size_gb = total_size_bytes / (1024 ** 3)
        monthly_price = self.S3_PRICING.get(storage_class, self.S3_PRICING["STANDARD"])

        storage_cost = size_gb * monthly_price * months
        # Add data transfer costs (estimate)
        transfer_cost = size_gb * 0.01  # Simplified

        return {
            "storage_class": storage_class,
            "total_size_gb": round(size_gb, 2),
            "monthly_storage_cost": round(size_gb * monthly_price, 2),
            "estimated_months": months,
            "total_storage_cost": round(storage_cost, 2),
            "estimated_transfer_cost": round(transfer_cost, 2),
            "total_estimated_cost": round(storage_cost + transfer_cost, 2),
        }

    def estimate_dynamodb_costs(
        self,
        item_count: int,
        avg_item_size_bytes: int = 1024,
        monthly_read_percentage: float = 0.7,
        monthly_write_percentage: float = 0.3,
        months: int = 12,
        billing_mode: str = "ON_DEMAND",
    ) -> Dict[str, Any]:
        """
        Estimate DynamoDB costs.

        Args:
            item_count: Number of items in table
            avg_item_size_bytes: Average item size
            monthly_read_percentage: Percentage of operations that are reads
            monthly_write_percentage: Percentage of operations that are writes
            months: Number of months to estimate
            billing_mode: ON_DEMAND or PROVISIONED

        Returns:
            Cost breakdown
        """
        storage_gb = (item_count * avg_item_size_bytes) / (1024 ** 3)
        # DynamoDB charges 0.25 per GB per month for storage
        monthly_storage_cost = storage_gb * 0.25

        if billing_mode == "ON_DEMAND":
            # Estimate operations: assume 100 operations per item for total throughput
            monthly_operations = item_count * 100
            read_operations = monthly_operations * monthly_read_percentage
            write_operations = monthly_operations * monthly_write_percentage

            read_cost = read_operations * self.DYNAMODB_PRICING["on_demand"]["read"]
            write_cost = write_operations * self.DYNAMODB_PRICING["on_demand"]["write"]
            monthly_operational_cost = read_cost + write_cost
        else:
            # Provisioned mode estimation
            estimated_read_units = int((item_count * monthly_read_percentage) / 3600)
            estimated_write_units = int((item_count * monthly_write_percentage) / 3600)

            monthly_operational_cost = (estimated_read_units * 0.00000125 * 86400 * 30 +
                                       estimated_write_units * 0.00000125 * 86400 * 30)

        monthly_total = monthly_storage_cost + monthly_operational_cost
        total_cost = monthly_total * months

        return {
            "billing_mode": billing_mode,
            "item_count": item_count,
            "avg_item_size_bytes": avg_item_size_bytes,
            "total_storage_gb": round(storage_gb, 2),
            "monthly_storage_cost": round(monthly_storage_cost, 2),
            "monthly_operational_cost": round(monthly_operational_cost, 2),
            "monthly_total_cost": round(monthly_total, 2),
            "estimated_months": months,
            "total_estimated_cost": round(total_cost, 2),
        }

    def generate_cost_report(
        self, s3_estimate: Dict[str, Any], dynamodb_estimate: Dict[str, Any], months: int = 12
    ) -> str:
        """
        Generate cost estimation report.

        Args:
            s3_estimate: S3 cost estimate
            dynamodb_estimate: DynamoDB cost estimate
            months: Number of months

        Returns:
            Formatted report
        """
        total_cost = (s3_estimate.get("total_estimated_cost", 0) +
                     dynamodb_estimate.get("total_estimated_cost", 0))

        report = [
            "COST ESTIMATION REPORT",
            "=" * 60,
            f"Estimation Period: {months} months",
            "",
            "S3 COSTS:",
            f"  Storage Class: {s3_estimate.get('storage_class')}",
            f"  Total Size: {s3_estimate.get('total_size_gb')} GB",
            f"  Monthly Storage: ${s3_estimate.get('monthly_storage_cost'):.2f}",
            f"  Est. Transfer: ${s3_estimate.get('estimated_transfer_cost'):.2f}",
            f"  Total S3: ${s3_estimate.get('total_estimated_cost'):.2f}",
            "",
            "DYNAMODB COSTS:",
            f"  Billing Mode: {dynamodb_estimate.get('billing_mode')}",
            f"  Items: {dynamodb_estimate.get('item_count'):,}",
            f"  Storage: {dynamodb_estimate.get('total_storage_gb')} GB",
            f"  Monthly Storage: ${dynamodb_estimate.get('monthly_storage_cost'):.2f}",
            f"  Monthly Operations: ${dynamodb_estimate.get('monthly_operational_cost'):.2f}",
            f"  Total DynamoDB: ${dynamodb_estimate.get('total_estimated_cost'):.2f}",
            "",
            "TOTAL ESTIMATED COST:",
            f"  ${total_cost:.2f} for {months} months",
            f"  ${total_cost/months:.2f} per month average",
            "=" * 60,
        ]

        return "\n".join(report)
