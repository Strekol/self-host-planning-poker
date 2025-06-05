# Configuration de base de données externe pour Planning Poker

Ce projet supporte maintenant plusieurs types de bases de données pour le déploiement en production, notamment dans des environnements Kubernetes.

## Types de bases de données supportées

- **SQLite** (par défaut, pour le développement et les déploiements simples)
- **PostgreSQL** (recommandé pour la production)
- **MySQL** (alternative pour la production)

## Configuration

### Option 1: Variables d'environnement séparées

```bash
# Type de base de données
DATABASE_TYPE=postgresql  # ou mysql, sqlite

# Paramètres de connexion
DATABASE_HOST=postgres-service
DATABASE_PORT=5432
DATABASE_NAME=planning_poker
DATABASE_USER=planning_poker_user
DATABASE_PASSWORD=your-password

# Pour PostgreSQL uniquement
DATABASE_SSL_MODE=prefer  # require, prefer, disable

# Pour MySQL uniquement
DATABASE_CHARSET=utf8mb4
```

### Option 2: URL de base de données (recommandée)

```bash
# PostgreSQL
DATABASE_URL=postgresql://username:password@host:port/database

# MySQL
DATABASE_URL=mysql://username:password@host:port/database

# SQLite
DATABASE_URL=sqlite:///path/to/database.db
```

### Variables d'environnement supplémentaires

```bash
# Mode debug (active CORS pour le développement)
FLASK_DEBUG=true  # ou false pour la production

# Clé secrète Flask (obligatoire en production)
SECRET_KEY=your-secret-key-here

# Pour SQLite uniquement: chemin personnalisé
DATABASE_PATH=/custom/path/database.db
```

## Déploiement Kubernetes

### 1. Avec PostgreSQL

Utilisez le fichier `k8s-deployment-postgresql.yaml` comme exemple. Ce déploiement :

- Configure une base de données PostgreSQL externe
- Utilise des ConfigMaps pour la configuration non-sensible
- Utilise des Secrets pour les mots de passe
- Inclut des sondes de santé et des limites de ressources
- Configure un Ingress avec TLS

```bash
# Modifiez les valeurs dans le fichier YAML, puis :
kubectl apply -f k8s-deployment-postgresql.yaml
```

### 2. Avec MySQL

Utilisez le fichier `k8s-deployment-mysql.yaml` :

```bash
kubectl apply -f k8s-deployment-mysql.yaml
```

### 3. Configuration simplifiée avec DATABASE_URL

Utilisez le fichier `k8s-deployment-database-url.yaml` pour une configuration plus simple :

```bash
kubectl apply -f k8s-deployment-database-url.yaml
```

## Migration depuis SQLite

Si vous migrez depuis une installation SQLite existante :

1. **Exportez vos données** depuis SQLite
2. **Créez la base de données** cible (PostgreSQL/MySQL)
3. **Configurez les variables d'environnement** pour la nouvelle base
4. **Redémarrez l'application** - les tables seront créées automatiquement
5. **Importez vos données** dans la nouvelle base

Note: Un script de migration automatique pourrait être développé si nécessaire.

## Développement local

Pour le développement, vous pouvez continuer à utiliser SQLite :

```bash
# Mode debug avec SQLite local
FLASK_DEBUG=true
DATABASE_TYPE=sqlite
DATABASE_PATH=./development.db
```

Ou tester avec une base de données externe :

```bash
# PostgreSQL local avec Docker
docker run --name postgres-dev -e POSTGRES_PASSWORD=devpass -e POSTGRES_DB=planning_poker -p 5432:5432 -d postgres:13

# Configuration pour l'application
DATABASE_TYPE=postgresql
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=planning_poker
DATABASE_USER=postgres
DATABASE_PASSWORD=devpass
FLASK_DEBUG=true
```

## Bonnes pratiques

### Sécurité

- **Utilisez toujours des Secrets Kubernetes** pour les mots de passe
- **Activez SSL/TLS** pour les connexions de base de données en production
- **Utilisez des utilisateurs dédiés** avec des permissions minimales
- **Évitez d'exposer les secrets** dans les logs

### Performance

- **Configurez un pool de connexions** approprié pour votre charge
- **Utilisez des réplicas multiples** de l'application pour la haute disponibilité
- **Surveillez les métriques** de base de données et d'application
- **Configurez des sondes de santé** appropriées

### Haute disponibilité

- **Utilisez des bases de données managées** (AWS RDS, Google Cloud SQL, etc.)
- **Configurez des sauvegardes automatiques**
- **Testez la restauration** régulièrement
- **Utilisez plusieurs réplicas** de l'application

## Surveillance et debugging

L'application affiche des informations sur la configuration de base de données au démarrage :

```
INFO:__main__:Database configured: PostgreSQL: user@host:5432/database
```

Pour débugger les problèmes de connexion :

1. Vérifiez les logs de l'application
2. Testez la connectivité réseau vers la base de données
3. Vérifiez les credentials et permissions
4. Assurez-vous que la base de données existe

## Exemple complet

Voici un exemple complet de déploiement avec PostgreSQL externe :

```yaml
# Configuration dans votre namespace
apiVersion: v1
kind: Secret
metadata:
  name: planning-poker-db
type: Opaque
stringData:
  DATABASE_URL: "postgresql://planning_poker:secure_password@postgres.example.com:5432/planning_poker_prod"
  SECRET_KEY: "very-secret-key-for-production"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: planning-poker
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: planning-poker
        image: your-registry/planning-poker:v1.0.0
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: planning-poker-db
              key: DATABASE_URL
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: planning-poker-db
              key: SECRET_KEY
        - name: FLASK_DEBUG
          value: "false"
```

Cette configuration est prête pour un environnement de production avec une base de données PostgreSQL externe.
