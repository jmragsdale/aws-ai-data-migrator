# AWS AI Data Migrator

An intelligent, LLM-powered CLI tool for migrating unstructured data to AWS S3 and DynamoDB. Uses Claude AI to automatically analyze data schemas, resolve inconsistencies, and generate optimized migration plans.

## Features

- **Intelligent Schema Analysis**: Uses Claude to analyze document samples and infer implicit schemas
- **Conflict Resolution**: Automatically suggests strategies for handling data inconsistencies
- **Migration Planning**: Generates optimized DynamoDB and S3 designs with cost estimates
- **Multiple Data Sources**: Supports MongoDB, JSON, CSV, and filesystem data
- **PII Detection**: Scans for sensitive data with regex and AI analysis
- **Encrypted Migration**: Enforces encryption for both S3 and DynamoDB
- **Data Validation**: Post-migration integrity checks
- **Cost Estimation**: Monthly AWS cost projections
- **Rollback Support**: Complete rollback capability via manifest tracking

## Installation

### Prerequisites
- Python 3.9+
- AWS credentials configured (environment variables, credentials file, or IAM role)
- Anthropic API key

### Setup

1. Clone the repository:
```bash
cd /path/to/aws-ai-data-migrator
```

2. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your credentials
```

5. Install the CLI:
```bash
pip install -e .
```

## Configuration

Create a `.env` file with the following variables:

```env
# Anthropic API Key (required)
ANTHROPIC_API_KEY=sk-ant-...

# AWS Configuration
AWS_PROFILE=default
AWS_REGION=us-east-1

# Data Sources (optional)
SOURCE_MONGODB_URI=mongodb://localhost:27017/mydb
SOURCE_FILESYSTEM_PATH=/path/to/data

# Logging
LOG_LEVEL=INFO

# Migration Settings
MIGRATION_NAME=my-migration
DRY_RUN=false
```

## Usage

### 1. Analyze Data Schema

```bash
aws-migrate analyze --source json --path samples/mongo_export.json --sample-size 10
```

This command:
- Loads sample documents from the source
- Calls Claude API to analyze schema
- Detects field types and patterns
- Identifies inconsistencies
- Outputs analysis to `analysis.json`

**Options:**
- `--source` (required): `json`, `csv`, or `mongodb`
- `--path` (required): Path to data source
- `--sample-size`: Number of documents to sample (default: 10)

### 2. Generate Migration Plan

```bash
aws-migrate plan --analysis-file analysis.json --record-count 1000
```

This command:
- Reads the schema analysis
- Calls Claude to design DynamoDB tables and S3 structure
- Generates cost estimates
- Outputs plan to `migration-plan.json`

**Options:**
- `--analysis-file` (required): Path to analysis.json
- `--record-count` (required): Total records to migrate

### 3. Execute Migration

```bash
aws-migrate migrate \
  --plan-file migration-plan.json \
  --source samples/mongo_export.json \
  --s3-bucket my-migration-bucket \
  --dynamodb-table migration-data
```

This command:
- Creates S3 bucket with encryption and versioning
- Creates DynamoDB table with optimized design
- Uploads data to S3
- Writes items to DynamoDB
- Tracks all resources in manifest
- Enables PITR on DynamoDB

**Options:**
- `--plan-file` (required): Path to migration plan
- `--source` (required): Source data path
- `--s3-bucket` (required): Target S3 bucket name
- `--dynamodb-table` (required): Target DynamoDB table name
- `--dry-run`: Preview without creating resources

### 4. Validate Data Integrity

```bash
aws-migrate validate \
  --s3-bucket my-migration-bucket \
  --dynamodb-table migration-data \
  --expected-records 1000
```

This command:
- Verifies record counts match
- Spot-checks random samples
- Validates object existence
- Generates comprehensive report

**Options:**
- `--s3-bucket` (required): S3 bucket to validate
- `--dynamodb-table` (required): DynamoDB table to validate
- `--expected-records` (required): Expected record count

### 5. Rollback Migration

```bash
aws-migrate rollback --manifest-file default-migration-manifest.json
```

This command:
- Reads the migration manifest
- Deletes all created resources
- Updates manifest with deletion timestamps

**Options:**
- `--manifest-file` (required): Path to migration manifest JSON

## Project Structure

```
aws-ai-data-migrator/
├── src/
│   ├── agent/              # LLM-powered modules
│   │   ├── analyzer.py     # Schema analysis with Claude
│   │   ├── planner.py      # Migration planning with Claude
│   │   ├── resolver.py     # Conflict resolution with Claude
│   │   └── cost_estimator.py
│   ├── connectors/         # Data source adapters
│   │   ├── mongodb.py
│   │   ├── filesystem.py
│   │   └── json_csv.py
│   ├── migrators/          # AWS resource management
│   │   ├── dynamodb.py
│   │   └── s3.py
│   ├── validators/         # Post-migration verification
│   │   └── integrity.py
│   ├── security/           # Security and compliance
│   │   ├── credential_manager.py
│   │   ├── pii_scanner.py
│   │   └── encryption.py
│   ├── utils/              # Shared utilities
│   │   ├── config.py
│   │   ├── logger.py
│   │   ├── manifest.py
│   │   └── tagger.py
│   └── cli.py              # Main CLI interface
├── infra/                  # Terraform infrastructure
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── modules/
│   │   ├── dynamodb/
│   │   └── s3/
├── tests/                  # Comprehensive test suite
│   ├── conftest.py
│   ├── test_analyzer.py
│   ├── test_connectors.py
│   ├── test_planner.py
│   ├── test_migrators.py
│   └── test_pii_scanner.py
├── samples/                # Sample data for testing
│   ├── mongo_export.json
│   └── sample_documents/
├── docs/
│   └── architecture.md     # Detailed architecture documentation
├── setup.py
├── requirements.txt
├── .env.example
├── .gitignore
├── CHANGELOG.md
└── DEVLOG.md
```

## Testing

Run the test suite:

```bash
pytest tests/ -v --cov=src
```

Run specific test:

```bash
pytest tests/test_connectors.py -v
```

## Architecture

The system follows a modular architecture with clear separation of concerns:

- **Agent Modules**: Leverage Claude AI for intelligent analysis and planning
- **Connectors**: Abstract different data sources (MongoDB, JSON, CSV, filesystem)
- **Migrators**: Handle AWS resource creation and data migration
- **Security**: PII detection, encryption validation, credential management
- **Validators**: Post-migration data integrity verification

See `docs/architecture.md` for detailed architecture documentation.

## Security Considerations

- All credentials loaded from environment variables
- Sensitive values masked in logs
- PII detection before migration
- Encryption enforced for S3 and DynamoDB
- Public access blocked by default
- IAM roles supported for secure AWS access

## Cost Estimation

The tool provides cost estimates before migration:

```
DYNAMODB COSTS:
  Billing Mode: PAY_PER_REQUEST
  Items: 1,000
  Monthly Operations: $1.50
  Monthly Storage: $0.25
  Total DynamoDB: $1.75

S3 COSTS:
  Storage Class: STANDARD
  Total Size: 0.5 GB
  Monthly Storage: $0.01
  Total S3: $0.01

TOTAL ESTIMATED COST:
  $1.76 for 1 month
  $21.12 per year
```

## Troubleshooting

### API Key Not Found
Ensure `ANTHROPIC_API_KEY` is set in your `.env` file or environment.

### AWS Credentials Error
Configure AWS credentials using one of:
- Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- Credentials file: `~/.aws/credentials`
- IAM role (if running on EC2)

### Data Not Found
Verify the path to your data source is correct and readable.

### Schema Analysis Fails
Check that:
- Sample documents are valid JSON/CSV
- Anthropic API key is valid
- Network connectivity to Anthropic API is available

## Contributing

This is a sample implementation. Contributions welcome for:
- Additional data source connectors
- Performance optimizations
- New AWS services support
- Enhanced validation rules

## License

MIT License - See LICENSE file for details

## Support

For issues and questions:
1. Check the documentation in `docs/architecture.md`
2. Review test examples in `tests/`
3. Check logs for detailed error messages
4. Enable debug logging: `LOG_LEVEL=DEBUG`

## Roadmap

- [ ] Additional database connectors (PostgreSQL, Oracle, Cassandra)
- [ ] Parallel migration workers
- [ ] Real-time monitoring dashboards
- [ ] Machine learning schema matching
- [ ] Data quality scoring
- [ ] Advanced partitioning strategies
- [ ] Event-driven triggers
