# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-04-06

### Added
- Initial project release
- CLI with analyze, plan, migrate, rollback, and validate commands
- Schema analyzer using Claude API for intelligent data analysis
- Migration planner for automated table and bucket design
- Conflict resolver for handling schema inconsistencies
- Cost estimator for S3 and DynamoDB
- Multiple data connectors (MongoDB, filesystem, JSON/CSV)
- DynamoDB and S3 migrators with manifest tracking
- Data integrity validator for post-migration verification
- PII scanner with regex and Claude-powered analysis
- Encryption configuration validator
- Credential manager with secure secret handling
- Resource tagger for AWS resource organization
- Migration manifest tracking for rollback capability
- Terraform modules for S3 and DynamoDB infrastructure
- Comprehensive test suite with moto mocking
