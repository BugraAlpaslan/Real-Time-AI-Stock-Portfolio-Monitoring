#!/usr/bin/env bash
set -euo pipefail

minikube start --driver=docker
eval "$(minikube docker-env)"
docker build -t portfolio:dev .
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/ -n portfolio
kubectl rollout status deployment/portfolio-app -n portfolio --timeout=120s
echo "Service: $(minikube service portfolio-app -n portfolio --url)"
