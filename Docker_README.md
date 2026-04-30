# Lancement de l'application via Docker

## Prérequis

- Avoir Docker installé sur votre machine.
- Avoir cloné le repo de l'application.

## Étapes pour lancer l'application

1. Ouvrez un terminal et naviguez jusqu'au répertoire racine de l'application.
2. Construisez les images Docker en utilisant les commandes suivante :

   ```bash
   docker build -t dockerfile.api fbpred_api:tag
   docker build -t dockerfile.apiml fbpred_ml:tag
   docker build -t dockerfile.front fbpred_front:tag
   ```

3. Récupérez l'image officielle de PostgreSQL :

   ```bash
   docker login dhi.io
        # Entrez vos identifiants de connexion pour dhi.io
   docker pull dhi.io/postgres:18-alpine3.22-dev
   ```

    3.1 Créez les bases de données nécessaires pour l'application :

    ```bash
    docker run --name fbpred_db -e POSTGRES_USER=fbpred_user -e POSTGRES_PASSWORD=fbpred_password -d dhi.io/postgres:18-alpine3.22-dev

    docker exec -it fbpred_db psql -U postgres

    CREATE DATABASE fbpred_ml;
    CREATE DATABASE fbpred_app;
    ```

    3.2 Créez un volume Docker pour persister les données de la base de données :

    ```bash
    docker volume create fbpred_db_data
    ```

    3.3 Montez le volume dans le conteneur de la base de données pour assurer la persistance des données :

    ```bash
    docker run --name fbpred_db -e POSTGRES_USER=fbpred_user -e POSTGRES_PASSWORD=fbpred_password -v fbpred_db_data:/var/lib/postgresql/data -d dhi.io/postgres:18-alpine3.22-dev
    ```

4. Créez un réseau Docker pour permettre la communication entre les conteneurs :

   ```bash
   docker network create fbpred_network
   ```

5. Lancez les conteneurs pour l'API, le ML et le front-end en les connectant au réseau créé :

   ```bash
   docker run -d --name fbpred_api --network fbpred_network -p 8000:8000 dockerfile.api
   docker run -d --name fbpred_ml --network fbpred_network -p 8001:8001 dockerfile.apiml
   docker run -d --name fbpred_front --network fbpred_network -p 80:80 dockerfile.front
   ```

6. Vérifiez que les conteneurs sont en cours d'exécution :

   ```bash
   docker ps
   ```

7. Accédez à l'application via votre navigateur en utilisant l'adresse suivante :

   > http://localhost:8000 | http://localhost:8001 | http://localhost:80
