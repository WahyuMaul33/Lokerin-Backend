import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from database import SessionLocal, engine, Base
from models import User, Job, UserRole, JobType
from routers.auth import get_password_hash
from services.ai import get_embedding # Uses your new AI logic automatically!
import random
from datetime import datetime

# --- 🎯 THE NEW SKILL POOL (Aligned with your Taxonomy) ---
SKILL_POOLS = {
    "Data Scientist": ["Python", "Machine Learning", "Deep Learning", "Pandas", "SQL", "Scikit-learn", "TensorFlow", "LightGBM"],
    "Backend Engineer": ["Python", "FastAPI", "Django", "PostgreSQL", "Docker", "Redis", "AWS", "System Design"],
    "Frontend Developer": ["React", "TypeScript", "Tailwind CSS", "Next.js", "Figma", "HTML", "CSS"],
    "DevOps Engineer": ["Docker", "Kubernetes", "AWS", "Terraform", "CI/CD", "Linux", "Bash"],
    "Full Stack Developer": ["React", "Node.js", "TypeScript", "PostgreSQL", "MongoDB", "Docker"]
}

LOCATIONS = ["Jakarta", "Bali", "Bandung", "Surabaya", "Yogyakarta", "Remote", "Singapore", "Tokyo"]
COMPANIES = ["GoTo", "Traveloka", "Shopee", "Tokopedia", "Blibli", "Ruangguru", "Tiket.com", "TechNova"]

async def seed_db():
    async with engine.begin() as conn:
        # Create tables from scratch
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        print("🌱 Seeding Users...")
        
        # 1. Create a Recruiter
        recruiter = User(
            email="recruiter@example.com",
            username="recruiter_main",
            hashed_password=get_password_hash("password123"),
            role=UserRole.RECRUITER,
            company_name="Tech Giants Inc"
        )
        db.add(recruiter)
        
        # 2. Create a Seeker (You can log in as this guy too)
        seeker = User(
            email="seeker@example.com",
            username="job_seeker",
            hashed_password=get_password_hash("password123"),
            role=UserRole.SEEKER
        )
        db.add(seeker)
        await db.commit()
        await db.refresh(recruiter)

        print(f"🚀 Generating 100 Jobs with AI Embeddings...")
        
        jobs_to_add = []
        
        # 3. Generate 100 Jobs
        for i in range(100):
            job_title = random.choice(list(SKILL_POOLS.keys()))
            skills = SKILL_POOLS[job_title]
            location = random.choice(LOCATIONS)
            is_remote = location == "Remote"
            
            # Make the description realistic
            description = f"We are looking for a {job_title} to join our team in {location}. " \
                          f"Must be proficient in {', '.join(skills[:3])}. " \
                          f"Great opportunity for growth!"
            
            # 🔥 GENIUS MOVE: Generate Vector Embedding right now!
            # This ensures the database has vectors ready for searching.
            job_embedding = get_embedding(description) 

            job = Job(
                title=f"{job_title} {'(Senior)' if i % 5 == 0 else ''}",
                owner_id=recruiter.id,
                company=random.choice(COMPANIES),
                location=location,
                salary=random.randint(8, 25) * 1000000, # 8jt - 25jt
                description=description,
                requirements="Bachelor Degree, 2+ Years Experience",
                job_type=JobType.FULL_TIME,
                is_remote=is_remote,
                skills=skills, # Saves as JSON
                job_embedding=job_embedding # <--- THE KEY PIECE
            )
            jobs_to_add.append(job)
            
            if i % 10 == 0:
                print(f"   ...Generated {i}/100 jobs")

        db.add_all(jobs_to_add)
        await db.commit()
        
        print(f"✅ Successfully seeded {len(jobs_to_add)} jobs!")

if __name__ == "__main__":
    asyncio.run(seed_db())