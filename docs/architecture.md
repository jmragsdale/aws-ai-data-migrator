# AWS AI Data Migrator - Architecture

## Overview

AWS AI Data Migrator is an LLM-powered CLI tool that automates the analysis, planning, and execution of data migrations to AWS S3 and DynamoDB. The system uses Claude AI to intelligently analyze source data schemas, resolve inconsistencies, and generate optimized migration plans.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI Interface                           │
│  (analyze, plan, migrate, validate, rollback commands)       │
└────────────────┬────────────────────────────────────────────┘
                 │
         ┌───────┴───────┬──────────────┬──────────────┐
         │               │              │              │
    ┌────▼────┐    ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
    │ Agent   │    │Connectors│   │Migrators│   │Validators
    │Modules  │    │          │   │         │   │
    └─────────┘    └──────────┘   └─────────┘   └──────────┘
         │               │              │              │
    ┌────┴──────┐  ┌────┴──────┐ ┌────┴──────┐  ┌────┴──────┐
    │ Analyzer  │  │  MongoDB   │ │ DynamoDB  │  │ Integrity │
    │ Planner   │  │  Filesystem│ │ S3        │  │ Validator │
    │ Resolver  │  │  JSON/CSV  │ │           │  │           │
    │ Cost Est. │  │            │ │           │  │           │
    └───────────┘  └────────────┘ └───────────┘  └───────────┘
         │
    ┌────▼────────────────────────────────────────────┐
    │      Claude AI via Anthropic API                │
    │  (Schema analysis, Planning, Conflict resolution)
    └─────────────────────────────────────────────────┘
         │
    ┌────▼────────────────────────────────────────────┐
    │            AWS Services                        │
    │      (DynamoDB, S3, CloudWatch)                │
    └─────────────────────────────────────────────────┘
```

## Module Responsibilities

### CLI (`src/cli.py`)
- Entry point for all user commands
- Command orchestration: analyze, plan, migrate, rollback, validate
- User-friendly output using Rich library
- Configuration management and credential validation
- Error handling and logging

**Commands:**
- `analyze` - Discover and analyze source data schema
- `plan` - Generate migration plan with cost estimates
- `migrate` - Execute migration to S3 and DynamoDB
- `rollback` - Delete all migrated resources
- `validate` - Verify data integrity post-migration

### Agent Modules (`src/agent/`)

#### Analyzer (`analyzer.py`)
**Purpose:** Intelligently analyze unstructured data schemas

**Responsibilities:**
- Sample documents from various sources
- Call Claude API to infer field types and patterns
- Detect implicit schemas across documents
- Identify data inconsistencies
- Generate structured analysis report

**Key Methods:**
- `analyze_documents()` - Main analysis entry point
- `detect_inconsistencies()` - Find field type mismatches
- `infer_field_types()` - Determine Python types
- `_infer_type()` - Type inference for individual values

**Claude Prompt Focus:**
- Acts as database schema expert
- Analyzes sample documents for patterns
- Detects relationships between fields
- Recommends schema design

#### Planner (`planner.py`)
**Purpose:** Generate comprehensive migration architecture plans

**Responsibilities:**
- Take analyzer output as input
- Call Claude API for architectural recommendations
- Design DynamoDB table structure (keys, GSIs, billing mode)
- Plan S3 bucket organization and lifecycle rules
- Estimate resource requirements
- Generate Terraform configuration

**Key Methods:**
- `generate_plan()` - Create migration plan from analysis
- `validate_plan()` - Verify plan completeness
- `create_terraform_config()` - Generate IaC

**Claude Prompt Focus:**
- Acts as migration architect
- Recommends partition/sort keys based on access patterns
- Suggests GSI design
- Plans S3 folder structure
- Optimizes for cost and performance

#### Resolver (`resolver.py`)
**Purpose:** Resolve data inconsistencies with intelligent strategies

**Responsibilities:**
- Accept inconsistency reports from analyzer
- Call Claude API to recommend resolution strategies
- Provide options: coerce, split, nullable, skip, transform
- Generate implementation guidance
- Apply transformations to documents

**Key Methods:**
- `resolve_inconsistencies()` - Generate resolution strategies
- `apply_resolution()` - Transform documents
- `_coerce_value()` - Type coercion logic
- `generate_resolution_report()` - Human-readable guidance

**Claude Prompt Focus:**
- Acts as data consistency expert
- Recommends pragmatic resolution approaches
- Considers data loss trade-offs
- Provides implementation details

#### Cost Estimator (`cost_estimator.py`)
**Purpose:** Estimate AWS resource costs

**Responsibilities:**
- Calculate S3 storage costs by class
- Estimate DynamoDB costs (on-demand vs provisioned)
- Include data transfer estimates
- Generate cost breakdown reports
- Support multi-month projections

**Key Methods:**
- `estimate_s3_costs()` - S3 storage cost calculation
- `estimate_dynamodb_costs()` - DynamoDB cost calculation
- `generate_cost_report()` - Formatted cost report

### Connectors (`src/connectors/`)
**Purpose:** Abstract data source interactions

#### MongoDB Connector
- Connect to MongoDB clusters
- List databases and collections
- Sample documents efficiently
- Stream documents in batches
- Gather collection statistics

#### Filesystem Connector
- Scan directories recursively
- Categorize files by type
- Extract file metadata (size, date, MIME type)
- Stream files for upload
- Generate directory statistics

#### JSON/CSV Connector
- Load JSON (single or array)
- Load CSV with auto-delimiter detection
- Normalize nested JSON structures
- Batch streaming support
- File statistics

### Migrators (`src/migrators/`)
**Purpose:** Execute AWS resource creation and data migration

#### DynamoDB Migrator
**Responsibilities:**
- Create tables with proper key schemas
- Design GSIs based on access patterns
- Batch write items with exponential backoff
- Handle table lifecycle (create, wait, delete)
- Enable PITR and encryption
- Track progress and manifest entries

**Key Methods:**
- `create_table()` - Table creation with configuration
- `batch_write_items()` - Resilient batch writes
- `wait_for_table()` - Polling for table readiness
- `enable_point_in_time_recovery()` - Enable PITR
- `delete_table()` - Clean rollback
- `get_table_stats()` - Post-migration verification

#### S3 Migrator
**Responsibilities:**
- Create buckets with proper configuration
- Upload files with multipart for large objects
- Apply tags to objects for organization
- Handle lifecycle rules automatically
- Enable versioning and encryption
- Track upload progress

**Key Methods:**
- `create_bucket()` - Bucket creation with security
- `upload_file()` - Single file upload with multipart support
- `upload_batch()` - Batch upload with error handling
- `_tag_object()` - Apply tags to objects
- `delete_bucket()` - Clean rollback
- `get_bucket_stats()` - Verify upload success

### Validators (`src/validators/`)

#### Integrity Validator
**Purpose:** Verify post-migration data correctness

**Responsibilities:**
- Compare source vs destination record counts
- Spot-check random samples for accuracy
- Verify S3 object existence and sizes
- Generate validation reports
- Support pass/fail determination

**Key Methods:**
- `validate_s3_migration()` - S3 validation
- `validate_dynamodb_migration()` - DynamoDB validation
- `validate_migration()` - Combined validation
- `generate_validation_report()` - Formatted report

### Security (`src/security/`)

#### Credential Manager
- Load AWS credentials (profile, env vars, IAM roles)
- Load Anthropic API key
- Validate credentials at startup
- Mask sensitive values in logs
- Provide boto3 clients

#### PII Scanner
- Detect common PII patterns (SSN, email, phone, CC, IP)
- Call Claude for deep PII analysis
- Generate risk reports with recommendations
- Suggest actions (encrypt, redact, flag)

#### Encryption Config
- Validate S3/DynamoDB encryption settings
- Generate encryption Terraform code
- Support SSE-S3 and SSE-KMS
- Configuration validation

### Utilities (`src/utils/`)

#### Config
- Load configuration from .env
- Validate required fields
- Provide sensible defaults
- Singleton pattern for global access

#### Logger
- Configured logging with file/console output
- Sensitive data masking (API keys, URIs)
- Structured logging with timestamps
- Configurable log levels

#### Tagger
- Generate standard AWS resource tags
- Apply tags to S3 objects and DynamoDB tables
- Merge custom tags with defaults
- Cost allocation and organization

#### Manifest
- Track all created resources
- JSON-based persistence
- Load manifest for rollback operations
- Resource ARN and metadata storage

## Data Flow

### Analyze Phase
```
Source Data → Connector → Sampled Documents
                              ↓
                        Claude Analyzer
                              ↓
                        Schema Analysis
                              ↓
                        JSON Report
```

### Plan Phase
```
Schema Analysis → Claude Planner
                        ↓
                  Migration Plan
                        ↓
                  Cost Estimator
                        ↓
                Cost Breakdown Report
```

### Migrate Phase
```
Source Data → Connector
                   ↓
        ┌─────────┴─────────┐
        ↓                   ↓
    S3 Migrator      DynamoDB Migrator
        ↓                   ↓
    S3 Objects      DynamoDB Items
        ↓                   ↓
    Manifest Entry   Manifest Entry
        ↓                   ↓
        └─────────┬─────────┘
                  ↓
          Migration Manifest
```

### Validate Phase
```
S3 Bucket → Integrity Validator ← DynamoDB Table
                    ↓
            Validation Report
```

### Rollback Phase
```
Migration Manifest → Resource Iterator
                          ↓
        ┌─────────────────┼─────────────────┐
        ↓                 ↓                 ↓
    Delete S3         Delete DynamoDB   Update Manifest
        ↓                 ↓
        └─────────────────┴─────────────────┘
                    ↓
            Rollback Complete
```

## Technology Stack

- **Language:** Python 3.9+
- **CLI Framework:** Click
- **AWS SDK:** boto3
- **LLM Integration:** Anthropic Python SDK
- **Database Connectors:** pymongo
- **Testing:** pytest, moto (AWS mocking)
- **IaC:** Terraform
- **UI:** Rich (formatted output)

## Error Handling Strategy

1. **Connector Errors:** Graceful degradation with detailed messages
2. **API Errors:** Exponential backoff retry (3 attempts)
3. **AWS Errors:** Specific handling (ResourceInUseException, etc.)
4. **Validation Errors:** Report issues, don't fail silently

## Security Considerations

1. **Credential Management:** Uses boto3 standard mechanisms
2. **Sensitive Data:** Masked in logs and output
3. **PII Detection:** Pre-migration scanning with recommendations
4. **Encryption:** Enforced for S3 and DynamoDB
5. **Access Control:** Public access blocked by default

## Scalability

- **Batch Processing:** Handles large datasets in configurable batches
- **Streaming:** Files streamed to avoid memory overload
- **Pagination:** S3 and DynamoDB pagination support
- **Exponential Backoff:** Prevents API rate limiting
- **Cost Monitoring:** Estimates provided before execution

## Testing Strategy

- **Unit Tests:** Individual component testing with mocks
- **Integration Tests:** AWS service mocking with moto
- **Fixtures:** Reusable test data and cloud resources
- **Coverage:** All major code paths covered

## Future Enhancements

- Support for additional sources (PostgreSQL, Oracle, etc.)
- Parallel migration workers for improved throughput
- Real-time monitoring dashboards
- Machine learning for schema matching
- Automated partitioning strategies
- Data quality scoring
