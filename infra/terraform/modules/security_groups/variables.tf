variable "project" {
  type    = string
  default = "viberoi"
}

variable "env" {
  type        = string
  description = "dev | staging | prod"
}

variable "vpc_id" {
  type        = string
  description = "VPC the security groups live in."
}

variable "tags" {
  type    = map(string)
  default = {}
}
