variable "table_name" {
  description = "Name of the DynamoDB table"
  type        = string
}

variable "partition_key_name" {
  description = "Partition key attribute name"
  type        = string
}

variable "partition_key_type" {
  description = "Partition key attribute type (S, N, B)"
  type        = string
  default     = "S"
}

variable "sort_key_name" {
  description = "Sort key attribute name (optional)"
  type        = string
  default     = null
}

variable "sort_key_type" {
  description = "Sort key attribute type (S, N, B)"
  type        = string
  default     = "S"
}

variable "billing_mode" {
  description = "Billing mode (PROVISIONED or PAY_PER_REQUEST)"
  type        = string
  default     = "PAY_PER_REQUEST"
}

variable "read_capacity" {
  description = "Read capacity units for provisioned mode"
  type        = number
  default     = 5
}

variable "write_capacity" {
  description = "Write capacity units for provisioned mode"
  type        = number
  default     = 5
}

variable "enable_pitr" {
  description = "Enable point-in-time recovery"
  type        = bool
  default     = true
}

variable "point_in_time_recovery" {
  description = "Enable point-in-time recovery"
  type        = bool
  default     = true
}

variable "enable_encryption" {
  description = "Enable server-side encryption"
  type        = bool
  default     = true
}

variable "global_secondary_indexes" {
  description = "List of global secondary indexes"
  type = list(object({
    name            = string
    partition_key   = string
    partition_type  = string
    sort_key        = optional(string)
    sort_type       = optional(string)
    projection_type = optional(string, "ALL")
    read_capacity   = optional(number, 5)
    write_capacity  = optional(number, 5)
  }))
  default = []
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
