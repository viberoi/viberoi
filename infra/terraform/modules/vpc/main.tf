# VPC + subnets + NAT + (optional) VPC endpoints.
#
# Subnet plan (per AZ, with /16 root + /20 subnets):
#   public  - ALB + NAT
#   private - ECS Fargate tasks, Lambdas (egress via NAT)
#   data    - RDS + ElastiCache (no egress)
#
# `single_nat = true` puts all private subnets through one NAT gateway in
# the first AZ. Cuts cost ~$32/AZ. The trade-off is that if that AZ
# fails, private subnets in other AZs lose outbound. Acceptable in dev,
# NOT in prod - flip `single_nat = false` there.

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  prefix = "${var.project}-${var.env}"
  azs    = slice(data.aws_availability_zones.available.names, 0, var.az_count)

  # Carve the /16 into /20 chunks per (subnet-kind × AZ).
  # First 3 AZs of public, then private, then data.
  public_cidrs  = [for i in range(var.az_count) : cidrsubnet(var.cidr_block, 4, i)]
  private_cidrs = [for i in range(var.az_count) : cidrsubnet(var.cidr_block, 4, i + 4)]
  data_cidrs    = [for i in range(var.az_count) : cidrsubnet(var.cidr_block, 4, i + 8)]

  common_tags = merge(
    {
      Project   = var.project
      Env       = var.env
      ManagedBy = "terraform"
      Module    = "vpc"
    },
    var.tags,
  )
}

# ── VPC ────────────────────────────────────────────────────────────────────
resource "aws_vpc" "this" {
  cidr_block           = var.cidr_block
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(local.common_tags, { Name = "${local.prefix}-vpc" })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags   = merge(local.common_tags, { Name = "${local.prefix}-igw" })
}

# ── Subnets ────────────────────────────────────────────────────────────────
resource "aws_subnet" "public" {
  count                   = var.az_count
  vpc_id                  = aws_vpc.this.id
  cidr_block              = local.public_cidrs[count.index]
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "${local.prefix}-public-${count.index}"
    Tier = "public"
  })
}

resource "aws_subnet" "private" {
  count             = var.az_count
  vpc_id            = aws_vpc.this.id
  cidr_block        = local.private_cidrs[count.index]
  availability_zone = local.azs[count.index]

  tags = merge(local.common_tags, {
    Name = "${local.prefix}-private-${count.index}"
    Tier = "private"
  })
}

resource "aws_subnet" "data" {
  count             = var.az_count
  vpc_id            = aws_vpc.this.id
  cidr_block        = local.data_cidrs[count.index]
  availability_zone = local.azs[count.index]

  tags = merge(local.common_tags, {
    Name = "${local.prefix}-data-${count.index}"
    Tier = "data"
  })
}

# ── NAT Gateway(s) ─────────────────────────────────────────────────────────
# One NAT in AZ 0 if single_nat, else one per AZ. Each NAT needs a public EIP.
locals {
  nat_count = var.single_nat ? 1 : var.az_count
}

resource "aws_eip" "nat" {
  count  = local.nat_count
  domain = "vpc"

  tags = merge(local.common_tags, { Name = "${local.prefix}-nat-eip-${count.index}" })

  depends_on = [aws_internet_gateway.this]
}

resource "aws_nat_gateway" "this" {
  count         = local.nat_count
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = merge(local.common_tags, { Name = "${local.prefix}-nat-${count.index}" })

  depends_on = [aws_internet_gateway.this]
}

# ── Route tables ───────────────────────────────────────────────────────────
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = merge(local.common_tags, { Name = "${local.prefix}-rt-public" })
}

resource "aws_route_table_association" "public" {
  count          = var.az_count
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Private subnets - one RT per AZ so we can either pin them all to one
# NAT (single_nat) or fan out one NAT per AZ.
resource "aws_route_table" "private" {
  count  = var.az_count
  vpc_id = aws_vpc.this.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.this[var.single_nat ? 0 : count.index].id
  }

  tags = merge(local.common_tags, { Name = "${local.prefix}-rt-private-${count.index}" })
}

resource "aws_route_table_association" "private" {
  count          = var.az_count
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# Data subnets - RDS / Redis. NO outbound - RDS doesn't need internet
# access; if a service needs to reach the internet from data, it should
# be in private instead.
resource "aws_route_table" "data" {
  vpc_id = aws_vpc.this.id
  tags   = merge(local.common_tags, { Name = "${local.prefix}-rt-data" })
}

resource "aws_route_table_association" "data" {
  count          = var.az_count
  subnet_id      = aws_subnet.data[count.index].id
  route_table_id = aws_route_table.data.id
}

# ── VPC endpoints (optional) ───────────────────────────────────────────────
# Gateway endpoints (free) - S3, DynamoDB.
resource "aws_vpc_endpoint" "s3" {
  count             = var.enable_vpc_endpoints ? 1 : 0
  vpc_id            = aws_vpc.this.id
  service_name      = "com.amazonaws.${data.aws_region.current.name}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = concat(aws_route_table.private[*].id, [aws_route_table.data.id])

  tags = merge(local.common_tags, { Name = "${local.prefix}-vpce-s3" })
}

resource "aws_vpc_endpoint" "dynamodb" {
  count             = var.enable_vpc_endpoints ? 1 : 0
  vpc_id            = aws_vpc.this.id
  service_name      = "com.amazonaws.${data.aws_region.current.name}.dynamodb"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = aws_route_table.private[*].id

  tags = merge(local.common_tags, { Name = "${local.prefix}-vpce-dynamodb" })
}

data "aws_region" "current" {}
