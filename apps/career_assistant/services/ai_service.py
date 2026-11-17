import os
import re
import logging
from django.conf import settings
from apps.career_assistant.models import Conversation, ChatMessage
from apps.career_assistant.services.context_builder import StudentCareerContextBuilder
from apps.career_assistant.services.prompt_builder import CareerPromptBuilder

logger = logging.getLogger(__name__)


class AICareerAssistantService:
    """
    Orchestrates the AI Career & Placement Assistant.
    Leverages Google Gemini API when configured, with an institutional rule-based
    fallback engine that personalizes guidance using the student's actual TPMS record.
    """

    @classmethod
    def get_api_key(cls) -> str:
        return os.environ.get('GEMINI_API_KEY') or getattr(settings, 'GEMINI_API_KEY', '')

    @classmethod
    def generate_response(cls, conversation: Conversation, user_message: str) -> str:
        student = conversation.student
        query_text = user_message.strip()

        # 1. Build context
        context = StudentCareerContextBuilder.build_context(student, query=query_text)
        system_instruction = CareerPromptBuilder.build_system_prompt(context)

        # 2. Check for API key
        api_key = cls.get_api_key()

        if api_key:
            try:
                response_text = cls._call_gemini_api(api_key, system_instruction, conversation, query_text)
                if response_text:
                    return response_text
            except Exception as e:
                logger.warning(f"Gemini API invocation failed: {e}. Falling back to institutional engine.")

        # 3. Fallback: High-Quality Institutional Rule-Based Engine
        return cls._generate_institutional_response(context, query_text)

    @classmethod
    def get_model_name(cls) -> str:
        return os.environ.get('GEMINI_MODEL') or getattr(settings, 'GEMINI_MODEL', '') or 'gemini-flash-latest'

    @classmethod
    def _call_gemini_api(cls, api_key: str, system_instruction: str, conversation: Conversation, user_message: str) -> str:
        """Calls the Gemini REST API with the last few turns of this conversation."""
        import requests

        # Last 12 messages, oldest first. The newest student message is already saved,
        # so it is part of this history and is not sent a second time.
        recent = list(conversation.messages.order_by('-timestamp')[:12])[::-1]
        contents = []
        for msg in recent:
            role = 'user' if msg.sender == 'STUDENT' else 'model'
            if contents and contents[-1]['role'] == role:
                contents[-1]['parts'][0]['text'] += "\n\n" + msg.content
            else:
                contents.append({'role': role, 'parts': [{'text': msg.content}]})
        # Gemini expects the conversation to start with a user turn.
        while contents and contents[0]['role'] != 'user':
            contents.pop(0)
        if not contents or contents[-1]['role'] != 'user':
            contents.append({'role': 'user', 'parts': [{'text': user_message}]})

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{cls.get_model_name()}:generateContent"
        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": contents,
        }
        resp = requests.post(url, json=payload, headers={'x-goog-api-key': api_key}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        parts = data['candidates'][0]['content']['parts']
        return "".join(p.get('text', '') for p in parts).strip()

    @classmethod
    def _generate_institutional_response(cls, context: dict, query: str) -> str:
        """
        Expert rule-based career guidance engine grounded in the student's actual TPMS data.
        """
        student = context.get('student', {})
        matched_drive = context.get('matched_drive')
        active_drives = context.get('active_drives', [])
        study_resources = context.get('study_resources', [])
        student_skills = student.get('skills', [])
        skills_str = ", ".join(student_skills) if student_skills else "not yet specified in your profile"
        q_lower = query.lower()

        name = student.get('name', 'Student')
        dept = student.get('department_name', 'Engineering')
        cgpa = student.get('graduation_cgpa', 0.0)
        backlogs = student.get('active_backlogs', 0)

        # ----------------------------------------------------------------------
        # Case A: Company-Specific Preparation Query
        # ----------------------------------------------------------------------
        if matched_drive or any(c in q_lower for c in ['company', 'drive', 'deloitte', 'google', 'tcs', 'infosys', 'microsoft']):
            target = matched_drive or (active_drives[0] if active_drives else None)
            if target:
                comp_name = target['company']
                role_title = target['title']
                pkg = target['package']
                min_cgpa = target['min_cgpa']
                max_bl = target['max_backlogs']

                eligible_str = "meets" if cgpa >= min_cgpa and backlogs <= max_bl else "does not meet"

                res_recommendations = ""
                if study_resources:
                    res_recommendations = "\n\n### Recommended TPMS Resources for This Drive\n"
                    for r in study_resources[:3]:
                        res_recommendations += f"- [{r['title']}]({r['url']}) — *{r['category']} ({r['type']})*\n"

                return f"""### Comprehensive Placement Preparation Plan: {comp_name} ({role_title})

Hello **{name}**, here is your personalized preparation strategy for the upcoming **{comp_name}** recruitment drive offering **{pkg} LPA**.

#### 1. Eligibility & Cut-Off Assessment
- **Your Academic Record**: CGPA **{cgpa} / 10.0**, Live Backlogs: **{backlogs}**.
- **Drive Cut-Offs**: Minimum CGPA **{min_cgpa}**, Maximum Backlogs: **{max_bl}**.
- **Verdict**: Your current academic record **{eligible_str}** the institutional screening requirements for this drive.

#### 2. Recruitment Round Breakdown & Strategy
1. **Online Assessment (Cognitive & Technical)**:
   - Focus on quantitative aptitude, logical reasoning, verbal ability, and pseudocode debugging.
   - Core CS fundamentals: Object-Oriented Programming (OOP), Database Management Systems (DBMS), and Computer Networks.
2. **Technical Interview Rounds**:
   - Expect deep questions on Data Structures (Arrays, Strings, HashMaps, Trees) and Time/Space complexity.
   - Prepare to walk through the architecture of projects listed on your resume, especially technical challenges you solved.
   - Relevant skills from your profile: **{skills_str}**.
3. **HR & Behavioral Round**:
   - Research {comp_name}'s core values, recent projects, and market presence.
   - Prepare STAR-format (Situation, Task, Action, Result) answers for teamwork and problem-solving scenarios.
{res_recommendations}
> *These are built-in suggestions based on your record. Live AI answers turn on when the placement office adds a Gemini API key.*"""

        # ----------------------------------------------------------------------
        # Case B: 30-Day or Learning Roadmap Request
        # ----------------------------------------------------------------------
        if any(term in q_lower for term in ['roadmap', 'plan', '30-day', '30 day', 'schedule', 'guide']):
            return f"""### 30-Day Strategic Placement Preparation Roadmap

Hello **{name}**, tailored for your background in **{dept}** (Graduation Batch {student.get('batch_year')}):

#### Week 1: Core DSA Foundations & Problem-Solving
- **Focus**: Arrays, Strings, Two Pointers, Sliding Window, and HashMaps.
- **Daily Goal**: Solve 3-4 LeetCode / HackerRank problems (Medium difficulty).
- **Core Topics**: Big-O Analysis, Sorting & Searching algorithms.
- **Your Current Stack**: Leverage your existing knowledge of **{skills_str}**.

#### Week 2: Advanced Data Structures & CS Fundamentals
- **Focus**: Linked Lists, Stacks, Queues, Binary Trees, and Binary Search Trees.
- **Academic Review**: Operating Systems (Processes, Threads, Deadlocks), DBMS (SQL Joins, Normalization, ACID properties).
- **Milestone Project**: Build a small full-stack or API-driven project implementing authentication and database indexing.

#### Week 3: Dynamic Programming, Graphs & System Design
- **Focus**: Recursion, Backtracking, Graphs (BFS/DFS), and basic Dynamic Programming patterns.
- **System Design**: RESTful API design, database schema optimization, caching fundamentals.
- **Aptitude Routine**: 45 minutes daily on Quantitative Aptitude and Data Interpretation.

#### Week 4: Mock Interviews, Resume Polish & Company Revisions
- **Focus**: Timed mock coding assessments and behavioral interview practice (STAR technique).
- **Resume Check**: Ensure your uploaded PDF resume in the **Academic Vault** features verifiable project metrics.
- **Review**: Re-read company-specific interview archives in the [TPMS Preparation Resources](/study-materials/).

> *These are built-in suggestions based on your record. Live AI answers turn on when the placement office adds a Gemini API key.*"""

        # ----------------------------------------------------------------------
        # Case C: Skill-Gap Analysis & Role In-Demand Skills
        # ----------------------------------------------------------------------
        if any(term in q_lower for term in ['skill', 'learn', 'full stack', 'backend', 'frontend', 'demand', 'technology', 'stack']):
            return f"""### Personalized Skill-Gap Analysis for {name}

Based on your recorded profile in **{dept}** and current corporate hiring requirements at Apex Institute of Technology:

#### 1. Skills You Already Have (Profile Verified)
- **Documented Skills**: **{skills_str}**
- *Insight*: Having these fundamentals already recorded gives corporate recruiters immediate visibility during campus shortlist filtering.

#### 2. Skills to Deepen & Strengthen
- **Core Algorithms**: Deepen expertise in Trees, Graphs, and Dynamic Programming.
- **Database Architecture**: Master SQL indexing, query optimization, and transaction isolation levels.
- **System Design Principles**: Learn how scalable backends handle high concurrency and caching (Redis, Memcached).

#### 3. Recommended Skills to Learn Next
- **API Development & Microservices**: Build production-ready REST and GraphQL endpoints with Docker containerization.
- **Cloud & Deployment Basics**: Gain familiarity with AWS/GCP essentials (S3, EC2, Cloud Functions) and CI/CD pipelines.
- **Automated Testing**: Write unit and integration tests (e.g. pytest, Jest) to demonstrate production code quality.

#### 4. Actionable Next Steps
1. Update your skills in [Academic Vault & Resume](/student/profile/) so corporate cut-off filters reflect your latest competencies.
2. Explore available practice assets in [TPMS Preparation Resources](/study-materials/).

> *These are built-in suggestions based on your record. Live AI answers turn on when the placement office adds a Gemini API key.*"""

        # ----------------------------------------------------------------------
        # Case D: Resume Improvement
        # ----------------------------------------------------------------------
        if any(term in q_lower for term in ['resume', 'cv', 'profile']):
            has_resume = student.get('has_resume')
            resume_status = "Uploaded & Active" if has_resume else "No PDF resume currently attached"

            return f"""### Placement Resume Optimization Guide for {name}

- **Current Vault Status**: **{resume_status}** in your [Academic Vault](/student/profile/).

#### 1. Top Improvements for Campus Placement Resumes
1. **Use the Action + Metric + Result Formula**:
   - *Weak*: "Created an e-commerce website using Python and Django."
   - *Strong*: "Engineered a full-stack e-commerce portal in Django handling 500+ daily mock requests, reducing query latency by 35% through Redis caching."
2. **Prioritize Relevant Technical Skills**:
   - Highlight your verified competencies: **{skills_str}**.
   - Group skills into: Languages, Frameworks, Databases, Tools & Cloud.
3. **Keep to a Strict Single Page Format**:
   - Recruiters spend 6–10 seconds on initial screening. Use clean margins, readable typography, and bullet points.
4. **Highlight Academic Standing & Achievements**:
   - State your CGPA (**{cgpa} / 10.0**), academic branch (**{dept}**), and graduation year (**{student.get('batch_year')}**).

> *These are built-in suggestions based on your record. Live AI answers turn on when the placement office adds a Gemini API key.*"""

        # ----------------------------------------------------------------------
        # Case E: Default Personalized Guidance
        # ----------------------------------------------------------------------
        return f"""### Personalized Career & Placement Guidance for {name}

Hello **{name}**, welcome to the AI Career & Placement Assistant at Apex Institute of Technology!

Here is a summary of your current institutional placement profile:
- **Academic Branch**: {dept} ({student.get('department_code')})
- **Academic Standing**: CGPA **{cgpa} / 10.0** • Live Backlogs: **{backlogs}**
- **Recorded Skills**: {skills_str}
- **Placement Status**: {student.get('placement_status')}

#### How I Can Help You Today:
1. **Targeted Drive Preparation**: Ask *"What should I prepare for the Deloitte drive?"* or any active campus recruiter.
2. **Personalized Skill-Gap Analysis**: Ask *"What skills do I need to learn to become a Full Stack Developer?"*
3. **Structured Learning Roadmaps**: Ask *"Generate a 30-day coding and DSA interview preparation plan."*
4. **Resume Optimization**: Ask *"How can I improve my resume for high-paying campus drives?"*
5. **Study Material Recommendations**: Ask for direct links to aptitude, DSA, and technical interview resources stored in the [TPMS Preparation Library](/study-materials/).

What specific placement goal would you like to focus on right now?

> *These are built-in suggestions. Ask the placement office to add a Gemini API key for fuller answers.*"""
