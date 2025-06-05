#!/bin/bash

# Script de construction et déploiement pour Planning Poker
# Usage: ./build-and-deploy.sh [options]

set -e

# Configuration par défaut
IMAGE_NAME="planning-poker"
IMAGE_TAG="latest"
REGISTRY=""
PUSH_IMAGE=false
DEPLOY_K8S=false
K8S_CONFIG=""
BUILD_ONLY=false

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction d'aide
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -n, --name NAME          Nom de l'image Docker (défaut: planning-poker)"
    echo "  -t, --tag TAG            Tag de l'image Docker (défaut: latest)"
    echo "  -r, --registry REGISTRY  Registry Docker (ex: docker.io/username)"
    echo "  -p, --push               Push l'image vers le registry"
    echo "  -k, --k8s CONFIG         Déploie sur Kubernetes avec le fichier de config spécifié"
    echo "  -b, --build-only         Construit seulement l'image, ne déploie pas"
    echo "  -h, --help               Affiche cette aide"
    echo ""
    echo "Exemples:"
    echo "  $0 --build-only                              # Construction locale uniquement"
    echo "  $0 --push --registry docker.io/username      # Construction et push"
    echo "  $0 --k8s k8s-deployment-postgresql.yaml      # Construction et déploiement K8s"
    echo "  $0 --push --registry myregistry.com/planning-poker --k8s k8s-deployment-postgresql.yaml"
}

# Fonction de log
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✅${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ❌${NC} $1"
}

# Parse des arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -p|--push)
            PUSH_IMAGE=true
            shift
            ;;
        -k|--k8s)
            DEPLOY_K8S=true
            K8S_CONFIG="$2"
            shift 2
            ;;
        -b|--build-only)
            BUILD_ONLY=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "Option inconnue: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validation des arguments
if [[ "$PUSH_IMAGE" == true && -z "$REGISTRY" ]]; then
    log_error "Le registry est requis pour pusher l'image (--registry)"
    exit 1
fi

if [[ "$DEPLOY_K8S" == true && -z "$K8S_CONFIG" ]]; then
    log_error "Le fichier de configuration Kubernetes est requis (--k8s)"
    exit 1
fi

if [[ "$DEPLOY_K8S" == true && ! -f "$K8S_CONFIG" ]]; then
    log_error "Le fichier de configuration Kubernetes '$K8S_CONFIG' n'existe pas"
    exit 1
fi

# Construction du nom complet de l'image
if [[ -n "$REGISTRY" ]]; then
    FULL_IMAGE_NAME="$REGISTRY/$IMAGE_NAME:$IMAGE_TAG"
else
    FULL_IMAGE_NAME="$IMAGE_NAME:$IMAGE_TAG"
fi

log "Début de la construction de Planning Poker"
log "Image: $FULL_IMAGE_NAME"

# Vérification des prérequis
log "Vérification des prérequis..."

if ! command -v docker &> /dev/null; then
    log_error "Docker n'est pas installé ou n'est pas dans le PATH"
    exit 1
fi

if [[ "$DEPLOY_K8S" == true ]] && ! command -v kubectl &> /dev/null; then
    log_error "kubectl n'est pas installé ou n'est pas dans le PATH"
    exit 1
fi

# Vérification de la structure du projet
if [[ ! -f "Dockerfile" ]]; then
    log_error "Dockerfile non trouvé dans le répertoire courant"
    exit 1
fi

if [[ ! -d "angular" || ! -d "flask" ]]; then
    log_error "Répertoires 'angular' et 'flask' requis"
    exit 1
fi

log_success "Prérequis validés"

# Construction de l'image Docker
log "Construction de l'image Docker..."
if docker build --platform linux/amd64,linux/arm64 -t "$FULL_IMAGE_NAME" .; then
    log_success "Image Docker construite avec succès: $FULL_IMAGE_NAME"
else
    log_error "Échec de la construction de l'image Docker"
    exit 1
fi

# Vérification de la configuration de base de données
log "Vérification de la configuration de base de données..."
if python3 check_database_config.py > /dev/null 2>&1; then
    log_success "Configuration de base de données validée"
else
    log_warning "Impossible de valider la configuration de base de données (normal en build)"
fi

# Push de l'image si demandé
if [[ "$PUSH_IMAGE" == true ]]; then
    log "Push de l'image vers le registry..."
    if docker push "$FULL_IMAGE_NAME"; then
        log_success "Image pushée avec succès vers $REGISTRY"
    else
        log_error "Échec du push de l'image"
        exit 1
    fi
fi

# Déploiement Kubernetes si demandé
if [[ "$DEPLOY_K8S" == true && "$BUILD_ONLY" == false ]]; then
    log "Déploiement sur Kubernetes..."
    
    # Mise à jour de l'image dans le fichier de configuration
    temp_config=$(mktemp)
    sed "s|your-registry/planning-poker:latest|$FULL_IMAGE_NAME|g" "$K8S_CONFIG" > "$temp_config"
    
    if kubectl apply -f "$temp_config"; then
        log_success "Déploiement Kubernetes réussi"
        
        # Attendre que les pods soient prêts
        log "Attente que les pods soient prêts..."
        kubectl wait --for=condition=ready pod -l app=planning-poker --timeout=300s 2>/dev/null || true
        
        # Affichage du statut
        echo ""
        log "Statut du déploiement:"
        kubectl get pods -l app=planning-poker
        
    else
        log_error "Échec du déploiement Kubernetes"
        rm -f "$temp_config"
        exit 1
    fi
    
    rm -f "$temp_config"
fi

log_success "Construction et déploiement terminés avec succès!"

# Affichage des commandes utiles
echo ""
log "Commandes utiles:"
echo "  - Vérifier les logs: docker logs <container_id>"
echo "  - Tester localement: docker run -p 8000:8000 $FULL_IMAGE_NAME"
if [[ "$DEPLOY_K8S" == true ]]; then
    echo "  - Logs K8s: kubectl logs -l app=planning-poker"
    echo "  - Port-forward: kubectl port-forward svc/planning-poker-service 8000:80"
fi
