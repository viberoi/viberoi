output "endpoint" {
  description = "host:port - used in DATABASE_URL."
  value       = aws_db_instance.this.endpoint
}

output "address" {
  description = "Hostname only - convenient for constructing URLs without port."
  value       = aws_db_instance.this.address
}

output "port" {
  value = aws_db_instance.this.port
}

output "db_name" {
  value = aws_db_instance.this.db_name
}

output "master_username" {
  value = aws_db_instance.this.username
}

output "id" {
  description = "DB identifier. Useful for CloudWatch alarms in 6F."
  value       = aws_db_instance.this.id
}

output "arn" {
  value = aws_db_instance.this.arn
}
