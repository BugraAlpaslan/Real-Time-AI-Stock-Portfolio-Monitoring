#!/usr/bin/env bash
set -euo pipefail
awslocal s3 mb s3://portfolio-exports || true
awslocal s3 mb s3://portfolio-analysis || true
echo "S3 buckets ready"
