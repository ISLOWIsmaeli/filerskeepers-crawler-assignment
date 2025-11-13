from db.connector import DbConnector
from model.book_details import BookDetails
from bson import ObjectId

class BookSelector:
    def __init__(self):
        pass

    async def get_books(
        self,
        category: str,
        min_price: float,
        max_price: float,
        skip: int = 0,
        limit: int = 20,
    ):
        db_connector = DbConnector()
        await db_connector.connect_to_db()

        cursor = db_connector.books_collection.find().skip(skip).limit(limit)
        books = await cursor.to_list(limit)
        details = []

        for book in books:
            book_details = book.get("book_details", {})

            details.append(
                BookDetails(
                    name=book_details.get("name"),
                    description=book_details.get("description"),
                    price_excl_tax=book_details.get("price_excl_tax"),
                    price_incl_tax=book_details.get("price_incl_tax"),
                    availability=book_details.get("availability"),
                    category=book_details.get("category"),
                    rating=book_details.get("rating"),
                    num_reviews=book_details.get("num_reviews", 0),
                    image_url=book_details.get("image_url"),
                )
            )
        return details

    async def get_book_by_id(self, book_id: str):
        db_connector = DbConnector()
        await db_connector.connect_to_db()

        try:
            object_id = ObjectId(book_id)
        except Exception:
            return None

        book = await db_connector.books_collection.find_one({"_id": object_id})

        if not book:
            return None

        book_details = book.get("book_details", {})

        return BookDetails(
            name=book_details.get("name"),
            description=book_details.get("description"),
            price_excl_tax=book_details.get("price_excl_tax"),
            price_incl_tax=book_details.get("price_incl_tax"),
            availability=book_details.get("availability"),
            category=book_details.get("category"),
            rating=book_details.get("rating"),
            num_reviews=book_details.get("num_reviews", 0),
            image_url=book_details.get("image_url"),
        )

    async def get_recent_changes(self, skip: int = 0, limit: int = 20):
        db_connector = DbConnector()
        await db_connector.connect_to_db()

        try:
            cursor = (
                db_connector.changelog_collection.find()
                .sort("crawl_timestamp", -1)
                .skip(skip)
                .limit(limit)
            )
            changes = await cursor.to_list(limit)

            result = []
            for change in changes:
                change["_id"] = str(change.get("_id"))
                result.append(change)

            return result
        except Exception as e:
            print(f"❌ Error retrieving changes: {e}")
            return []
