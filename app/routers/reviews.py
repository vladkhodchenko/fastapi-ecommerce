from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reviews import Review as ReviewModel
from app.models.users import User as UserModel
from app.models.products import Product as ProductModel

from app.schemas import Review as ReviewSchema, ReviewCreate
from app.db_depends import get_async_db
from app.tools.reviews import update_product_rating

router = APIRouter(
    prefix="/reviews",
    tags=["reviews"],
)


@router.get("/", response_model=list[ReviewSchema])
async def get_reviews(db: AsyncSession = Depends(get_async_db)):
    result = await db.scalars(select(ReviewModel).where(ReviewModel.is_active == True))

    return result.all()


@router.post("/", response_model=ReviewSchema)
async def create_review(review: ReviewCreate, db: AsyncSession = Depends(get_async_db)):
    stmt_user = select(UserModel).where(UserModel.id == review.user_id, UserModel.is_active == True)
    stmt_product = select(ProductModel).where(ProductModel.id == review.product_id, ProductModel.is_active == True)
    stmt_review = select(ReviewModel).where(
        ReviewModel.user_id == review.user_id,
        ReviewModel.product_id == review.product_id,
        ReviewModel.is_active == True
    )

    user_id = (await db.scalars(stmt_user)).first()
    product_id = (await db.scalars(stmt_product)).first()
    exist_review = (await db.scalars(stmt_review)).first()

    if exist_review:
        raise HTTPException(status_code=409, detail="Review already exists")
    if user_id is None:
        raise HTTPException(status_code=400, detail="User not found or inactive")
    if product_id is None:
        raise HTTPException(status_code=400, detail="Product not found or inactive")

    await update_product_rating(db, review.product_id)

    db_review = ReviewModel(**review.model_dump())
    db.add(db_review)
    await db.commit()
    await db.refresh(db_review)

    return db_review


@router.get("/products/{product_id}/reviews/", response_model=list[ReviewSchema])
async def get_reviews_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    stmt = select(ReviewModel).where(ReviewModel.product_id == product_id, ReviewModel.is_active == True)
    reviews = (await db.scalars(stmt)).all()

    return reviews


@router.delete("/{review_id}", status_code=status.HTTP_200_OK)
async def delete_review(review_id: int, db: AsyncSession = Depends(get_async_db)):
    stmt = select(ReviewModel).where(ReviewModel.id == review_id, ReviewModel.is_active == True)
    review = (await db.scalars(stmt)).first()

    #TODO: Add validation user

    if review is None:
        raise HTTPException(status_code=404, detail="Review not found or inactive")

    await db.execute(update(ReviewModel).where(ReviewModel.id == review_id).values(is_active=False))
    await db.commit()

    return {"status": "success", "message": "Review marked as inactive"}




