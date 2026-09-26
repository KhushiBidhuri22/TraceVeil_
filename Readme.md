# Darkweb Attribution System

SIH project for deanonymizing dark web threat actors.

## Structure

- `backend/` – FastAPI backend (API, DB, integration with ML & crawler)
- `crawler/` – scrapers for forums/marketplaces
- `ml/` – stylometry & behavioural analysis
- `frontend/` – analyst dashboard
- `infra/` – Docker, deployment scripts
- `docs/` – architecture, API docs, setup guides

# ways to copy to ur system and work 

Clone the repository directly:

git clone https://github.com/KhushiBidhuri22/darkweb-attribution.git
cd darkweb-attribution

Get develop:

git checkout develop
git pull origin develop

Create their own branch:

git checkout -b feature/your-name
Work on their code.

Commit:

git add .
git commit -m "Add <what you worked on>"

Push their branch:

git push -u origin feature/your-name
Create a Pull Request from their branch → develop



