from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.account import Account
from app.models.investment import Investment
from app.models.saving_goal import SavingGoal, SavingGoalAllocation
from app.models.user import User
from app.schemas.saving_goal import (
    SavingGoalAllocationCreate,
    SavingGoalAllocationRead,
    SavingGoalCreate,
    SavingGoalRead,
    SavingGoalUpdate,
)
from app.routers.deps import get_current_active_user


router = APIRouter(prefix="/saving-goals", tags=["Saving Goals"])


def _owned_goal(db: Session, user_id, goal_id) -> SavingGoal:
    goal = db.query(SavingGoal).filter(
        SavingGoal.id == goal_id,
        SavingGoal.user_id == user_id,
    ).first()
    if goal is None:
        raise HTTPException(status_code=404, detail="Saving goal not found")
    return goal


@router.get("/", response_model=list[SavingGoalRead])
def list_saving_goals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return db.query(SavingGoal).filter(SavingGoal.user_id == current_user.id).order_by(SavingGoal.created_at.desc()).all()


@router.post("/", response_model=SavingGoalRead, status_code=status.HTTP_201_CREATED)
def create_saving_goal(
    payload: SavingGoalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    goal = SavingGoal(**payload.model_dump(), user_id=current_user.id)
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


@router.get("/{goal_id}", response_model=SavingGoalRead)
def get_saving_goal(
    goal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return _owned_goal(db, current_user.id, goal_id)


@router.put("/{goal_id}", response_model=SavingGoalRead)
def update_saving_goal(
    goal_id: str,
    payload: SavingGoalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    goal = _owned_goal(db, current_user.id, goal_id)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(goal, field, value)
    db.commit()
    db.refresh(goal)
    return goal


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saving_goal(
    goal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    goal = _owned_goal(db, current_user.id, goal_id)
    db.delete(goal)
    db.commit()


@router.get("/{goal_id}/allocations", response_model=list[SavingGoalAllocationRead])
def list_allocations(
    goal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    goal = _owned_goal(db, current_user.id, goal_id)
    return (
        db.query(SavingGoalAllocation)
        .filter(SavingGoalAllocation.saving_goal_id == goal.id)
        .order_by(SavingGoalAllocation.created_at.asc())
        .all()
    )


@router.post(
    "/{goal_id}/allocations",
    response_model=SavingGoalAllocationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_allocation(
    goal_id: str,
    payload: SavingGoalAllocationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    goal = _owned_goal(db, current_user.id, goal_id)

    if payload.account_id is not None:
        source = db.query(Account).filter(
            Account.id == payload.account_id,
            Account.user_id == current_user.id,
        ).first()
        source_field = SavingGoalAllocation.account_id
        source_id = payload.account_id
    else:
        source = db.query(Investment).filter(
            Investment.id == payload.investment_id,
            Investment.user_id == current_user.id,
        ).first()
        source_field = SavingGoalAllocation.investment_id
        source_id = payload.investment_id

    if source is None:
        raise HTTPException(status_code=404, detail="Allocation source not found")

    already_allocated = sum(
        (
            row.allocation_percent
            for row in db.query(SavingGoalAllocation)
            .filter(
                SavingGoalAllocation.user_id == current_user.id,
                source_field == source_id,
            )
            .all()
        ),
        0,
    )
    if already_allocated + payload.allocation_percent > 100:
        raise HTTPException(status_code=422, detail="This source would be allocated above 100% across goals")

    allocation = SavingGoalAllocation(
        user_id=current_user.id,
        saving_goal_id=goal.id,
        **payload.model_dump(),
    )
    db.add(allocation)
    db.commit()
    db.refresh(allocation)
    return allocation


@router.delete("/{goal_id}/allocations/{allocation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_allocation(
    goal_id: str,
    allocation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    goal = _owned_goal(db, current_user.id, goal_id)
    allocation = db.query(SavingGoalAllocation).filter(
        SavingGoalAllocation.id == allocation_id,
        SavingGoalAllocation.saving_goal_id == goal.id,
        SavingGoalAllocation.user_id == current_user.id,
    ).first()
    if allocation is None:
        raise HTTPException(status_code=404, detail="Saving goal allocation not found")
    db.delete(allocation)
    db.commit()
