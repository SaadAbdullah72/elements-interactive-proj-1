# IntelliHealth Project Structure

This is a full-stack medical knowledge application with frontend and backend separated.

## Project Layout

```
opencl/
├── backend/                         # Backend Python application (see backend/README.md)
│   ├── main.py
│   ├── requirements.txt
│   ├── auth.py, mongo.py, email_service.py, etc.
│   ├── parsers/                     # PDF and data parsing
│   ├── scripts/                     # Utility and setup scripts
│   ├── data/                        # All datasets and data files
│   ├── docs/                        # Backend documentation
│   └── README.md                    # Backend documentation
│
├── frontend/                        # React frontend application
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── components/              # React components
│   │   └── assets/                  # Images and static files
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── build/                       # Production build output
│
├── .env                             # Environment variables
├── .gitignore                       # Git ignore rules
├── package.json                     # Root dependencies (if any)
├── vercel.json                      # Vercel deployment config
├── MONGODB_MIGRATION_GUIDE.md       # Database migration guide
│
└── node_modules/                    # Frontend dependencies
    (and other temporary files)
```

## Quick Start

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
python main.py
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## Key Directories

- **`backend/`** - All backend Python code, APIs, and data processing
- **`frontend/`** - React SPA (Single Page Application)
- **`backend/data/`** - Datasets, CSV files, knowledge graphs, FAERS data
- **`backend/parsers/`** - PDF extraction and data parsing utilities
- **`backend/scripts/`** - Database setup, migrations, and testing utilities

## Environment Configuration

Create a `.env` file at the root with:
- MongoDB connection URI
- Email service credentials
- API keys and secrets

See `.gitignore` for files that should not be committed.

## Deployment

- Frontend: Vercel (configured in `frontend/vercel.json`)
- Backend: Can be deployed to any Python-capable server

For more details, see:
- [Backend Setup](backend/README.md)
- [MongoDB Migration](MONGODB_MIGRATION_GUIDE.md)
