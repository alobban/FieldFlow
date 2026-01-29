# Sport League System
Sport League System is an app that manages sports leagues, matches and pickups.

## Requirements

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