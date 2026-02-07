from fastapi import APIRouter, Depends, status, HTTPException

from app.schemas import ProductCreate, Product as ProductSchema
from app.db_depends import get_db

from app.models.products import Product as ProductModel
from app.models.categories import Category as CategoryModel

from sqlalchemy.orm import Session
from sqlalchemy import select, update

# Создаём маршрутизатор для товаров
router = APIRouter(
    prefix="/products",
    tags=["products"],
)


@router.post("/", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
async def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """
    Создаёт новый товар.
    """

    stmt = select(CategoryModel).where(CategoryModel.id == product.category_id)
    category_id = db.scalars(stmt).first()
    if category_id is None:
        raise HTTPException(status_code=400, detail="Category not found or inactive")

    db_product = ProductModel(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    return db_product


@router.get("/", response_model=list[ProductSchema], status_code=status.HTTP_200_OK)
async def get_all_products(db: Session = Depends(get_db)):
    """
    Возвращает список всех товаров.
    """
    stmt = select(ProductModel).where(ProductModel.is_active == True)
    products = db.scalars(stmt).all()
    return products


@router.get("/products/category/{category_id}", response_model=ProductSchema)
async def get_products_by_category(category_id: int, db: Session = Depends(get_db)):
    stmt_category = select(CategoryModel).where(CategoryModel.id == category_id)
    stmt_product = select(ProductModel).where(ProductModel.category_id == category_id, ProductModel.is_active == True)

    is_category_id = db.scalars(stmt_category).first()
    products_by_category = db.scalars(stmt_product).all()

    if is_category_id is None:
        raise HTTPException(status_code=400, detail="Category not found or inactive")
    if products_by_category is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return products_by_category


@router.get("/products/{product_id}", response_model=ProductSchema)
async def get_product(product_id: int, db: Session = Depends(get_db)):
    """
    Возвращает детальную информацию о товаре по его ID.
    """
    stmt = select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
    product = db.scalars(stmt).first()

    if product is None:
        return HTTPException(status_code=404, detail="Product not found")

    return product


@router.put("/products/{product_id}")
async def update_product(product_id: int, product: ProductCreate,db: Session = Depends(get_db)):
    """
    Обновляет товар по его ID.
    """
    stmt = select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
    product = db.scalars(stmt).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    stmt = select(CategoryModel).where(CategoryModel.id == product.category_id)
    category = db.scalars(stmt).first()
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found or inactive")

    db.execute(
        update(ProductModel)
        .where(ProductModel.id == product_id)
        .values(**product.model_dump())
    )
    db.commit()
    db.refresh(product)

    return product


@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
async def delete_product(product_id: int, db: Session = Depends(get_db)):
    stmt = select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
    product = db.scalars(stmt).first()

    if product is None:
        raise HTTPException(status_code=404, details="Product not found")

    db.execute(update(ProductModel).where(ProductModel.id == product_id).values(is_active=False))
    db.commit()

    return {"status": "success", "message": "Product marked as inactive"}