output "table_name" {
  description = "Name of the DynamoDB table"
  value       = aws_dynamodb_table.main.name
}

output "table_arn" {
  description = "ARN of the DynamoDB table"
  value       = aws_dynamodb_table.main.arn
}

output "table_id" {
  description = "ID of the DynamoDB table"
  value       = aws_dynamodb_table.main.id
}

output "table_stream_arn" {
  description = "ARN of the DynamoDB stream"
  value       = aws_dynamodb_table.main.stream_arn
}

output "table_stream_label" {
  description = "Stream label of the DynamoDB table"
  value       = aws_dynamodb_table.main.stream_label
}

output "gsi_names" {
  description = "Names of the global secondary indexes"
  value       = [for gsi in var.global_secondary_indexes : gsi.name]
}
