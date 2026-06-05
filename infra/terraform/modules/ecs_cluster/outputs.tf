output "cluster_id" {
  description = "Cluster id - passed into every ECS service."
  value       = aws_ecs_cluster.this.id
}

output "cluster_name" {
  value = aws_ecs_cluster.this.name
}

output "cluster_arn" {
  value = aws_ecs_cluster.this.arn
}
