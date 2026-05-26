from flask import Flask, jsonify, request
from flask_cors import CORS
from database import init_db, get_prices, get_price_history
from scraper import scrape_all

app = Flask(__name__)
CORS(app)
init_db()


@app.route("/")
def home():
    return jsonify({
        "status":  "CrossCart Backend Running ✅",
        "version": "1.0",
        "routes": [
            "GET /search?q=product  — live price comparison",
            "GET /cached?q=product  — results from database",
            "GET /history?q=product — price history",
            "GET /best?q=product    — cheapest result only"
        ]
    })


@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Example: /search?q=iphone"}), 400
    if len(query) < 2:
        return jsonify({"error": "Query too short"}), 400

    results = scrape_all(query)

    if not results:
        return jsonify({
            "query": query, "count": 0,
            "results": [], "best": None,
            "message": "No results found."
        })

    best   = results[0]
    by_app = {}
    for r in results:
        by_app.setdefault(r["app"], []).append(r)

    return jsonify({
        "query":   query,
        "count":   len(results),
        "best":    best,
        "by_app":  by_app,
        "results": results
    })


@app.route("/cached")
def cached():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Provide search query"}), 400
    rows    = get_prices(query)
    results = [{"app": r[0], "price": r[1], "url": r[2]} for r in rows]
    return jsonify({"query": query, "count": len(results), "results": results})


@app.route("/history")
def history():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Provide product name"}), 400
    rows = get_price_history(query)
    data = [{"app": r[0], "price": r[1], "timestamp": r[2]} for r in rows]
    return jsonify({"query": query, "count": len(data), "history": data})


@app.route("/best")
def best_price():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Provide search query"}), 400
    results = scrape_all(query)
    if not results:
        return jsonify({"query": query, "best": None})
    best = results[0]
    return jsonify({
        "query": query,
        "best":  best,
        "message": f"Cheapest: {best['price']} on {best['app']}"
    })


if __name__ == "__main__":
    print("\nCrossCart Backend Starting...")
    print("Open: http://localhost:5000")
    print("Test: http://localhost:5000/search?q=samsung+s24\n")
    app.run(debug=True, port=5000)
    from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# This serves your HTML file
@app.route('/')
def home():
    return send_file('crosscart_enhanced.html')

@app.route('/search')
def search():
    # your existing search code...

 @app.route('/history')
 def history():
    # your existing history code...

  if __name__ == '__main__':
    app.run(debug=True)