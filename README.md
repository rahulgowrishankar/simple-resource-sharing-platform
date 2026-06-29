```markdown
# AI-Powered Academic Resource Sharing & RAG Platform

A production-ready academic repository system designed to handle resource distribution, secure user authentication, and advanced data-driven question answering. Built on a clean, maintainable relational structure using MySQL and an intelligent retrieval-augmented generation (RAG) backend.

The platform integrates data parsing engines, semantic search indexing, and real-time LLM validation interfaces to let students dynamically query uploaded institutional materials for contextual, hallucination-free answers.

---

## 🛠️ Core Tech Stack

* **Web Framework:** Python, Flask
* **Relational Storage:** MySQL Database (`mysql-connector-python`)
* **Vector Indexing Vault:** ChromaDB Vector Storage Engine
* **Inference Engines:** Google Gemini 2.5 Flash, Google Text Embedding Model (`text-embedding-004`)
* **Document Parser:** PyPDF text extraction library

---

## Setup (do this once)

### 1. Install the Python packages
```bash
cd simple-platform-mysql
pip install -r requirements.txt

```

### 2. Create the Database

Open **MySQL Command Line Client**, log in with your root password, then run:

```sql
SOURCE C:/path/to/simple-platform-mysql/schema.sql;

```

*(Make sure to adjust the absolute file path to wherever this repository is located on your local drive)*

This initializes a database called `simple_resources` containing the core relational schema tables for managing platform users and assets.

### 3. Configure System Credentials

Create a `.env` file in your root folder (or update your environment variables) to pass your API and database keys:

```env
# Gemini API Key
GEMINI_API_KEY=your_actual_google_ai_studio_key_here

# Database Configuration
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_root_password
MYSQL_DATABASE=simple_resources

```

### 4. Run the Application

```bash
python app.py

```

Open your web browser and navigate to: **http://localhost:5002**

---

## Technical Architecture & RAG Pipeline

1. **Data Ingestion:** Uploaded PDFs are parsed page-by-page using `PyPDF` to extract raw, readable strings.
2. **Text Chunking:** Extracted strings are divided into optimized paragraphs with context overlap to prevent structural split errors.
3. **Vector Indexing:** Paragraph chunks are transformed into 768-dimensional semantic embeddings via `text-embedding-004` and stored permanently inside `ChromaDB`.
4. **Contextual Retrieval:** When a student queries the chatbot interface, the question is mapped into vector coordinates, matched instantly against matching context keys in ChromaDB, and forwarded directly to **Gemini 2.5 Flash** to render highly accurate academic answers.

---

## Troubleshooting

* **"Access denied for user 'root'@'localhost'"** → The password provided in the system configurations or your `.env` file is incorrect or blank.
* **"Unknown database 'simple_resources'"** → The database structure has not been initialized yet. Ensure you successfully executed the `schema.sql` installation script.
* **Port already in use** → Another background process or application instance is currently binding to network port 5002. Terminate conflicting processes and restart the application.

```

```
