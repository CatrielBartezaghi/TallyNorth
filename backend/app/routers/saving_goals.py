from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.saving_goal import SavingGoal
from app.models.user import User
from app.schemas.saving_goal import SavingGoalCreate, SavingGoalRead, SavingGoalUpdate
from app.routers.deps import get_current_active_user

router = APIRouter(prefix="/saving-goals", tags=["Saving Goals"])


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
    goal_data = payload.model_dump()
    goal_data["user_id"] = current_user.id
    goal = SavingGoal(**goal_data)
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
    goal = db.query(SavingGoal).filter(SavingGoal.id == goal_id, SavingGoal.user_id == current_user.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Saving goal not found")
    return goal


@router.put("/{goal_id}", response_model=SavingGoalRead)
def update_saving_goal(
    goal_id: str,
    payload: SavingGoalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    goal = db.query(SavingGoal).filter(SavingGoal.id == goal_id, SavingGoal.user_id == current_user.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Saving goal not found")
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
    goal = db.query(SavingGoal).filter(SavingGoal.id == goal_id, SavingGoal.user_id == current_user.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Saving goal not found")
    db.delete(goal)
    db.commit()
