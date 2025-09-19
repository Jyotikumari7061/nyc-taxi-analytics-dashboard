#  Benefit Optimization Dashboard

A full-stack web app that analyzes customer behavior, tracks partner performance, and simulates benefit negotiation strategies—ideal for loyalty-driven platforms like American Express.

## Tech Stack

**Frontend**: React 19, Tailwind CSS, Radix UI, CRACO  
**Backend**: FastAPI, MongoDB (motor), Pydantic v2  
**Dev Tools**: JWT Auth, AWS S3 (boto3), Pytest, Black, ESLint

## Installation

### Frontend
```bash
cd frontend
yarn install
yarn start

cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
