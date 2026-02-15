import re
from pypdf import PdfReader
from io import BytesIO
from services.ai import get_embedding
from datetime import datetime

SKILLS_TAXONOMY = {
    "languange": {
        "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go",
        "Rust", "Swift", "Kotlin", "PHP", "Ruby", "Dart", "Scala", "R",
        "MATLAB", "Perl", "Haskell", "Elixir", "Objective-C", "Groovy"
    },
    "frontend": {
        "React", "Vue", "Angular", "Svelte", "Next.js", "Nuxt.js",
        "Redux", "Tailwind CSS", "Bootstrap", "HTML", "CSS",
        "Material UI", "Chakra UI", "Ant Design", "jQuery",
        "Webpack", "Vite", "Parcel"
    },
    "backend": {
        "FastAPI", "Django", "Flask", "Spring Boot", "Express.js",
        "NestJS", "Laravel", "Ruby on Rails", "ASP.NET", "Node.js",
        "GraphQL", "Gin", "Fiber", "Actix", "Micronaut", "Quarkus",
        "REST API", "gRPC", "Microservices"
    },
    "mobile": {
        "Flutter", "React Native", "Android", "iOS",
        "SwiftUI", "Jetpack Compose", "Ionic", "Xamarin"
    },
    "database": {
        "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis",
        "SQLite", "Cassandra", "DynamoDB", "Firebase",
        "Elasticsearch", "MariaDB", "Oracle", "Supabase",
        "CockroachDB", "Neo4j", "InfluxDB"
    },
    "devops": {
        "Docker", "Kubernetes", "AWS", "GCP", "Azure",
        "Terraform", "Ansible", "Jenkins", "GitHub Actions",
        "GitLab CI", "CircleCI", "Linux", "Bash", "Nginx",
        "Apache", "Helm", "ArgoCD", "Prometheus", "Grafana",
        "CI/CD", "CloudFormation"
    },
    "ai_data": {
        "Machine Learning", "Deep Learning", "PyTorch",
        "TensorFlow", "Keras", "Scikit-learn", "Pandas", "NumPy",
        "Matplotlib", "Seaborn", "NLP", "LangChain", "LLM",
        "HuggingFace", "YOLO", "Computer Vision", "OpenCV",
        "XGBoost", "LightGBM", "CatBoost", "Spark", "Hadoop",
        "Kafka", "Airflow", "Feature Engineering"
    },
    "testing": {
        "PyTest", "Unit Testing", "Integration Testing",
        "Selenium", "Cypress", "Playwright", "JUnit",
        "TestNG", "Mocha", "Chai"
    },
    "architecture": {
        "Clean Architecture", "Domain Driven Design",
        "Event Driven Architecture", "Monolith",
        "Serverless", "Design Patterns", "SOLID",
        "CQRS"
    },
    "tools": {
        "Git", "GitHub", "GitLab", "Bitbucket",
        "Postman", "Insomnia", "Swagger",
        "Figma", "Jira", "Notion", "Trello"
    }
}

SKILL_ALIASES = {
    # --- Languages ---
    "js": "JavaScript",
    "ts": "TypeScript",
    "golang": "Go",
    "go-lang": "Go",
    "cpp": "C++",
    "cplusplus": "C++",
    "cplus": "C++",
    "csharp": "C#",
    "c-sharp": "C#",

    # --- Node / Backend ---
    "node": "Node.js",
    "nodejs": "Node.js",
    "node js": "Node.js",
    "express": "Express.js",
    "rest": "REST API",
    "restful": "REST API",
    "grpc": "gRPC",
    "microservice": "Microservices",
    "micro-service": "Microservices",

    # --- Frontend ---
    "reactjs": "React",
    "react js": "React",
    "vuejs": "Vue",
    "vue js": "Vue",
    "nextjs": "Next.js",
    "next js": "Next.js",
    "nuxtjs": "Nuxt.js",
    "tailwind": "Tailwind CSS",
    "mui": "Material UI",

    # --- Database ---
    "postgres": "PostgreSQL",
    "postgre": "PostgreSQL",
    "psql": "PostgreSQL",
    "mongo": "MongoDB",
    "elastic": "Elasticsearch",

    # --- DevOps / Cloud ---
    "k8s": "Kubernetes",
    "docker-compose": "Docker",
    "gh actions": "GitHub Actions",
    "github action": "GitHub Actions",
    "gitlab-ci": "GitLab CI",
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",

    # --- AI / Data ---
    "ml": "Machine Learning",
    "machine-learning": "Machine Learning",
    "dl": "Deep Learning",
    "deep-learning": "Deep Learning",
    "tf": "TensorFlow",
    "sklearn": "Scikit-learn",
    "pytorch lightning": "PyTorch",
    "huggingface transformers": "HuggingFace",
    "computer-vision": "Computer Vision",

    # --- Testing ---
    "pytest": "PyTest",
    "unit test": "Unit Testing",
    "unit tests": "Unit Testing",
    "integration test": "Integration Testing",
    "e2e": "Integration Testing",

    # --- Architecture ---
    "ddd": "Domain Driven Design",
    "clean arch": "Clean Architecture",
    "event-driven": "Event Driven Architecture",
    "design pattern": "Design Patterns",

    # --- Tools ---
    "gh": "GitHub",
    "gitlab.com": "GitLab",
    "figma design": "Figma"
}

# KNOWN_SKILLS = {
#     "Python", "FastAPI", "Django", "Flask", "Docker", "Kubernetes", 
#     "AWS", "GCP", "Azure", "SQL", "PostgreSQL", "MySQL", "MongoDB",
#     "React", "Vue", "Angular", "Node.js", "Java", "Go", "C++",
#     "Machine Learning", "Deep Learning", "PyTorch", "TensorFlow",
#     "LightGBM", "YOLO", "Computer Vision", "NLP", "Git", "Linux",
#     "Scikit-learn", "Pandas", "NumPy"
# }


def build_skill_lookup():
    """Builds the dictionary { 'alias': 'Canonical Name' }."""
    lookup = {}
    
    # Add base taxonomy
    for category, skills in SKILLS_TAXONOMY.items():
        for skill in skills:
            lookup[skill.lower()] = skill
    
    # Add aliases
    for aliases, canonical in SKILL_ALIASES.items():
        lookup[aliases] = canonical
    
    return lookup

SKILL_LOOKUP = build_skill_lookup()

def clean_text_artifacts(text: str) -> str:
    """Remove OCR artifacts and weird symbols."""
    # Remove non-ASCII symbols like ♂, ⌢
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)

    # Fix "Split Kerning" (e.g., "W ahyu" -> "Wahyu")
    text = re.sub(r"([A-Z])\s+(?=[a-z])", r"\1", text)

    # Collapse spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_text_from_pdf(file_content: bytes) -> str:
    """
    **PDF Text Extractor**
    
    Reads the raw bytes of a PDF file and converts it into a plain string.
    
    **Parameters:**
    - `file_content`: The binary content of the uploaded file.
    """
    try:
        # Open PDF from memory (no need to save to disk first)
        pdf_reader = PdfReader(BytesIO(file_content))

        # Extract text page by page
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"   
        return text.strip()
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""

# def clean_name(name: str) -> str:
#     """
#     **Name Cleaner**
    
#     Fixes common PDF kerning issues where letters have spaces between them.
#     Example: 'W ahyu' -> 'Wahyu'
#     """
#     if not name: return ""
#     return re.sub(r"([A-Z])\s+(?=[a-z])", r"\1", name).strip()

def extract_details(text: str):
    """
    **Detail Extractor**
    
    Attempts to parse specific metadata from the raw resume text.
    """
    # Name Extraction
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Simple Heuristic 
    extracted_name = "Unknown Candidate"
    if lines:
        words = lines[0].split()
        extracted_name = " ".join(words[:3])
    
    # Experience calculator
    lower_text = text.lower()

    # Find start of "Experience" section to avoid counting Graduation Dates
    experience_start_index = -1
    for keyword in ["experience","work history", "employment"]:
        idx = lower_text.find(keyword)
        if idx != -1:
            experience_start_index = idx
            break

    # Crop text if header found
    target_text = text if experience_start_index == -1 else text[experience_start_index:]
    
    # Find years (2015-2023)
    years = re.findall(r"\b(20\d{2})\b", target_text)
    
    experience_years = 0
    if years:
        years_int = [int(y) for y in years]
        
        # Filter future years to be safe
        current_year = datetime.now().year
        
        valid_years = [y for y in years_int if y <= current_year]
        
        if valid_years:
            experience_years = max(valid_years) - min(valid_years)
    
    return extracted_name, experience_years


def extract_skills(text: str) -> list[str]:
    """
    **Skill Matcher**
    
    Scans the resume for keywords defined in `KNOWN_SKILLS`.
    Uses SKILL_LOOKUP to find aliases (e.g., "JS" -> "JavaScript").
    """
    found_skills = set()
    text_lower = text.lower()

    for search_term, canonical_name in SKILL_LOOKUP.items():
        pattern = r"(?<!\w)" + re.escape(search_term) + r"(?!\w)"
        
        if re.search(pattern, text_lower):
            found_skills.add(canonical_name)
            
    return list(found_skills)

# def estimate_experience(text: str) -> int:
#     years = re.findall(r"\b(20\d{2})\b", text)
#     if not years:
#         return 0

#     years = [int(y) for y in years]
#     min_years = min(years)
#     max_years = max(years)

#     diff = max_years - min_years
#     return max(0, diff)

def analyze_resume(file_content: bytes):
    """
    Main Pipeline:
    1. Extract Raw PDF Text
    2. Clean Artifacts (Fix 'W ahyu')
    3. Extract Details (Smart Experience Logic)
    4. Extract Skills (Smart Taxonomy)
    5. Embed
    """
    raw_text = extract_text_from_pdf(file_content)
    if not raw_text: return None

    # 1. Clean FIRST
    cleaned_text = clean_text_artifacts(raw_text)
    
    # 2. Use Cleaned Text for everything else
    extracted_name, years = extract_details(cleaned_text)
    skills = extract_skills(cleaned_text)

    # 3. Embed Cleaned Text
    embedding = get_embedding(cleaned_text[:2000])
    
    return {
        "text": cleaned_text,
        "embedding": embedding,
        "skills": skills,
        "experience_years": years,
        "extracted_name": extracted_name
    }