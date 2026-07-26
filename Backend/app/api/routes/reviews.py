from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user

from app.models.user import User
from app.models.review import Review

from app.schemas.review import ReviewCreate, ReviewCreateResponse, ReviewResponse

router = APIRouter(
    prefix="/reviews",
    tags=["Reviews"]
)

@router.post("/", response_model=ReviewCreateResponse)
def create_review(
    review: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    new_review = Review(
        user_id=current_user.id,
        place_name=review.place_name,
        place_type=review.place_type,
        rating=review.rating,
        review_text=review.review_text,
        visit_date=review.visit_date
    )

    db.add(new_review)

    db.commit()

    db.refresh(new_review)

    return {
        "message": "Review created",
        "review_id": str(new_review.id)
    }

@router.get("/my", response_model=list[ReviewResponse])
def get_my_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    reviews = (
        db.query(Review)
        .filter(
            Review.user_id == current_user.id
        )
        .all()
    )

    return reviews


@router.get("/place/{place_name}", response_model=list[ReviewResponse])
def get_place_reviews(
    place_name: str,
    db: Session = Depends(get_db)
):

    reviews = (
        db.query(Review)
        .filter(
            Review.place_name == place_name
        )
        .all()
    )

    return reviews
