resource "aws_dynamodb_table" "main" {
  name           = var.table_name
  billing_mode   = var.billing_mode
  hash_key       = var.partition_key_name
  range_key      = var.sort_key_name
  stream_enabled = true
  stream_view_specification {
    stream_view_type = "NEW_AND_OLD_IMAGES"
  }

  attribute {
    name = var.partition_key_name
    type = var.partition_key_type
  }

  dynamic "attribute" {
    for_each = var.sort_key_name != null ? [var.sort_key_name] : []
    content {
      name = var.sort_key_name
      type = var.sort_key_type
    }
  }

  # GSI attributes
  dynamic "attribute" {
    for_each = var.global_secondary_indexes
    content {
      name = attribute.value.partition_key
      type = attribute.value.partition_type
    }
  }

  dynamic "attribute" {
    for_each = [for gsi in var.global_secondary_indexes : gsi if gsi.sort_key != null]
    content {
      name = attribute.value.sort_key
      type = attribute.value.sort_type
    }
  }

  # Global Secondary Indexes
  dynamic "global_secondary_index" {
    for_each = var.global_secondary_indexes
    content {
      name            = global_secondary_index.value.name
      hash_key        = global_secondary_index.value.partition_key
      range_key       = global_secondary_index.value.sort_key
      projection_type = global_secondary_index.value.projection_type

      dynamic "provisioned_throughput" {
        for_each = var.billing_mode == "PROVISIONED" ? [1] : []
        content {
          read_capacity_units  = global_secondary_index.value.read_capacity
          write_capacity_units = global_secondary_index.value.write_capacity
        }
      }
    }
  }

  # Provisioned throughput for main table
  dynamic "provisioned_throughput" {
    for_each = var.billing_mode == "PROVISIONED" ? [1] : []
    content {
      read_capacity_units  = var.read_capacity
      write_capacity_units = var.write_capacity
    }
  }

  # Point-in-time recovery
  point_in_time_recovery {
    enabled = var.point_in_time_recovery
  }

  # Server-side encryption
  dynamic "server_side_encryption" {
    for_each = var.enable_encryption ? [1] : []
    content {
      enabled = true
    }
  }

  # TTL (optional - can be set based on use case)
  # ttl {
  #   attribute_name = "expires_at"
  #   enabled        = true
  # }

  tags = var.tags

  lifecycle {
    ignore_changes = [
      read_capacity,
      write_capacity,
    ]
  }
}
