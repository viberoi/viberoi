output "primary_endpoint_address" {
  description = "Hostname for REDIS_URL. TLS is enforced — use rediss:// not redis://."
  value       = aws_elasticache_replication_group.this.primary_endpoint_address
}

output "reader_endpoint_address" {
  description = "Reader endpoint — only meaningful when num_cache_clusters > 1."
  value       = aws_elasticache_replication_group.this.reader_endpoint_address
}

output "port" {
  value = aws_elasticache_replication_group.this.port
}

output "replication_group_id" {
  value = aws_elasticache_replication_group.this.id
}
