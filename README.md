# Web Crawling Project for Python Developer

A project for crawling, monitoring, and serving data from a sample e-commerce website

## Tech Stack/ Tools

- **Framework**: FastAPI 
- **Backend**: Python 3.12.0
- **Server**: Uvicorn
- **Database**: MongoDB
- **Validation**: Pydantic
- **Scheduling**: APScheduler
- **Rate Limiting**: SlowAPI
- **Monitoring**: Sentry SDK

## Setup Instructions

1. **Clone the repository**
```bash
   git clone https://github.com/ISLOWIsmaeli/ceanapse-donation-platform.git
   cd ceanapse-donation-platform
```

2. **Create and activate the virtual environment**
```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Mac/Linux
   python3 -m venv venv
   source venv/bin/activate
```

3. **Install dependencies**
```bash
   pip install -r requirements.txt
```

4. **Setup Database**
  - Log in or setup an acccount on MongoDB Cloud
  - After setting up your database copy your connection string
  - Create a `.env` file in the root folder
  - Add the connection string as shown below (replace the current string with yours)
```bash
   # in .env file
   MONGO_URI = "mongodb+srv://<username>:<password>@<clusterName>.<randomID>.mongodb.net/<databaseName>?retryWrites=true&w=majority
"
```
## Running Instructions

1. Navigate to the project root directory and copy the command below to start crawling and scraping to your MongoDB database
```bash
   python -m crawler.crawler
```
2. After crawling is finished, navigate to the root folder and use the command below to run the api
```bash
   fastapi dev main.py
```
3. Navigate to:
```bash
   http://127.0.0.1:8000/docs#/
```
to access the swagger UI with all the endpoints

4. Use the `/GET/books` to get all the books in the database by setting the output limits

5. Use the `/GET/books/{book_id}` to get a book by the ID stored in the database

6. Go back to the project terminal, press `Ctrl+C` to stop the server then run the following command to start the scheduler
```bash
   python scheduler/run_scheduler.py
```
The scheduler generates the following reports as a result:
  * A `.json` file containing all the changes made/found
  * A `.log` file containing all the logs

7. Wait for the scheduler to finish running and run the api once again as in step 2 and 3 then navigate to the `/GET/changes` endpoint

6. Use the `/GET/changes` to view the changes by adjusting the limits

## Api endpoints
The following is a list of all my current API endpoints:
* /GET/books
* /GET/books/{book_id}
* /GET/changes

## Feature section 
Below are some of the sample screenshots that demonstrate the working of some of the parts of the project:
1. Samples of the `books` schema

2. The `snapshots` schema

3. The `changelogs` schema

4. Running a successful crawl in the terminal

5. Running a successful schedule in the terminal

6. A sample generated `scraper.log` file

7. A sample generated `daily_change_report_2025_11_12.json` file

8. A sample generated `scraper.log` file

9. A sample of the Swagger UI documentation when navigating to `http://127.0.0.1:8000/docs#/`

10. A sample of getting all the books endpoint `/GET/books`

11. A sample of getting a book by id `/GET/books/{book_id}`

12. A sample of looking at all the changes detected `/GET/changes`

## Limitations  
Despite the progress that I have made my final submission is limited in the following areas, which I purpose to implement even post submission date:
* Does not currently contain tests
* Does not contain API Key implementation
* Has not added rate limitations

