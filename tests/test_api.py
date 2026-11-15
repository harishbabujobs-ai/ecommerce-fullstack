from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.product import Product
from tests.conftest import auth, login, make_admin, register_user


def create_category(client: TestClient, token: str, name: str = "Books") -> int:
    response = client.post("/api/v1/categories", json={"name": name}, headers=auth(token))
    assert response.status_code == 201
    return response.json()["id"]


def create_product(client: TestClient, token: str, category_id: int, inventory: int = 5) -> dict:
    response = client.post(
        "/api/v1/products",
        json={
            "name": "Backend Basics",
            "description": "A test product",
            "price": "10.00",
            "inventory": inventory,
            "category_id": category_id,
        },
        headers=auth(token),
    )
    assert response.status_code == 201
    return response.json()


def admin_token(client: TestClient, db_session: Session) -> str:
    register_user(client)
    make_admin(db_session)
    return login(client)


def test_registration_login_and_protected_profile(client: TestClient) -> None:
    user = register_user(client)
    assert user["role"] == "customer"
    assert client.get("/api/v1/users/me").status_code == 401
    token = login(client)
    response = client.get("/api/v1/users/me", headers=auth(token))
    assert response.status_code == 200
    assert response.json()["email"] == "customer@example.com"


def test_product_crud_search_and_admin_permissions(
    client: TestClient, db_session: Session
) -> None:
    token = admin_token(client, db_session)
    category_id = create_category(client, token)
    product = create_product(client, token, category_id)
    product_id = product["id"]

    listing = client.get("/api/v1/products?search=Basics&min_price=5&max_price=15")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert client.get(f"/api/v1/products/{product_id}").status_code == 200

    updated = client.put(
        f"/api/v1/products/{product_id}",
        json={"price": "12.50"},
        headers=auth(token),
    )
    assert updated.status_code == 200
    assert updated.json()["price"] == "12.50"

    stock = client.patch(
        f"/api/v1/products/{product_id}/inventory",
        json={"inventory": 8},
        headers=auth(token),
    )
    assert stock.json()["inventory"] == 8
    assert client.delete(f"/api/v1/products/{product_id}", headers=auth(token)).status_code == 204
    assert client.get(f"/api/v1/products/{product_id}").status_code == 404


def test_category_crud_and_protected_deletion(client: TestClient, db_session: Session) -> None:
    token = admin_token(client, db_session)
    category_id = create_category(client, token)
    assert client.get("/api/v1/categories").json()[0]["id"] == category_id
    updated = client.put(
        f"/api/v1/categories/{category_id}",
        json={"name": "Reading", "description": "Printed material"},
        headers=auth(token),
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Reading"

    product = create_product(client, token, category_id)
    conflict = client.delete(f"/api/v1/categories/{category_id}", headers=auth(token))
    assert conflict.status_code == 409
    assert client.delete(
        f"/api/v1/products/{product['id']}", headers=auth(token)
    ).status_code == 204

    empty_category = create_category(client, token, "Empty")
    assert client.delete(
        f"/api/v1/categories/{empty_category}", headers=auth(token)
    ).status_code == 204


def test_cart_quantity_totals_checkout_and_order_history(
    client: TestClient, db_session: Session
) -> None:
    admin = admin_token(client, db_session)
    category_id = create_category(client, admin)
    product = create_product(client, admin, category_id)
    customer = login(client)
    headers = auth(customer)

    first = client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 2},
        headers=headers,
    )
    item_id = first.json()["items"][0]["id"]
    duplicate = client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers=headers,
    )
    assert duplicate.json()["items"][0]["quantity"] == 3
    assert duplicate.json()["subtotal"] == "30.00"
    assert duplicate.json()["tax"] == "2.40"
    assert duplicate.json()["shipping"] == "5.00"

    updated = client.patch(
        f"/api/v1/cart/items/{item_id}", json={"quantity": 2}, headers=headers
    )
    assert updated.json()["items"][0]["quantity"] == 2
    order_response = client.post("/api/v1/orders/checkout", headers=headers)
    assert order_response.status_code == 201
    order = order_response.json()
    assert order["status"] == "paid"
    assert order["items"][0]["product_name"] == "Backend Basics"
    assert order["items"][0]["unit_price"] == "10.00"
    assert client.get("/api/v1/cart", headers=headers).json()["items"] == []
    assert client.get("/api/v1/orders", headers=headers).json()[0]["id"] == order["id"]
    assert client.get(f"/api/v1/orders/{order['id']}", headers=headers).status_code == 200
    shipped = client.patch(
        f"/api/v1/orders/{order['id']}/status",
        json={"status": "shipped"},
        headers=auth(admin),
    )
    assert shipped.status_code == 200
    assert shipped.json()["status"] == "shipped"

    other_user = register_user(client, "another@example.com")
    other_token = login(client, "another@example.com")
    assert client.get(
        f"/api/v1/orders/{order['id']}", headers=auth(other_token)
    ).status_code == 404
    assert other_user["id"] != order["id"]


def test_insufficient_inventory_rolls_back_checkout(
    client: TestClient, db_session: Session
) -> None:
    admin = admin_token(client, db_session)
    category_id = create_category(client, admin)
    product = create_product(client, admin, category_id, inventory=3)
    customer = auth(login(client))
    client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 3},
        headers=customer,
    )
    db_product = db_session.get(Product, product["id"])
    assert db_product is not None
    db_product.inventory = 2
    db_session.commit()

    failed = client.post("/api/v1/orders/checkout", headers=customer)
    assert failed.status_code == 409
    assert client.get("/api/v1/cart", headers=customer).json()["items"][0]["quantity"] == 3
    assert db_session.scalar(select(Order.id)) is None
    assert db_session.get(Product, product["id"]).inventory == 2


def test_cart_removal_validation_and_role_protection(
    client: TestClient, db_session: Session
) -> None:
    user = register_user(client)
    token = login(client)
    assert client.post("/api/v1/cart/items", json={"product_id": 1, "quantity": 1}).status_code == 401
    register_user(client, "admin@example.com")
    make_admin(db_session, "admin@example.com")
    admin = login(client, "admin@example.com")
    category_id = create_category(client, admin)
    product = create_product(client, admin, category_id)
    invalid = client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 0},
        headers=auth(token),
    )
    assert invalid.status_code == 422

    added = client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers=auth(token),
    )
    item_id = added.json()["items"][0]["id"]
    removed = client.delete(f"/api/v1/cart/items/{item_id}", headers=auth(token))
    assert removed.status_code == 200
    assert removed.json()["items"] == []
    assert client.delete("/api/v1/cart", headers=auth(token)).json()["items"] == []

    customer_headers = auth(token)
    forbidden = client.post(
        "/api/v1/categories",
        json={"name": "Unauthorized Category"},
        headers=customer_headers,
    )
    assert forbidden.status_code == 403
    assert user["role"] == "customer"


def test_profile_update_and_deactivation(client: TestClient) -> None:
    register_user(client)
    token = login(client)
    updated = client.put(
        "/api/v1/users/me",
        json={"full_name": "Updated Name", "email": "updated@example.com"},
        headers=auth(token),
    )
    assert updated.status_code == 200
    assert updated.json()["email"] == "updated@example.com"
    assert client.delete("/api/v1/users/me", headers=auth(token)).status_code == 204
    assert client.get("/api/v1/users/me", headers=auth(token)).status_code == 401