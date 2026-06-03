variable "project" {
  type    = string
  default = "viberoi"
}

variable "env" {
  type        = string
  description = "dev | staging | prod"
}

variable "domain" {
  type        = string
  description = "Apex domain — e.g. viberoi.io. Cert covers this + SANs."
}

variable "subject_alternative_names" {
  type        = list(string)
  description = "All other names the cert should cover. Empty list = apex only."
  default     = []
}

variable "tags" {
  type    = map(string)
  default = {}
}
