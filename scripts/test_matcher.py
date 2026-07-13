import asyncio
from app.services.cv_parser import parse_cv
from app.services.job_title_matcher import match_occupations

async def test_matcher():
    print("Parsing CV...")
    cv_text = """
    I am a data scientist with 5 years of experience.
    SKILLS
    - Python programming
    - Machine learning
    - SQL database management
    - Data visualization with Tableau
    - Scikit-learn and pandas
    
    EXPERIENCE
    Data Analyst at Acme Corp (Jan 2020 - Present)
    Built predictive models and dashboards.
    """
    
    parsed_cv = parse_cv(cv_text)
    print("Parsed Skills:")
    for skill in parsed_cv.skills:
        print(f"  - {skill.name} (weight: {skill.weight})")
        
    print("\nMatching Occupations against Live ESCO API...")
    matches = await match_occupations(parsed_cv, top_k=3)
    
    if not matches:
        print("No matches found.")
        return
        
    for i, match in enumerate(matches, 1):
        print(f"\nMatch {i}: {match.target_title} (Score: {match.match_score_percent}%)")
        print(f"  Existing Skills: {match.existing_skills}")
        print(f"  Missing Skills: {match.missing_skills}")

if __name__ == "__main__":
    asyncio.run(test_matcher())
