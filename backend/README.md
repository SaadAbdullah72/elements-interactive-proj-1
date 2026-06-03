# Backend Structure

This folder contains all backend code and data for the IntelliHealth application.

## Folder Structure

```
backend/
├── main.py                          # Main entry point for the backend application
├── auth.py                          # Authentication logic
├── doctor_auth.py                   # Doctor-specific authentication
├── mongo.py                         # MongoDB connection and utilities
├── email_service.py                 # Email sending functionality
├── profile.py                       # User profile management
├── ada_guidelines_engine.py          # ADA guidelines processing engine
├── requirements.txt                 # Python dependencies
│
├── parsers/                         # PDF and data parsing utilities
│   ├── extract_all_pdfs.py          # Extract content from all PDFs
│   ├── extract_key_recommendations.py # Extract key recommendations from documents
│   ├── extract_recommendations.py   # Extract recommendations
│   ├── parsedata.py                 # Data parsing utilities
│   ├── thecsv.py                    # CSV processing
│   └── tmp_pdf_extract.py           # Temporary PDF extraction script
│
├── scripts/                         # Utility and setup scripts
│   ├── seed_dummy_data.py           # Seed database with dummy data
│   ├── setup_doctor.py              # Doctor account setup
│   ├── demo_case_studies.py         # Demo case study data
│   ├── demo_case_study.py           # Additional demo cases
│   ├── migrate_mongodb_fast.py       # MongoDB migration tool
│   ├── reset_email_tracking.py      # Reset email tracking state
│   ├── test.py                      # Basic tests
│   ├── test_import.py               # Import testing
│   ├── test_diagnosis_email.py      # Email diagnosis testing
│   └── main_backup.py               # Backup of main application
│
├── data/                            # Data files and datasets
│   ├── drug_disease_map.csv         # Drug-disease interaction mapping
│   ├── drug_interactions.csv        # Drug interaction data
│   ├── drug_reaction_map.csv        # Drug reaction mapping
│   ├── symptom_disease_map.csv      # Symptom-disease mapping
│   ├── medical_knowledge_graph.json # Knowledge graph data
│   ├── faers_clean_dataset.csv      # Cleaned FAERS dataset
│   ├── faers_parsed_dataset.csv     # Parsed FAERS data
│   ├── faers_xml_2025Q4/            # FAERS XML data Q4 2025
│   ├── 14. Children and Adolescents.txt
│   ├── 15. Management of Diabetes in Pregnancy.txt
│   └── 16. Diabetes Care in the Hospital.txt
│
├── docs/                            # Documentation
│   └── MONGODB_MIGRATION_GUIDE.md
│
└── utils/                           # Utility modules (reserved for future use)
```

## Setup Instructions

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment variables in `.env` file at project root

3. Run the main application:
   ```bash
   python main.py
   ```

## Running Scripts

To run setup or migration scripts:
```bash
python scripts/setup_doctor.py
python scripts/seed_dummy_data.py
python scripts/migrate_mongodb_fast.py
```

## Data Files

All data files are stored in the `data/` folder:
- **CSV Files**: Drug mappings, disease mappings, and FAERS datasets
- **JSON Files**: Knowledge graph data
- **Text Files**: Medical guidelines and recommendations
- **XML Files**: FAERS data in XML format (in faers_xml_2025Q4 subdirectory)

## Testing

Run tests using:
```bash
python scripts/test.py
python scripts/test_import.py
python scripts/test_diagnosis_email.py
```
