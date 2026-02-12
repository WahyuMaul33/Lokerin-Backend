import asyncio
import random
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from database import engine, AsyncSessionLocal, Base
import models
from services.ai import get_embedding
from routers.auth import hash_password

# --- DATASETS (Indonesia Context) ---

LOCATIONS = ["Jakarta, Indonesia", "Bandung, West Java", "Yogyakarta, ID", "Surabaya, East Java", "Remote (Indonesia)", "Bali, Indonesia"]

COMPANIES = [
    ("TechNova Indonesia", "recruiter_nova"),
    ("Solusi Digital Jaya", "recruiter_jaya"),
    ("Creative Indo Studio", "recruiter_studio"),
    ("DataSinergi", "recruiter_data"),
    ("CloudNesia Systems", "recruiter_cloud")
]

JOB_TITLES = [
    ("Senior Backend Engineer (Python)", ["Python", "Django", "FastAPI", "PostgreSQL", "Docker"]),
    ("Frontend Developer (React)", ["React", "TypeScript", "Tailwind", "Redux"]),
    ("DevOps Engineer", ["AWS", "Kubernetes", "Docker", "CI/CD", "Linux"]),
    ("Data Scientist", ["Python", "Pandas", "Machine Learning", "Scikit-learn", "SQL"]),
    ("Fullstack Engineer (Go + Vue)", ["Go", "Vue.js", "MySQL", "Redis"]),
    ("Mobile Developer (Flutter)", ["Flutter", "Dart", "Firebase", "Android"]),
    ("UI/UX Designer", ["Figma", "UI Design", "User Research", "Prototyping"]),
    ("QA Automation Engineer", ["Python", "Selenium", "PyTest", "Jenkins"]),
    ("Product Manager", ["Agile", "Scrum", "Product Management", "Jira"]),
    ("Junior Web Developer", ["HTML", "CSS", "JavaScript", "PHP"])
]

DESCRIPTIONS = [
    "We are looking for a passionate {title} to join our team in {location}. You will work on high-scale applications.",
    "Join one of the fastest-growing tech startups in Indonesia. As a {title}, you will drive innovation.",
    "Seeking a talented {title} to help us build the next generation of our platform. Competitive salary and benefits.",
    "Are you an expert in {skill}? We need a {title} to lead our new initiative in {location}.",
    "Work from home or office! We are looking for a {title} with strong experience in {skill}."
]

# --- THE SCRIPT ---

async def reset_database():
    print("🗑️  Wiping database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    print("✨  Database reset complete.")

async def create_users(db: AsyncSession):
    print("bust  Creating Users...")
    
    recruiters = []
    # 1. Create Recruiters
    for company_name, username in COMPANIES:
        user = models.User(
            username=username,
            email=f"{username}@example.com",
            hashed_password=hash_password("password123"),
            role=models.Role.OWNER,
            company_name=company_name,
            is_active=True
        )
        db.add(user)
        recruiters.append(user)
    
    # 2. Create Seekers
    seekers = []
    for i in range(1, 6):
        user = models.User(
            username=f"seeker_{i}",
            email=f"seeker{i}@example.com",
            hashed_password=hash_password("password123"),
            role=models.Role.SEEKER,
            company_name=None,
            is_active=True
        )
        db.add(user)
        seekers.append(user)

    await db.commit()
    print(f"✅  Created {len(recruiters)} Recruiters and {len(seekers)} Seekers.")
    return recruiters, seekers

async def create_jobs(db: AsyncSession, recruiters):
    print("💼  Creating Jobs & Generating AI Embeddings (This might take a moment)...")
    
    jobs_created = 0
    
    # Create 30 random jobs
    for _ in range(30):
        # Pick random data
        recruiter = random.choice(recruiters)
        title, skills = random.choice(JOB_TITLES)
        location = random.choice(LOCATIONS)
        is_remote = "Remote" in location
        
        # Generate Text
        desc_template = random.choice(DESCRIPTIONS)
        description = desc_template.format(title=title, location=location, skill=skills[0])
        
        # Generate Salary (8jt to 35jt)
        salary = random.randint(8, 35) * 1_000_000
        
        # 🧠 GENERATE AI EMBEDDING
        # We combine everything so the AI understands the full context
        full_text = f"Job Title: {title}. Description: {description}. Skills: {' '.join(skills)}. Location: {location}"
        embedding = get_embedding(full_text)

        job = models.Job(
            title=title,
            company=recruiter.company_name,
            location=location,
            salary=salary,
            description=description,
            is_remote=is_remote,
            skills=skills,
            owner_id=recruiter.id,
            job_embedding=embedding, # <--- The Magic
            job_posted=models.datetime.now(models.timezone.utc)
        )
        db.add(job)
        jobs_created += 1
        
        # Simple progress indicator
        if jobs_created % 5 == 0:
            print(f"   ... generated {jobs_created} jobs")

    await db.commit()
    print(f"✅  Successfully posted {jobs_created} jobs with AI vectors!")

async def main():
    # 1. Reset DB
    await reset_database()
    
    # 2. Start Session
    async with AsyncSessionLocal() as db:
        try:
            # 3. Create Users
            recruiters, seekers = await create_users(db)
            
            # 4. Refresh to get IDs
            for r in recruiters: await db.refresh(r)
            
            # 5. Create Jobs
            await create_jobs(db, recruiters)
            
        except Exception as e:
            print(f"❌  Error: {e}")
            await db.rollback()
        finally:
            await db.close()

if __name__ == "__main__":
    asyncio.run(main())