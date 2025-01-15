import json
import logging
from pathlib import Path

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from flask import Flask, jsonify, render_template, request, url_for

app = Flask(__name__)
limiter = Limiter(app=app, key_func=get_remote_address)
log_path = Path("logs") / "app.log"

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename=log_path,
                    filemode='a')


logger = logging.getLogger(__name__)




class Books:

    def __init__(self, books_file = "books.json"):
        self.BOOKS = books_file
        self.books = self.open_books()
        logger.info("New Books instance started %s", self.BOOKS)


    def open_books(self):
        """open persistent storage and store local"""
        try:
            with open(self.BOOKS, "r") as read_handle:
                books = json.load(read_handle)
                if books:
                    logger.info("persistent storage read into instance")
                    return books
        except FileNotFoundError as e:
            logger.error("Error reading persistent storage into instance")
            print("error occurred opening the json storage file", e)

    def write_books(self):
        """ write local books to persistent storage"""
        try:
            with open(self.BOOKS, "w") as write_handle:
                json.dump(self.books,write_handle, indent =4)
                logger.info("local storage written into persistent storage %s", self.BOOKS)
        except FileNotFoundError as e:
            logger.error("error occurred opening the json storage file", e)

    def find_book_by_id(self,id):
        """ find book and return based on its id """
        book =next((book for book in self.books if book["id"] == id), None)
        logger.info("Book found: %s",book)
        return book

    def get_books(self):
        """return all books"""
        logger.info("Listing books in instance storage")
        return jsonify(self.books)

    def add_books(self,new_book):
        """add new book to local storage"""
        if b.validate_book_data(new_book):
            new_book_id = self.new_book_id()
            new_book['id'] = new_book_id
            self.books.append(new_book)
            self.write_books()
            logger.info("Book added to persistent storage %s", self.BOOKS)
            return True


    def validate_book_data(self, book):
        """validation of book data"""
        return True if "title" in book and "author" in book else False

    def new_book_id(self):
        return  max(book['id'] for book in self.books) + 1 if self.books else 1

    def delete_book(self,id):
        """delete book based on valid id"""
        book = b.find_book_by_id(id)
        if book:
            self.books.remove(book)
            self.write_books()
            logger.info("Book removed from persistent storage %s %s", book, self.BOOKS)
            return jsonify({"book deleted": book['title']}), 200
        else:
            logger.warning("Book not found %s", book)
            return jsonify({"error": "Book not found"}), 405


    def books_by_author(self, author):
        return jsonify([book for book in self.books
                        if book["author"] == author])


b= Books()
@app.route("/")
def home():
    """teapot message"""
    return "I am a teapot", 418

@app.route('/api/books', methods=['GET', 'POST'])
@limiter.limit("10/minute")
def handle_books():
    """ return books or add new book depending on request method used"""
    if request.method == "GET":
        author = request.args.get("author")
        if author:
            logger.info("Returning books by author %s", author)
            return b.books_by_author(author)
        else:
            logger.info("Returning all books")
            return b.get_books()
    elif request.method == "POST":
        new_book = request.get_json()
        if b.add_books(new_book):
            logger.info("New book added to persistent storage %s %s", new_book, self.BOOKS)
            return jsonify({"book added": new_book['title']}),  201
        else:
            logger.warning("Invalid book data %s", new_book)
            return jsonify({"error": "Invalid book data"}), 400

@app.route("/api/books/<int:id>", methods = ["PUT"])
def handle_book(id):
    """update book based on its id"""
    book = b.find_book_by_id(id)
    if not book:
        return jsonify({"Book not found": "Method Not Allowed"}), 404
    else:
        new_book_data = request.get_json()
        book.update(new_book_data)
        b.write_books()
        return jsonify(book), 200

@app.route("/api/books/delete/<int:id>", methods = ["DELETE"])
def delete_book(id):
    """delete book based on its id"""
    response = b.delete_book(id)
    return response

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Not Found"}), 404


@app.errorhandler(405)
def method_not_allowed_error(error):
    return jsonify({"error": "Method Not Allowed"}), 405


if __name__ == '__main__':

    app.run(host="0.0.0.0", port=5000, debug=True)
