from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Annotated

from database import get_db
import models
import schemas
from dependencies import get_current_user
from schemas import APIResponse, ApplicationResponse, ApplicationCreate, ApplicationStatusUpdate

router = APIRouter()

# --- JOB SEEKER ENDPOINTS----

@router.post("/{job_id}", response_model=APIResponse[ApplicationResponse])
async def apply_to_job(
    job_id: int,
    application_data: ApplicationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[models.User, Depends(get_current_user)]
):
    """
    **Submit a Job Application**
    
    Allows a Job Seeker to apply for a specific job.
    
    **Logic Checks:**
    1. **Job Existence:** Validates if the `job_id` exists in the database.
    2. **Self-Application:** Prevents a Recruiter (Owner) from applying to their own job.
    3. **Duplicate Check:** Ensures the user hasn't already applied to this job to prevent spam.
    
    **Returns:**
    - The newly created Application object with status `PENDING`.
    """
    # 1. Check if Job Exists
    result = await db.execute(select(models.Job).where(models.Job.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # 2. Prevent Owner from applying to their own job 
    if job.owner_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot apply to your own job.")

    # 3. Check if User Already Applied 
    existing_app = await db.execute(
        select(models.Application)
        .where(models.Application.job_id == job_id)
        .where(models.Application.user_id == current_user.id)
    )
    if existing_app.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You have already applied to this job.")
    
    final_cv_file = application_data.cv_file
    # If user didn't provide a specific file, try to grab from their Profile
    if not final_cv_file:
        # Fetch the User Profile
        profile_result = await db.execute(
            select(models.UserProfile).where(models.UserProfile.user_id == current_user.id)
        )
        user_profile = profile_result.scalar_one_or_none()
        
        if user_profile and user_profile.resume_url:
            final_cv_file = user_profile.resume_url
        else:
            raise HTTPException(
                status_code=400, 
                detail="No CV found. Please upload a CV to your profile first or provide a file."
            )
        
    # 4. Create Application
    new_application = models.Application(
        job_id=job_id,
        user_id=current_user.id,
        cv_file=final_cv_file, 
        cover_letter=application_data.cover_letter, 
        status=models.ApplicationStatus.PENDING
    )

    db.add(new_application)
    await db.commit()
    await db.refresh(new_application)

    return APIResponse(
        success=True,
        message="Application submitted successfully!",
        data=new_application
    )

@router.get("/me", response_model=APIResponse[list[ApplicationResponse]])
async def get_my_applications(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[models.User, Depends(get_current_user)]
):
    """
    **Get My Application History**
    
    Retrieves all jobs that the *current logged-in user* has applied to.
    
    **Note:**
    - Uses `selectinload(models.Application.job)` to efficiently fetch the related Job details 
      (Title, Company, etc.) in a single query to avoid the "N+1" problem.
    """
    query = (
        select(models.Application)
        .where(models.Application.user_id == current_user.id)
        .options(selectinload(models.Application.job)) # Load Job data related to the application
    )
    result = await db.execute(query)
    applications = result.scalars().all()

    return APIResponse(
        success=True,
        message=f"You have applied to {len(applications)} jobs",
        data=applications
    )


# --- JOB OWNER ENDPOINTS ---

@router.patch("/{application_id}", response_model=APIResponse[ApplicationResponse])
async def review_application(
    application_id: int,    
    status_update: ApplicationStatusUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[models.User, Depends(get_current_user)]
):
    """
    **Review an Application (Accept/Reject)**
    
    Allows a Recruiter to update the status of an application (e.g., PENDING -> INTERVIEW).
    
    **Parameters:**
    - `application_id`: ID of the application to review.
    - `status_update`: JSON body containing the new status (enum).
    """
    # 1. Find application and its job
    query = (
        select(models.Application)
        .where(models.Application.id == application_id)
        .options(selectinload(models.Application.job)) 
    )
    result = await db.execute(query)
    application = result.scalar_one_or_none()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # 2. Only the owner of the job can change the status
    if application.job.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to review this application.")

    # 3. Update and Save
    application.status = status_update.status
    await db.commit()
    await db.refresh(application)

    return APIResponse(
        success=True,
        message=f"Application status updated to {application.status}",
        data=application
    )