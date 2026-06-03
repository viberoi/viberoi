output "alb_dns_name" {
  description = "ALB DNS name. Create a CNAME at Hostinger pointing api.<domain> here (or use as the only public entry point)."
  value       = aws_lb.this.dns_name
}

output "alb_arn" {
  value = aws_lb.this.arn
}

output "alb_zone_id" {
  description = "Useful if you ever move DNS to Route 53 and want an A-alias instead of CNAME."
  value       = aws_lb.this.zone_id
}

output "target_group_arns" {
  description = "Map service_name → TG ARN. Each ECS service module attaches via its load_balancer arg."
  value = {
    for k, tg in aws_lb_target_group.this : k => tg.arn
  }
}

output "https_listener_arn" {
  value = aws_lb_listener.https.arn
}
