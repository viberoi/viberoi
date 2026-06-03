output "queue_arns" {
  description = "Queue ARNs keyed by short name. Used by IAM policies for task roles."
  value = {
    for k, q in aws_sqs_queue.main : k => q.arn
  }
}

output "queue_urls" {
  description = "Queue URLs keyed by short name. Used by application code (though viberoi_shared.sqs resolves by name)."
  value = {
    for k, q in aws_sqs_queue.main : k => q.url
  }
}

output "dlq_arns" {
  description = "DLQ ARNs keyed by short name. CloudWatch alarms attach to these in 6F."
  value = {
    for k, q in aws_sqs_queue.dlq : k => q.arn
  }
}
