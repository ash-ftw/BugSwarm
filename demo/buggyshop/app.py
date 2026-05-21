from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HOST = "0.0.0.0"
PORT = 8090


def page(title: str, body: str, extra_head: str = "") -> bytes:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title} | BuggyShop</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f5f7f8;
      color: #172026;
    }}
    body {{ margin: 0; }}
    header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
      min-height: 68px;
      padding: 0 28px;
      background: #12343b;
      color: #fff;
    }}
    header a {{ color: #e9fbf4; text-decoration: none; font-weight: 700; }}
    nav {{ display: flex; gap: 16px; flex-wrap: wrap; }}
    main {{ width: min(1040px, calc(100% - 36px)); margin: 28px auto 48px; }}
    .hero, .panel, .product {{
      border: 1px solid #d9e1e5;
      border-radius: 8px;
      background: #fff;
      box-shadow: 0 8px 24px rgba(18, 52, 59, 0.08);
    }}
    .hero {{ padding: 28px; }}
    .hero h1 {{ margin: 0 0 10px; font-size: 36px; }}
    .hero p {{ max-width: 660px; color: #56656f; line-height: 1.6; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-top: 18px; }}
    .product, .panel {{ padding: 18px; }}
    .product h3 {{ margin-top: 0; }}
    .price {{ display: block; margin: 12px 0; color: #0a6847; font-weight: 800; }}
    .button, button {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 40px;
      padding: 0 14px;
      border: 0;
      border-radius: 8px;
      background: #0a6847;
      color: #fff;
      font: inherit;
      font-weight: 800;
      text-decoration: none;
      cursor: pointer;
    }}
    .secondary {{ background: #365a67; }}
    label {{ display: grid; gap: 8px; margin-bottom: 12px; color: #43525c; font-weight: 700; }}
    input {{ min-height: 40px; padding: 0 10px; border: 1px solid #c8d3d9; border-radius: 8px; font: inherit; }}
    .message {{ margin-top: 14px; padding: 12px; border-radius: 8px; background: #e8f8ee; color: #0a6847; font-weight: 700; }}
    .spinner {{ width: 52px; height: 52px; border: 7px solid #d9e1e5; border-top-color: #0a6847; border-radius: 50%; animation: spin 0.7s linear infinite; }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    @media (max-width: 640px) {{
      .grid {{ grid-template-columns: 1fr; }}
      header {{ min-height: 54px; padding: 0 10px; }}
      nav {{ gap: 4px; }}
      nav a {{ margin-left: -18px; padding: 10px 6px; background: rgba(255,255,255,0.12); }}
      .product {{ height: 118px; overflow: hidden; }}
      .product .button {{ position: relative; top: -34px; left: 48%; }}
    }}
  </style>
  {extra_head}
</head>
<body>
  <header>
    <a href="/">BuggyShop</a>
    <nav>
      <a href="/products">Products</a>
      <a href="/search">Search</a>
      <a href="/cart">Cart</a>
      <a href="/orders">Orders</a>
      <a href="/login">Login</a>
    </nav>
  </header>
  <main>{body}</main>
</body>
</html>""".encode("utf-8")


class BuggyShopHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        routes = {
            "/": self.home,
            "/login": self.login,
            "/register": self.register,
            "/products": self.products,
            "/products/widget": self.product_detail,
            "/search": self.search,
            "/cart": self.cart,
            "/orders": self.orders,
        }
        if parsed.path == "/checkout" and parse_qs(parsed.query).get("empty") == ["1"]:
            self.respond(HTTPStatus.INTERNAL_SERVER_ERROR, b"Checkout crashed while loading an empty cart.")
            return
        handler = routes.get(parsed.path)
        if handler is None:
            self.respond(HTTPStatus.NOT_FOUND, b"Product or page was not found.")
            return
        self.respond(HTTPStatus.OK, handler())

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/login":
            self.respond(HTTPStatus.OK, self.login(success="Logged in successfully with unvalidated credentials."))
            return
        if parsed.path == "/register":
            self.respond(HTTPStatus.OK, self.register(success="Account created even though the email was invalid."))
            return
        self.respond(HTTPStatus.NOT_FOUND, b"Unknown form endpoint.")

    def home(self) -> bytes:
        return page(
            "Home",
            """
            <section class="hero">
              <h1>Demo storefront with intentional defects</h1>
              <p>BuggyShop is a contained target application for BugSwarm demos. It includes broken links, console errors, bad form validation, a checkout crash, and a loading state that never resolves.</p>
              <a class="button" href="/products">Browse products</a>
            </section>
            <section class="grid">
              <article class="product"><h3>QA Hoodie</h3><span class="price">$49</span><a class="button" href="/products/widget">View</a></article>
              <article class="product"><h3>Broken Sneaker</h3><span class="price">$89</span><a class="button" href="/products/missing-sku">View</a></article>
              <article class="product"><h3>Test Mug</h3><span class="price">$14</span><a class="button" href="/cart">Add to cart</a></article>
            </section>
            """,
        )

    def login(self, success: str | None = None) -> bytes:
        message = f'<p class="message">{success}</p>' if success else ""
        return page(
            "Login",
            f"""
            <section class="panel">
              <h1>Login</h1>
              <form method="post" action="/login">
                <label>Email <input name="email" value="not-an-email" /></label>
                <label>Password <input name="password" type="password" value="" /></label>
                <button type="submit">Login</button>
              </form>
              {message}
              <p><a href="/register">Create account</a></p>
            </section>
            """,
        )

    def register(self, success: str | None = None) -> bytes:
        message = f'<p class="message">{success}</p>' if success else ""
        return page(
            "Register",
            f"""
            <section class="panel">
              <h1>Register</h1>
              <form method="post" action="/register">
                <label>Name <input name="name" value="Demo Tester" /></label>
                <label>Email <input name="email" value="bad-email-value" /></label>
                <label>Password <input name="password" type="password" value="short" /></label>
                <button type="submit">Create account</button>
              </form>
              {message}
            </section>
            """,
        )

    def products(self) -> bytes:
        return page(
            "Products",
            """
            <section class="panel">
              <h1>Products</h1>
              <p>The product list intentionally emits a console error for BugSwarm to capture.</p>
            </section>
            <section class="grid">
              <article class="product"><h3>QA Hoodie</h3><span class="price">$49</span><a class="button" href="/products/widget">View details</a></article>
              <article class="product"><h3>Ghost Product</h3><span class="price">$999</span><a class="button" href="/products/ghost">View details</a></article>
              <article class="product"><h3>Cart Crash Repro</h3><span class="price">$0</span><a class="button" href="/checkout?empty=1">Checkout empty cart</a></article>
            </section>
            """,
            '<script>console.error("Inventory widget failed to hydrate: missing product payload");</script>',
        )

    def product_detail(self) -> bytes:
        return page(
            "QA Hoodie",
            """
            <section class="panel">
              <h1>QA Hoodie</h1>
              <p>This detail page has a mobile layout overlap by design.</p>
              <a class="button" href="/cart">Add to cart</a>
            </section>
            """,
        )

    def search(self) -> bytes:
        return page(
            "Search",
            """
            <section class="panel">
              <h1>Search</h1>
              <label>Search products <input id="search-box" name="q" value="hoodie" /></label>
              <button id="search-button" type="button">Search</button>
              <p id="search-result">No search has run yet.</p>
            </section>
            <script>
              document.querySelector("#search-button").addEventListener("click", function () {
                // Intentional no-op bug: the visible result never changes.
              });
            </script>
            """,
        )

    def cart(self) -> bytes:
        return page(
            "Cart",
            """
            <section class="panel">
              <h1>Cart</h1>
              <p>Your cart is empty.</p>
              <a class="button" href="/checkout?empty=1">Checkout anyway</a>
            </section>
            """,
        )

    def orders(self) -> bytes:
        return page(
            "Orders",
            """
            <section class="panel">
              <h1>Order history</h1>
              <p>Loading your orders...</p>
              <div class="spinner" role="status" aria-label="Loading"></div>
            </section>
            <script>
              window.__ordersNeverResolve = true;
            </script>
            """,
        )

    def respond(self, status_code: HTTPStatus, body: bytes) -> None:
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), BuggyShopHandler)
    print(f"BuggyShop demo target listening on http://{HOST}:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
