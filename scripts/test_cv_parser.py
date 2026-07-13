"""Test the CV parser with sample CVs.

Run with: uv run pytest scripts/test_cv_parser.py
"""

from app.cv_parser import parse_cv


# --- Sample CV 1: Data Science / Tech background ---
SAMPLE_CV_DATA_SCIENCE = """
AUNG KYAW ZAW
Yangon, Myanmar | aungkz@email.com | +95-9-123456789

SUMMARY
Recent Computer Science graduate with hands-on experience in data analysis,
machine learning, and web development. Passionate about leveraging technology
to solve real-world problems in Myanmar's growing digital economy.

EDUCATION
Bachelor of Science in Computer Science
Yangon Technological University (YTU), 2020 - 2024
- GPA: 3.7/4.0
- Relevant coursework: Data Structures, Machine Learning, Database Systems,
  Statistics, Software Engineering

WORK EXPERIENCE
Data Analyst Intern | Wave Money | June 2023 - December 2023
- Analyzed transaction data using Python and SQL to identify fraud patterns
- Built dashboards in Tableau for executive reporting
- Wrote automated data pipelines processing 500K+ daily records
- Collaborated with the engineering team on API integration

Junior Web Developer | Myanmar ICT Association | January 2024 - Present
- Developed responsive web applications using React and Node.js
- Managed PostgreSQL databases and wrote REST APIs
- Conducted code reviews and mentored junior team members

SKILLS
Programming: Python, JavaScript, SQL, R
Frameworks: React, Node.js, FastAPI, TensorFlow
Tools: Git, Docker, Tableau, Power BI, Excel
Cloud: AWS (S3, Lambda), Google Cloud Platform

LANGUAGES
English (Fluent), Burmese (Native), Japanese (Intermediate)

CERTIFICATIONS
Google Data Analytics Professional Certificate, 2023
AWS Cloud Practitioner, 2024
"""


# --- Sample CV 2: Social Science / Governance background ---
SAMPLE_CV_GOVERNANCE = """
THIN THIN AUNG
Mandalay, Myanmar

EDUCATION
Master of Arts in International Relations
University of Mandalay, 2021 - 2023

Bachelor of Arts in Political Science
University of Mandalay, 2017 - 2021

PROFESSIONAL EXPERIENCE
Program Coordinator | UNDP Myanmar | March 2023 - Present
- Coordinated community-based governance programs across 5 townships
- Developed monitoring and evaluation frameworks for peacebuilding initiatives
- Managed stakeholder engagement with local government officials
- Prepared policy briefs and donor reports on democratic governance

Research Assistant | International Crisis Group | June 2022 - February 2023
- Conducted field research on conflict dynamics in ethnic minority areas
- Analyzed qualitative data from 50+ stakeholder interviews
- Co-authored reports on political transitions and humanitarian access

Volunteer Coordinator | Myanmar Red Cross | 2019 - 2022
- Organized community health education workshops in rural areas
- Trained 30+ volunteers in disaster preparedness
- Managed project budgets and logistics for 10 township-level programs

SKILLS
Research: Qualitative research, field research, stakeholder analysis
Technical: Microsoft Office, SPSS, NVivo, data visualization
Soft Skills: Public speaking, report writing, cross-cultural communication,
project management, team leadership

LANGUAGES
English (Advanced), Burmese (Native), Shan (Conversational)
"""


# --- Sample CV 3: Minimal / Sparse CV ---
SAMPLE_CV_MINIMAL = """
Hi, I'm Zaw Min Oo from Yangon. I studied at University of Computer Studies
Yangon (UCSY). I know some Python and have used Excel for data entry work.
I worked part-time at a local IT shop fixing computers for 2 years.
I want to work in technology.
"""

def test_data_science_cv():
    result = parse_cv(SAMPLE_CV_DATA_SCIENCE)
    assert len(result.skills) > 0
    assert "Python" in [s.name for s in result.skills]
    assert len(result.experience) > 0
    titles = [e.title.strip() for e in result.experience]
    assert any("Data Analyst Intern" in t for t in titles)

def test_governance_cv():
    result = parse_cv(SAMPLE_CV_GOVERNANCE)
    assert len(result.skills) > 0
    assert len(result.experience) > 0

def test_minimal_cv():
    result = parse_cv(SAMPLE_CV_MINIMAL)
    assert result is not None
