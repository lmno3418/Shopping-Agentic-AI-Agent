import base64
import json
import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from reviews_api import get_product_rating
from store_db import create_order, get_product_name_and_price, search_products as query_products


load_dotenv()

googlegeminiapikey = os.getenv("googlegeminiapikey")
visionmodel = os.getenv("visionmodel")


@tool
def search_products(query: str, max_price: float | None = None, is_organic: bool | None = None) -> str:
    """
    Search the product database by keyword (matched against name, description, and category).
    Optionally filter by maximum price and/or organic status.
    Returns a JSON array of matching products, each with: id, name, category, price,
    description, is_organic.
    """
    return json.dumps(query_products(query=query, max_price=max_price, is_organic=is_organic))


@tool
def get_rating(product_id: int) -> str:
    """
    Get the average customer rating and total review count for a product by its ID.
    Returns a JSON object with: product_id, average_rating, review_count.
    """
    result = get_product_rating(product_id)
    return json.dumps(result)


@tool
def checkout(product_id: int) -> str:
    """
    Place an order for the given product ID. Saves the order to the database and returns
    a confirmation message with the order ID, product name, and price.
    """
    order_id = create_order(product_id)
    if order_id is None:
        return f"Error: product with ID {product_id} not found."

    product = get_product_name_and_price(product_id)
    if product is None:
        return f"Error: product with ID {product_id} not found."

    name, price = product
    return (
        f"Order #{order_id} confirmed! '{name}' has been successfully ordered for ${price:.2f}. "
        f"Your order will arrive in 3-5 business days. Thank you for shopping with us!"
    )


@tool
def describe_product_image(image_path: str) -> str:
    """
    Analyze a product image and return its key attributes as a JSON object.
    Use this when the user uploads a photo of a product they are interested in.
    The returned attributes can be used directly with search_products.
    """
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode()

    ext = os.path.splitext(image_path)[1].lower().lstrip(".")
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"

    message = HumanMessage(content=[
        {
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{image_data}"},
        },
        {
            "type": "text",
            "text": (
                "Look at this product image and extract its key attributes. "
                "Return ONLY a JSON object with these fields:\n"
                "- product_type: what kind of product it is (e.g. honey, olive oil, almonds)\n"
                "- search_query: a short keyword to search for it (e.g. 'honey', 'olive oil')\n"
                "- is_organic: true if the label says organic, false if not, null if unclear\n"
                "- description: one sentence describing the product"
            ),
        },
    ])

    from langchain_google_genai import ChatGoogleGenerativeAI

    vision_llm = ChatGoogleGenerativeAI(
        model=visionmodel,
        temperature=0,
        google_api_key=googlegeminiapikey,
    )

    response = vision_llm.invoke([message])
    return response.content