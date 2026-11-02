import pytest
from httpx import AsyncClient


# ─── Categories ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_category(client: AsyncClient):
    response = await client.post("/api/v1/categories", json={
        "name": "Electrónica",
        "description": "Productos electrónicos"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Electrónica"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_get_categories_empty(client: AsyncClient):
    response = await client.get("/api/v1/categories")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_categories_with_data(client: AsyncClient, test_category):
    response = await client.get("/api/v1/categories")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Test Category"


# ─── Products ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_product(client: AsyncClient, test_category):
    response = await client.post("/api/v1/products", json={
        "name": "MacBook Pro",
        "description": "Laptop de alto rendimiento",
        "price": 2499.99,
        "stock": 10,
        "category_id": test_category.id,
        "image_url": "https://example.com/macbook.jpg"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "MacBook Pro"
    assert data["price"] == "2499.99"
    assert data["stock"] == 10
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_get_products_empty(client: AsyncClient):
    response = await client.get("/api/v1/products")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_get_products_with_data(client: AsyncClient, test_product):
    response = await client.get("/api/v1/products")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Test Product"


@pytest.mark.asyncio
async def test_get_product_by_id(client: AsyncClient, test_product):
    response = await client.get(f"/api/v1/products/{test_product.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_product.id
    assert data["name"] == "Test Product"


@pytest.mark.asyncio
async def test_get_product_not_found(client: AsyncClient):
    response = await client.get("/api/v1/products/non-existent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_product(client: AsyncClient, test_product):
    response = await client.put(f"/api/v1/products/{test_product.id}", json={
        "name": "Updated Product",
        "price": 149.99,
        "stock": 20
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Product"
    assert data["price"] == "149.99"
    assert data["stock"] == 20


@pytest.mark.asyncio
async def test_delete_product(client: AsyncClient, test_product):
    response = await client.delete(f"/api/v1/products/{test_product.id}")
    assert response.status_code == 204

    
    response = await client.get("/api/v1/products")
    data = response.json()
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_get_products_pagination(client: AsyncClient, test_category):
   
    for i in range(5):
        await client.post("/api/v1/products", json={
            "name": f"Product {i}",
            "description": f"Description {i}",
            "price": 99.99,
            "stock": 10,
            "category_id": test_category.id,
        })

    response = await client.get("/api/v1/products?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5


@pytest.mark.asyncio
async def test_get_products_search(client: AsyncClient, test_category):
    await client.post("/api/v1/products", json={
        "name": "iPhone 15",
        "description": "Smartphone Apple",
        "price": 999.99,
        "stock": 5,
        "category_id": test_category.id,
    })
    await client.post("/api/v1/products", json={
        "name": "Samsung Galaxy",
        "description": "Smartphone Samsung",
        "price": 799.99,
        "stock": 5,
        "category_id": test_category.id,
    })

    response = await client.get("/api/v1/products?search=iPhone")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "iPhone 15"


# ─── Availability & Inventory ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_products_filter_by_availability(client: AsyncClient, test_category):
    # Create in-stock product
    await client.post("/api/v1/products", json={
        "name": "In Stock Item",
        "description": "Has stock",
        "price": 25.00,
        "stock": 10,
        "category_id": test_category.id,
    })
    # Create out-of-stock product
    await client.post("/api/v1/products", json={
        "name": "Out of Stock Item",
        "description": "Zero stock",
        "price": 30.00,
        "stock": 0,
        "category_id": test_category.id,
    })

    # All products
    response_all = await client.get("/api/v1/products")
    assert response_all.status_code == 200
    assert response_all.json()["total"] == 2

    # Filtered by availability
    response_avail = await client.get("/api/v1/products?available_only=true")
    assert response_avail.status_code == 200
    avail_data = response_avail.json()
    assert avail_data["total"] == 1
    assert avail_data["items"][0]["name"] == "In Stock Item"
    assert avail_data["items"][0]["is_available"] is True


@pytest.mark.asyncio
async def test_check_product_inventory_available(client: AsyncClient, test_product):
    response = await client.get(f"/api/v1/products/{test_product.id}/availability?quantity=5")
    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == test_product.id
    assert data["requested_quantity"] == 5
    assert data["available_stock"] == 10
    assert data["is_available"] is True


@pytest.mark.asyncio
async def test_check_product_inventory_insufficient(client: AsyncClient, test_product):
    response = await client.get(f"/api/v1/products/{test_product.id}/availability?quantity=50")
    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == test_product.id
    assert data["requested_quantity"] == 50
    assert data["available_stock"] == 10
    assert data["is_available"] is False


@pytest.mark.asyncio
async def test_check_product_inventory_not_found(client: AsyncClient):
    response = await client.get("/api/v1/products/non-existent-product/availability?quantity=1")
    assert response.status_code == 404