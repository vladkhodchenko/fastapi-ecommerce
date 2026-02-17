from fastapi import APIRouter, Depends, status, HTTPException, Query
from datetime import datetime

from app.schemas import ProductCreate, Product as ProductSchema, Review as ReviewSchema, ProductList
from app.db_depends import get_async_db
from app.auth import get_current_seller

from app.models.products import Product as ProductModel
from app.models.categories import Category as CategoryModel
from app.models.reviews import Review as ReviewModel
from app.models.users import User as UserModel

from sqlalchemy import select, func, desc, update
from sqlalchemy.ext.asyncio import AsyncSession


# Создаём маршрутизатор для товаров
router = APIRouter(
    prefix="/products",
    tags=["products"],
)


@router.post("/", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_seller)
):
    """
    Создаёт новый товар.
    """

    stmt = select(CategoryModel).where(CategoryModel.id == product.category_id)
    category_id = (await db.scalars(stmt)).first()
    if category_id is None:
        raise HTTPException(status_code=400, detail="Category not found or inactive")

    db_product = ProductModel(**product.model_dump(), seller_id=current_user.id)
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)

    return db_product


@router.get("/2", response_model=ProductList, status_code=status.HTTP_200_OK)
async def get_all_products_2(
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        category_id: int | None = Query(
            None, description="ID категории для фильтрации"),
        min_price: float | None = Query(
            None, ge=0, description="Минимальная цена товара"),
        max_price: float | None = Query(
            None, ge=0, description="Максимальная цена товара"),
        in_stock: bool | None = Query(
            None, description="true — только товары в наличии, false — только без остатка"),
        seller_id: int | None = Query(
            None, description="ID продавца для фильтрации"),
        created_date: datetime | None = Query(
            None, description="Дата добавления"),
        db: AsyncSession = Depends(get_async_db)
):
    """
    Возвращает список всех товаров.
    """
    """
    Возвращает список всех активных товаров.
    """
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_price не может быть больше max_price",
        )
    filters = [ProductModel.is_active == True]

    if category_id is not None:
        filters.append(ProductModel.category_id == category_id)
    if min_price is not None:
        filters.append(ProductModel.price >= min_price)
    if max_price is not None:
        filters.append(ProductModel.price <= max_price)
    if in_stock is not None:
        filters.append(ProductModel.stock > 0 if in_stock else ProductModel.stock == 0)
    if seller_id is not None:
        filters.append(ProductModel.seller_id == seller_id)
    if created_date is not None:
        filters.append(ProductModel.created_at == created_date)

    total_stmt = select(func.count()).select_from(ProductModel).where(*filters)
    total = await db.scalar(total_stmt) or 0

    products_stmt = (
        select(ProductModel)
        .where(ProductModel.is_active == True)
        .order_by(ProductModel.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await db.scalars(products_stmt)).all()
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/", response_model=list[ProductSchema], status_code=status.HTTP_200_OK)
async def get_all_products(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех товаров.
    """
    stmt = select(ProductModel).where(ProductModel.is_active == True)
    products = (await db.scalars(stmt)).all()
    return products


@router.get("/category/{category_id}", response_model=ProductSchema)
async def get_products_by_category(category_id: int, db: AsyncSession = Depends(get_async_db)):
    stmt_category = select(CategoryModel).where(CategoryModel.id == category_id)
    stmt_product = select(ProductModel).where(ProductModel.category_id == category_id, ProductModel.is_active == True)

    is_category_id = (await db.scalars(stmt_category)).first()
    products_by_category = (await db.scalars(stmt_product)).all()

    if is_category_id is None:
        raise HTTPException(status_code=400, detail="Category not found or inactive")
    if products_by_category is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return products_by_category


@router.get("/{product_id}", response_model=ProductSchema)
async def get_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает детальную информацию о товаре по его ID.
    """
    stmt = select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
    product = (await db.scalars(stmt)).first()

    if product is None:
        return HTTPException(status_code=404, detail="Product not found")

    return product


@router.put("/{product_id}", response_model=ProductSchema)
async def update_product(
    product_id: int,
    product: ProductCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_seller)
):
    """
    Обновляет товар по его ID.
    """
    stmt = select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
    result_product = (await db.scalars(stmt)).first()
    if result_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if result_product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own products")

    category = (await db.scalars(select(CategoryModel).where(CategoryModel.id == product.category_id))).first()
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found or inactive")

    await db.execute(
        update(ProductModel)
        .where(ProductModel.id == product_id)
        .values(**product.model_dump())
    )
    await db.commit()
    await db.refresh(result_product)

    return result_product


@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_seller)
):
    stmt = select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
    product = (await db.scalars(stmt)).first()

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own products")

    await db.execute(update(ProductModel).where(ProductModel.id == product_id).values(is_active=False))
    await db.commit()

    return {"status": "success", "message": "Product marked as inactive"}


@router.get("/{product_id}/reviews/", response_model=list[ReviewSchema])
async def get_reviews_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    stmt = select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
    product = (await db.scalars(stmt)).first()

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    stmt = select(ReviewModel).where(ReviewModel.product_id == product_id, ReviewModel.is_active == True)
    reviews = (await db.scalars(stmt)).all()

    return reviews