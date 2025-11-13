import httpx
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import datetime
import json
import time
import re
import hashlib
import logging
from pydantic import ValidationError
from typing import List, Dict
from model.book_details import Book
from model.logger import ChangeLogEntry
from db.connector import DbConnector


class BookScraper:
    def __init__(self, base_url: str, max_concurrent: int = 10):
        self.base_url = base_url
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.books_collection = None
        self.snapshots_collection = None
        self.changelog_collection = None
        self.mongo_client = None

        self.change_report_entries = []

    async def connect_to_db(self):
        """Connects to MongoDB and sets up collection handles."""
        db_connector = DbConnector()
        await db_connector.connect_to_db()
        self.books_collection = db_connector.books_collection
        self.snapshots_collection = db_connector.snapshots_collection
        self.changelog_collection = db_connector.changelog_collection
        self.mongo_client = db_connector.mongo_client
        logging.info(f"✅ Connected to MongoDB. DB: {db_connector.db.name}")

    def _calculate_hash(self, html_bytes: bytes) -> str:
        if not html_bytes:
            return None
        return hashlib.md5(html_bytes).hexdigest()

    async def _log_change(self, url: str, status: str, changes_list: List = []):
        try:
            entry = ChangeLogEntry(source_url=url, status=status, changes=changes_list)
            entry_dict = entry.model_dump()
            entry_dict["source_url"] = str(
                entry_dict["source_url"]
            )  # Convert HttpUrl for Mongo

            await self.changelog_collection.insert_one(entry_dict)

            self.change_report_entries.append(entry_dict)

            if status == "NEW":
                logging.warning(f"🔔 NEW BOOK: Found new book at {url}")
            elif status == "UPDATED":
                logging.warning(
                    f"🔔 BOOK UPDATED: Found changes at {url} - {changes_list}"
                )

        except Exception as e:
            logging.error(f"❌ Failed to log change for {url}: {e}")

    def _compare_book_data(self, old_book: Dict, new_book: Book) -> List[Dict]:
        changes = []
        new_details = new_book.book_details
        old_details = old_book.get("book_details", {})

        fields_to_check = ["price_excl_tax", "price_incl_tax", "availability"]

        for field in fields_to_check:
            old_val = old_details.get(field)
            new_val = getattr(new_details, field)

            if old_val != new_val:
                changes.append({"field": field, "old": old_val, "new": new_val})
        return changes

    async def fetch_page(self, client, url):
        try:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            logging.info(f"✅ Fetched: {url}")
            return response.content, "OK"
        except httpx.RequestError as e:
            logging.error(f"❌ FAILED to fetch {url}: {e}")
            return None, str(e)

    def parse_book_page(self, html_content, book_url, status):
        book_data_dict = {
            "metadata": {
                "crawl_timestamp": datetime.datetime.now(datetime.timezone.utc),
                "status": status,
                "source_url": book_url,
            },
            "book_details": {},
        }
        if status != "OK" or not html_content:
            pass
        else:
            try:
                soup = BeautifulSoup(html_content, "html.parser", from_encoding="utf-8")
                article = soup.find("article", class_="product_page")
                try:
                    book_data_dict["book_details"]["name"] = article.find(
                        "h1"
                    ).text.strip()
                except Exception:
                    book_data_dict["book_details"]["name"] = None
                try:
                    desc_header = article.find("div", id="product_description")
                    book_data_dict["book_details"]["description"] = (
                        desc_header.find_next_sibling("p").text.strip()
                    )
                except Exception:
                    book_data_dict["book_details"]["description"] = None
                try:
                    book_data_dict["book_details"]["category"] = soup.select_one(
                        "ul.breadcrumb > li:nth-last-child(2) > a"
                    ).text.strip()
                except Exception:
                    book_data_dict["book_details"]["category"] = None
                product_table = article.find("table", class_="table-striped")
                table_data = {}
                for row in product_table.find_all("tr"):
                    key = row.find("th").text.strip()
                    value = row.find("td").text.strip()
                    table_data[key] = value
                raw_excl_tax = table_data.get("Price (excl. tax)")
                raw_incl_tax = table_data.get("Price (incl. tax)")
                if raw_excl_tax:
                    book_data_dict["book_details"]["price_excl_tax"] = re.sub(
                        r"[^0-9.]", "", raw_excl_tax
                    )
                else:
                    book_data_dict["book_details"]["price_excl_tax"] = None
                if raw_incl_tax:
                    book_data_dict["book_details"]["price_incl_tax"] = re.sub(
                        r"[^0-9.]", "", raw_incl_tax
                    )
                else:
                    book_data_dict["book_details"]["price_incl_tax"] = None
                book_data_dict["book_details"]["availability"] = table_data.get(
                    "Availability"
                )
                book_data_dict["book_details"]["num_reviews"] = table_data.get(
                    "Number of reviews"
                )
                try:
                    img_tag = article.find("div", class_="item active").find("img")
                    relative_img_url = img_tag["src"]
                    book_data_dict["book_details"]["image_url"] = urljoin(
                        self.base_url, relative_img_url
                    )
                except Exception:
                    book_data_dict["book_details"]["image_url"] = None
                try:
                    rating_p = article.find("p", class_="star-rating")
                    rating_class = rating_p["class"][-1]
                    book_data_dict["book_details"]["rating"] = (
                        f"{rating_class} out of Five"
                    )
                except Exception:
                    book_data_dict["book_details"]["rating"] = None
            except Exception as e:
                logging.error(f"❌ CRITICAL PARSE ERROR on {book_url}: {e}")
                book_data_dict["metadata"]["status"] = f"Parsing Failed: {e}"
        try:
            validated_book = Book(**book_data_dict)
            return validated_book
        except ValidationError as e:
            logging.error(f"❌ VALIDATION FAILED for {book_url}:\n{e}\n")
            return None

    async def save_book_to_db(self, book: Book):
        try:
            book_dict = book.model_dump()
            book_dict["metadata"]["source_url"] = str(
                book_dict["metadata"]["source_url"]
            )
            if book_dict["book_details"]["image_url"]:
                book_dict["book_details"]["image_url"] = str(
                    book_dict["book_details"]["image_url"]
                )
            filter_query = {"metadata.source_url": book_dict["metadata"]["source_url"]}
            update_query = {"$set": book_dict}
            await self.books_collection.update_one(
                filter_query, update_query, upsert=True
            )
            logging.info(f"📚 Saved BOOK: {book.book_details.name}")
        except Exception as e:
            logging.error(f"❌ FAILED to save BOOK {book.book_details.name}: {e}")

    async def save_snapshot_to_db(
        self, url: str, html_bytes: bytes, status: str, content_hash: str
    ):
        try:
            html_string = None
            if html_bytes:
                html_string = html_bytes.decode("utf-8", errors="ignore")

            snapshot_doc = {
                "source_url": str(url),
                "crawl_timestamp": datetime.datetime.now(datetime.timezone.utc),
                "status": status,
                "content_hash": content_hash,
                "html_content": html_string,
            }
            filter_query = {"source_url": str(url)}
            update_query = {"$set": snapshot_doc}
            await self.snapshots_collection.update_one(
                filter_query, update_query, upsert=True
            )
            logging.info(f"🗃️ Saved HTML for: {url}")
        except Exception as e:
            logging.error(f"❌ FAILED to save HTML for {url}: {e}")

    async def fetch_parse_and_save(self, client, book_url):
        async with self.semaphore:
            try:
                book_page_html_bytes, book_status = await self.fetch_page(
                    client, book_url
                )

                if book_status != "OK":
                    logging.error(
                        f"Skipping {book_url} due to fetch error: {book_status}"
                    )
                    return 0

                new_hash = self._calculate_hash(book_page_html_bytes)

                old_snapshot = await self.snapshots_collection.find_one(
                    {"source_url": str(book_url)}
                )

                old_hash = None
                if old_snapshot:
                    old_hash = old_snapshot.get("content_hash")

                if old_hash and old_hash == new_hash:
                    logging.info(f"✅ SKIPPED (unchanged): {book_url}")
                    return 0

                await self.save_snapshot_to_db(
                    book_url, book_page_html_bytes, book_status, new_hash
                )

                new_book_data = self.parse_book_page(
                    book_page_html_bytes, book_url, book_status
                )
                if not new_book_data:
                    logging.error(f"Parse failed for {book_url}, snapshot saved.")
                    return 0

                await self.save_book_to_db(new_book_data)

                if not old_hash:
                    await self._log_change(book_url, "NEW")
                    return 1
                else:
                    old_book_data = await self.books_collection.find_one(
                        {"metadata.source_url": str(book_url)}
                    )
                    changes = self._compare_book_data(old_book_data, new_book_data)

                    if changes:
                        await self._log_change(book_url, "UPDATED", changes)
                        return 2
                    else:
                        logging.info(f"HTML changed but no data changes for {book_url}")
                        return 0

            except Exception as e:
                logging.critical(
                    f"--- UNHANDLED EXCEPTION in fetch_parse_and_save for {book_url}: {e} ---"
                )
                return 0

    async def generate_daily_report(self):
        if not self.change_report_entries:
            logging.info("--- Daily Report: No changes detected. ---")
            return

        report_filename = f"daily_change_report_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')}.json"

        try:
            with open(report_filename, "w", encoding="utf-8") as f:
                json.dump(self.change_report_entries, f, indent=2, default=str)
            logging.info(
                f"--- Daily Report: Successfully generated {report_filename} with {len(self.change_report_entries)} changes. ---"
            )
        except Exception as e:
            logging.error(f"--- Failed to generate daily report: {e} ---")

    async def start_crawling(self):
        logging.info("--- 🚀 Starting new crawl run... ---")

        self.change_report_entries = []

        total_new_books = 0
        total_updated_books = 0

        async with httpx.AsyncClient() as client:
            current_absolute_page_url = urljoin(self.base_url, "catalogue/page-1.html")

            while current_absolute_page_url:
                list_page_html, status = await self.fetch_page(
                    client, current_absolute_page_url
                )
                if status != "OK":
                    logging.error(
                        f"Cannot fetch list page {current_absolute_page_url}, stopping crawl."
                    )
                    break

                soup = BeautifulSoup(list_page_html, "html.parser")
                book_links = soup.select("article.product_pod h3 a")
                logging.info(
                    f"Found {len(book_links)} books on page. Fetching all concurrently..."
                )

                tasks = []
                for link in book_links:
                    relative_book_url = link["href"]
                    absolute_book_url = urljoin(
                        current_absolute_page_url, relative_book_url
                    )
                    tasks.append(self.fetch_parse_and_save(client, absolute_book_url))

                scraped_book_results = await asyncio.gather(*tasks)

                total_new_books += scraped_book_results.count(1)
                total_updated_books += scraped_book_results.count(2)

                next_page_element = soup.select_one("li.next a")
                if next_page_element:
                    next_page_relative_href = next_page_element["href"]
                    current_absolute_page_url = urljoin(
                        current_absolute_page_url, next_page_relative_href
                    )
                    logging.info(f"➡️  Found next page: {current_absolute_page_url}")
                else:
                    logging.info("✅ No 'next' page link found. Crawl complete.")
                    current_absolute_page_url = None

        logging.info("--- 🌟 CRAWL FINISHED 🌟 ---")
        logging.warning(f"--- Summary: {total_new_books} NEW books found. ---")
        logging.warning(f"--- Summary: {total_updated_books} UPDATED books found. ---")

        await self.generate_daily_report()


def setup_logging():
    file_handler = logging.FileHandler("scraper.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[file_handler, console_handler],
    )

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


async def run_full_crawl():
    scraper = BookScraper(base_url="https://books.toscrape.com/")
    start_time = time.time()
    try:
        await scraper.connect_to_db()
        await scraper.start_crawling()
    except Exception as e:
        logging.critical(f"--- 🚨 A CRITICAL unhandled error occurred: {e} ---")
    finally:
        if scraper.mongo_client:
            scraper.mongo_client.close()
            logging.info("Disconnected from MongoDB.")

    end_time = time.time()
    logging.info(f"--- Run completed in {end_time - start_time:.2f} seconds ---")


def run_crawl_job():
    logging.info("--- Scheduler job starting... Running async crawl. ---")
    try:
        asyncio.run(run_full_crawl())
    except Exception as e:
        logging.critical(f"--- 🚨 A CRITICAL error occurred in asyncio.run: {e} ---")

if __name__ == "__main__":
    setup_logging()
    asyncio.run(run_full_crawl())