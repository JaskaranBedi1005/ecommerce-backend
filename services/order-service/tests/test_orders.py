import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from decimal import Decimal


# ─── Crear orden ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_order(client: AsyncClient, mock_product):
    with patch(
        "app.commands.order_commands.OrderCommandHandler._validate_products",
        new_callable=AsyncMock
    ) as mock_validate:
        from app.schemas.order import ProductValidation
        mock_validate.return_value = {
            "product-123": ProductValidation(
                id="product-123",
                name="Test Product",
                price=Decimal("99.99"),
                stock=10,
                is_active=True
            )
        }

        response = await client.post("/api/v1/orders", json={
            "items": [{"product_id": "product-123", "quantity": 2}],
            "shipping_address": "Calle 123, Barranquilla",
            "notes": "Test order"
        })

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["shipping_address"] == "Calle 123, Barranquilla"
    assert data["total"] == "199.98"


@pytest.mark.asyncio
async def test_create_order_product_unavailable(client: AsyncClient):
    with patch(
        "app.commands.order_commands.OrderCommandHandler._validate_products",
        new_callable=AsyncMock
    ) as mock_validate:
        from fastapi import HTTPException
        mock_validate.side_effect = HTTPException(
            status_code=400,
            detail="Product product-999 not found"
        )

        response = await client.post("/api/v1/orders", json={
            "items": [{"product_id": "product-999", "quantity": 1}],
            "shipping_address": "Calle 123",
            "notes": ""
        })

    assert response.status_code == 400


# ─── Obtener órdenes ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_my_orders_empty(client: AsyncClient):
    response = await client.get(
        "/api/v1/orders/me",
        headers={"x-user-id": "user-123", "x-user-role": "user"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_get_my_orders_with_data(client: AsyncClient, test_order):
    response = await client.get(
        "/api/v1/orders/me",
        headers={"x-user-id": "dev-user-id", "x-user-role": "user"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_get_order_by_id(client: AsyncClient, test_order):
    response = await client.get(
        f"/api/v1/orders/{test_order['id']}",
        headers={"x-user-id": "dev-user-id", "x-user-role": "user"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_order["id"]


@pytest.mark.asyncio
async def test_get_order_not_found(client: AsyncClient):
    response = await client.get(
        "/api/v1/orders/non-existent-id",
        headers={"x-user-id": "dev-user-id", "x-user-role": "admin"}
    )
    assert response.status_code == 404


# ─── Admin endpoints ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_all_orders_admin(client: AsyncClient, test_order):
    response = await client.get(
        "/api/v1/orders",
        headers={"x-user-id": "admin-123", "x-user-role": "admin"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_get_all_orders_forbidden_for_user(client: AsyncClient):
    response = await client.get(
        "/api/v1/orders",
        headers={"x-user-id": "user-123", "x-user-role": "user"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_order_status(client: AsyncClient, test_order):
    response = await client.put(
        f"/api/v1/orders/{test_order['id']}/status",
        headers={"x-user-id": "admin-123", "x-user-role": "admin"},
        json={"status": "payment_pending", "notes": "Processing payment"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "payment_pending"


# ─── Cancelar orden ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cancel_order(client: AsyncClient, test_order):
    response = await client.post(
        f"/api/v1/orders/{test_order['id']}/cancel",
        headers={"x-user-id": "dev-user-id", "x-user-role": "user"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_order_wrong_user(client: AsyncClient, test_order):
    response = await client.post(
        f"/api/v1/orders/{test_order['id']}/cancel",
        headers={"x-user-id": "other-user-id", "x-user-role": "user"}
    )
    assert response.status_code == 403


# ─── Event Sourcing ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_order_history(client: AsyncClient, test_order):
    response = await client.get(
        f"/api/v1/orders/{test_order['id']}/history",
        headers={"x-user-id": "admin-123", "x-user-role": "admin"}
    )
    assert response.status_code == 200
    events = response.json()
    assert len(events) >= 1
    assert events[0]["event_type"] == "ORDER_CREATED"


# ─── Discount and Validation Tests ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_order_with_valid_discount(client: AsyncClient, mock_product):
    with patch(
        "app.commands.order_commands.OrderCommandHandler._validate_products",
        new_callable=AsyncMock
    ) as mock_validate:
        from app.schemas.order import ProductValidation
        mock_validate.return_value = {
            "product-123": ProductValidation(
                id="product-123",
                name="Test Product",
                price=Decimal("100.00"),
                stock=10,
                is_active=True
            )
        }

        response = await client.post("/api/v1/orders", json={
            "items": [{"product_id": "product-123", "quantity": 2}],
            "shipping_address": "Calle 45 # 10-20, Bogota",
            "notes": "Discount test",
            "discount_code": "SAVE10"
        })

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    # Subtotal 200.00 - 10% (20.00) = 180.00
    assert data["total"] == "180.00"


@pytest.mark.asyncio
async def test_create_order_with_invalid_discount(client: AsyncClient, mock_product):
    with patch(
        "app.commands.order_commands.OrderCommandHandler._validate_products",
        new_callable=AsyncMock
    ) as mock_validate:
        from app.schemas.order import ProductValidation
        mock_validate.return_value = {
            "product-123": ProductValidation(
                id="product-123",
                name="Test Product",
                price=Decimal("50.00"),
                stock=10,
                is_active=True
            )
        }

        response = await client.post("/api/v1/orders", json={
            "items": [{"product_id": "product-123", "quantity": 1}],
            "shipping_address": "Calle 45 # 10-20, Bogota",
            "discount_code": "NOTREAL"
        })

    assert response.status_code == 400
    assert "Invalid discount code" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_order_missing_shipping_address(client: AsyncClient):
    response = await client.post("/api/v1/orders", json={
        "items": [{"product_id": "product-123", "quantity": 1}],
        "shipping_address": "   ",
        "notes": ""
    })
    assert response.status_code == 400
    assert "Shipping address is required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_cancel_order_short_reason(client: AsyncClient, test_order):
    response = await client.post(
        f"/api/v1/orders/{test_order['id']}/cancel",
        headers={"x-user-id": "dev-user-id", "x-user-role": "user"},
        params={"reason": "no"}
    )
    assert response.status_code == 400
    assert "at least 5 characters" in response.json()["detail"]