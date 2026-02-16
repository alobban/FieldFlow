# Sport League System
Sport League System is an app that manages sports leagues, matches and pickups.

## Requirements

### Docker
**NOTE**: PGADMIN_EMAIL has to be of a valid email format else PG Admin won't start reliably and will be in an endless loop of restarts.
```bash
docker-compose --env-file ../.env build --no-cache
docker-compose --env-file ../.env up -d
```

### Pipenv
Automatically install and manage packages with **pipenv** package. Two options install `Pipenv`:

- Manually create VirtualEnv and install **pipenv**
```bash
python3 -m venv <virtual-env-name>
source <virtual-env-name>/bin/activate
pip install pipenv
```

- Automatically generate VirtualEnv with the installation of **pipenv**
```bash
pip install --user pipenv
```
### Install Packages
Install the packages listed in the `Pipfile` file by running the following commands:
```bash
cd fastAPI-backend
pipenv install
```

### Run Lint
After all packages have been installed, you can run lint inside Virtualenv. So first activate venv, if not already.
```bash
pipenv shell
pipenv run lint
```

### Run Test
To run available tests, within the venv, run the following command:
```bash
pipenv run test
```

## Run API
### Postgres Database
First lets get the database up and running. Ensure that the environment variables are loaded in **.env** file.
```bash
docker-compose --env-file ../.env up -d
```