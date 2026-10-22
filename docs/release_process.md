# Release process

### 1. Add changelog

Add an entry for the new version at the top of `docs/changelog.rst`.

### 2. Update version number

Both files must have the same version (it is shown to clients by `server.version`, in the banner and in the logs):

- `docs/conf.py`
- `src/electrumx/__init__.py`

### 3. Check

The CI on `main` (`.github/workflows/ci.yml`) must pass: tests, pycodestyle, docs build, and the Docker image with its
smoke test (`contrib/docker-smoke-test.sh`).

### 4. Deploy

On the server: `git pull && docker compose up -d --build` (see `DEPLOY.md`).
