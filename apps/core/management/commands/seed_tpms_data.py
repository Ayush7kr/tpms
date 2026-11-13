import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import User, UserRole
from apps.departments.models import Department, AssistantDepartmentAssignment
from apps.companies.models import Company, CompanyTier
from apps.students.models import StudentProfile, PlacementStatus, Gender
from apps.placements.models import JobOpening, JobStatus, DepartmentJobApproval, ApprovalStatus
from apps.applications.models import JobApplication, ApplicationStage, VerificationStatus
from apps.study_materials.models import StudyMaterial, ResourceCategory, ResourceType
from apps.notifications.models import Notification
from apps.audit.models import AuditLog


class Command(BaseCommand):
    help = "Seeds the TPMS database with comprehensive, realistic institutional demonstration data."

    def handle(self, *args, **options):
        self.stdout.write("Initializing TPMS Demonstration Dataset...")

        # 1. Academic Departments
        departments_data = [
            ('CSE', 'Computer Science & Engineering', 'Software Systems, AI & Data Science'),
            ('IT', 'Information Technology', 'Enterprise Computing & Cloud Architecture'),
            ('ECE', 'Electronics & Communication Engineering', 'VLSI, Embedded Systems & Signal Processing'),
            ('MECH', 'Mechanical Engineering', 'Thermodynamics, Robotics & Manufacturing'),
            ('CIVIL', 'Civil Engineering', 'Structural Engineering & Infrastructure Systems'),
        ]

        depts = {}
        for code, name, desc in departments_data:
            dept, _ = Department.objects.get_or_create(
                code=code,
                defaults={'name': name, 'description': desc, 'is_active': True}
            )
            depts[code] = dept
        self.stdout.write(self.style.SUCCESS(f"Configured {len(depts)} Academic Departments."))

        # 2. Staff Accounts
        default_pwd = 'apex@123'

        staff_data = [
            ('admin@apex.edu.in', 'Vikram', 'Aditya', UserRole.ADMIN, '+91 98200 11001', True),
            ('principal@apex.edu.in', 'Dr. Ramesh', 'Kulkarni', UserRole.PRINCIPAL, '+91 98200 22002', False),
            ('tpo@apex.edu.in', 'Prof. Arvind', 'Deshmukh', UserRole.TNP_OFFICER, '+91 98200 33003', False),
            ('assistant.cse@apex.edu.in', 'Sunil', 'Patil', UserRole.TNP_ASSISTANT, '+91 98200 44004', False),
            ('assistant.ece@apex.edu.in', 'Meena', 'Nair', UserRole.TNP_ASSISTANT, '+91 98200 55005', False),
        ]

        staff_users = {}
        for email, fn, ln, role, phone, is_super in staff_data:
            user = User.objects.filter(email=email).first()
            if not user:
                user = User.objects.create_user(
                    email=email,
                    password=default_pwd,
                    first_name=fn,
                    last_name=ln,
                    role=role,
                    phone=phone,
                    is_staff=is_super,
                    is_superuser=is_super
                )
            staff_users[email] = user
        self.stdout.write(self.style.SUCCESS("Configured Staff Accounts (Admin, Principal, TPO, Assistants)."))

        # 3. Assistant Department Allocations
        AssistantDepartmentAssignment.objects.get_or_create(
            assistant=staff_users['assistant.cse@apex.edu.in'],
            department=depts['CSE'],
            defaults={'assigned_by': staff_users['admin@apex.edu.in']}
        )
        AssistantDepartmentAssignment.objects.get_or_create(
            assistant=staff_users['assistant.cse@apex.edu.in'],
            department=depts['IT'],
            defaults={'assigned_by': staff_users['admin@apex.edu.in']}
        )
        AssistantDepartmentAssignment.objects.get_or_create(
            assistant=staff_users['assistant.ece@apex.edu.in'],
            department=depts['ECE'],
            defaults={'assigned_by': staff_users['admin@apex.edu.in']}
        )
        self.stdout.write(self.style.SUCCESS("Allocated departments to TnP Assistants."))

        # 4. Corporate Recruiting Partners
        companies_data = [
            ('Google India', 'https://careers.google.com', 'Information Technology', CompanyTier.TIER_1_DREAM, 'Priya Nair', 'recruiter.india@google.com', '+91 80 6721 0000', 'Bengaluru, Karnataka'),
            ('Microsoft Corporation', 'https://careers.microsoft.com', 'Cloud & Software', CompanyTier.TIER_1_DREAM, 'Ravi Teja', 'university.hiring@microsoft.com', '+91 40 6608 0000', 'Hyderabad, Telangana'),
            ('Deloitte Consulting', 'https://deloitte.com/careers', 'Management & Tech Consulting', CompanyTier.TIER_2_CORE, 'Siddharth Roy', 'campus.deloitte@deloitte.com', '+91 22 6185 4000', 'Mumbai, Maharashtra'),
            ('Tata Consultancy Services', 'https://tcs.com/careers', 'IT Services', CompanyTier.TIER_3_MASS, 'Anjali Rao', 'campus.tcs@tcs.com', '+91 20 6608 7777', 'Pune, Maharashtra'),
            ('Infosys Limited', 'https://infosys.com/careers', 'IT Services', CompanyTier.TIER_3_MASS, 'Deepak Joshi', 'talent.infosys@infosys.com', '+91 80 2852 0261', 'Bengaluru, Karnataka'),
        ]

        companies = {}
        for name, web, sector, tier, cp, ce, cph, addr in companies_data:
            comp, _ = Company.objects.get_or_create(
                name=name,
                defaults={
                    'website': web, 'industry_sector': sector, 'tier': tier,
                    'contact_person': cp, 'contact_email': ce, 'contact_phone': cph,
                    'address': addr, 'is_active': True
                }
            )
            companies[name] = comp
        self.stdout.write(self.style.SUCCESS("Configured Corporate Recruiting Partners."))

        # 5. Students Dataset (20+ realistic profiles across CSE, IT, ECE, MECH)
        students_dataset = [
            # Top CSE Students
            ('aarav.mehta@apex.edu.in', 'Aarav', 'Mehta', '21CSE101', 'PRN21001', 'CSE', 'MALE', 2025, '88.50', '86.40', '8.85', 0, 'Python, Django, AWS, React, Algorithms', PlacementStatus.UNPLACED, None, None),
            ('diya.sen@apex.edu.in', 'Diya', 'Sen', '21CSE102', 'PRN21002', 'CSE', 'FEMALE', 2025, '91.20', '89.50', '7.40', 0, 'Java, Spring Boot, SQL, Machine Learning', PlacementStatus.UNPLACED, None, None),
            ('rohan.sharma@apex.edu.in', 'Rohan', 'Sharma', '21CSE103', 'PRN21003', 'CSE', 'MALE', 2025, '94.00', '92.50', '9.25', 0, 'C++, Distributed Systems, Go, Kubernetes', PlacementStatus.PLACED, 'Google India', '28.00'),
            ('ananya.iyer@apex.edu.in', 'Ananya', 'Iyer', '21CSE104', 'PRN21004', 'CSE', 'FEMALE', 2025, '82.00', '79.50', '7.85', 0, 'Full Stack Web, Node.js, PostgreSQL', PlacementStatus.UNPLACED, None, None),
            ('karan.kapoor@apex.edu.in', 'Karan', 'Kapoor', '21CSE105', 'PRN21005', 'CSE', 'MALE', 2025, '65.00', '62.00', '6.45', 1, 'HTML, CSS, JavaScript, Basic Python', PlacementStatus.UNPLACED, None, None),

            # IT Students
            ('sneha.patel@apex.edu.in', 'Sneha', 'Patel', '21IT201', 'PRN21006', 'IT', 'FEMALE', 2025, '89.00', '87.50', '8.90', 0, 'Cloud Infrastructure, Azure, Python, Docker', PlacementStatus.PLACED, 'Microsoft Corporation', '21.50'),
            ('varun.gupta@apex.edu.in', 'Varun', 'Gupta', '21IT202', 'PRN21007', 'IT', 'MALE', 2025, '78.50', '76.00', '7.60', 0, 'Cybersecurity, Linux, Python Scripting', PlacementStatus.UNPLACED, None, None),
            ('ishita.shukla@apex.edu.in', 'Ishita', 'Shukla', '21IT203', 'PRN21008', 'IT', 'FEMALE', 2025, '84.00', '82.00', '8.15', 0, 'React, TypeScript, GraphQL, Django', PlacementStatus.PLACED, 'Deloitte Consulting', '11.20'),

            # ECE Students
            ('arjun.reddy@apex.edu.in', 'Arjun', 'Reddy', '21ECE301', 'PRN21009', 'ECE', 'MALE', 2025, '86.00', '84.00', '8.30', 0, 'Embedded C, ARM Cortex, IoT, Python', PlacementStatus.UNPLACED, None, None),
            ('pooja.nair@apex.edu.in', 'Pooja', 'Nair', '21ECE302', 'PRN21010', 'ECE', 'FEMALE', 2025, '79.00', '78.00', '7.70', 0, 'MATLAB, Signal Processing, C++', PlacementStatus.PLACED, 'Tata Consultancy Services', '7.00'),
            ('karthik.s@apex.edu.in', 'Karthik', 'Subramaniam', '21ECE303', 'PRN21011', 'ECE', 'MALE', 2025, '72.00', '70.00', '6.90', 1, 'Microcontrollers, Verilog, Circuit Design', PlacementStatus.UNPLACED, None, None),

            # MECH Students
            ('vikram.singh@apex.edu.in', 'Vikram', 'Singh', '21ME401', 'PRN21012', 'MECH', 'MALE', 2025, '75.00', '72.00', '7.20', 0, 'AutoCAD, SolidWorks, Finite Element Analysis', PlacementStatus.UNPLACED, None, None),
            ('rahul.deshmukh@apex.edu.in', 'Rahul', 'Deshmukh', '21ME402', 'PRN21013', 'MECH', 'MALE', 2025, '81.00', '79.00', '7.95', 0, 'Robotics, Thermal Engineering, Python', PlacementStatus.PLACED, 'Tata Consultancy Services', '7.00'),
            ('amit.joshi@apex.edu.in', 'Amit', 'Joshi', '21ME403', 'PRN21014', 'MECH', 'MALE', 2025, '62.00', '60.00', '5.90', 2, 'Manufacturing, Operations', PlacementStatus.UNPLACED, None, None),
        ]

        student_profiles = {}
        for semail, sfn, sln, roll, prn, dcode, gender, batch, tenth, twl, cgpa, backlogs, skills, pstatus, pcomp_name, pkg in students_dataset:
            suser = User.objects.filter(email=semail).first()
            if not suser:
                suser = User.objects.create_user(
                    email=semail,
                    password=default_pwd,
                    first_name=sfn,
                    last_name=sln,
                    role=UserRole.STUDENT,
                    phone='+91 98700 00000'
                )

            pcomp = companies.get(pcomp_name) if pcomp_name else None
            pkg_dec = Decimal(pkg) if pkg else None

            profile, _ = StudentProfile.objects.update_or_create(
                user=suser,
                defaults={
                    'department': depts[dcode],
                    'roll_number': roll,
                    'prn_number': prn,
                    'gender': gender,
                    'batch_year': batch,
                    'degree': 'B.Tech',
                    'tenth_percentage': Decimal(tenth),
                    'twelfth_percentage': Decimal(twl),
                    'graduation_cgpa': Decimal(cgpa),
                    'active_backlogs': backlogs,
                    'skills': skills,
                    'placement_status': pstatus,
                    'placed_company': pcomp,
                    'salary_package': pkg_dec
                }
            )
            student_profiles[roll] = profile
        self.stdout.write(self.style.SUCCESS(f"Configured {len(student_profiles)} Student Academic Profiles."))

        # 6. Placement Drives (Job Openings)
        now = timezone.now()
        deadline_active = now + datetime.timedelta(days=14)
        drive_date_1 = now.date() + datetime.timedelta(days=21)

        drives_data = [
            (
                companies['Google India'],
                'Software Development Engineer - 1',
                'Design, build, and maintain mission-critical cloud infrastructure and distributed consumer systems. Strong foundations in data structures, algorithms, and object-oriented architecture required.',
                'Bengaluru, Karnataka',
                Decimal('28.00'),
                'No bond agreement',
                Decimal('80.00'), Decimal('80.00'), Decimal('8.00'), 0,
                ['CSE', 'IT'],
                deadline_active, drive_date_1, JobStatus.PUBLISHED
            ),
            (
                companies['Microsoft Corporation'],
                'Cloud Solution Architect',
                'Engage enterprise customers to architect, modernize, and migrate mission-critical applications to Microsoft Azure. Collaborate with engineering on scalable cloud-native architectures.',
                'Hyderabad, Telangana',
                Decimal('21.50'),
                'No bond agreement',
                Decimal('75.00'), Decimal('75.00'), Decimal('7.50'), 0,
                ['CSE', 'IT', 'ECE'],
                deadline_active, drive_date_1, JobStatus.PUBLISHED
            ),
            (
                companies['Deloitte Consulting'],
                'Associate Technology Consultant',
                'Consulting engagements spanning digital transformation, enterprise cloud adoption, ERP solutions, and business data analytics for Fortune 500 clients.',
                'Mumbai / Pune',
                Decimal('11.20'),
                '1 Year Service Agreement',
                Decimal('65.00'), Decimal('65.00'), Decimal('6.50'), 0,
                ['CSE', 'IT', 'ECE', 'MECH'],
                deadline_active, drive_date_1, JobStatus.PUBLISHED
            ),
            (
                companies['Tata Consultancy Services'],
                'Digital & Ninja Trainee Engineer',
                'Global consulting and technology projects across agile software engineering, legacy modernization, full-stack development, and test automation.',
                'Multiple Locations',
                Decimal('7.00'),
                '1 Year Service Agreement',
                Decimal('60.00'), Decimal('60.00'), Decimal('6.00'), 1,
                ['CSE', 'IT', 'ECE', 'MECH', 'CIVIL'],
                deadline_active, drive_date_1, JobStatus.PUBLISHED
            ),
        ]

        jobs = []
        for comp, title, desc, loc, pkg, bond, min10, min12, mincgpa, maxback, dept_codes, dline, ddate, status in drives_data:
            job, _ = JobOpening.objects.update_or_create(
                company=comp,
                title=title,
                defaults={
                    'role_description': desc,
                    'job_location': loc,
                    'package_ctc': pkg,
                    'bond_details': bond,
                    'min_tenth_percentage': min10,
                    'min_twelfth_percentage': min12,
                    'min_graduation_cgpa': mincgpa,
                    'max_active_backlogs': maxback,
                    'allowed_degrees': 'B.Tech',
                    'allowed_batches': '2025,2026',
                    'application_deadline': dline,
                    'drive_date': ddate,
                    'status': status,
                    'created_by': staff_users['tpo@apex.edu.in']
                }
            )
            # Link departments
            dept_objs = [depts[c] for c in dept_codes]
            job.allowed_departments.set(dept_objs)

            # Department Approvals
            for d in dept_objs:
                DepartmentJobApproval.objects.get_or_create(
                    job_opening=job,
                    department=d,
                    defaults={
                        'status': ApprovalStatus.APPROVED,
                        'reviewed_by': staff_users['assistant.cse@apex.edu.in'],
                        'reviewed_at': now
                    }
                )
            jobs.append(job)
        self.stdout.write(self.style.SUCCESS(f"Configured {len(jobs)} Active Campus Drives with Department Approvals."))

        # 7. Student Applications across recruitment rounds
        apps_data = [
            (jobs[0], student_profiles['21CSE103'], ApplicationStage.OFFERED, VerificationStatus.VERIFIED, "Cleared Google interview rounds with highest recommendations."),
            (jobs[0], student_profiles['21CSE101'], ApplicationStage.TECHNICAL_ROUND, VerificationStatus.VERIFIED, "Cleared Online Assessment (95/100). Technical round scheduled."),
            (jobs[0], student_profiles['21IT201'], ApplicationStage.SHORTLISTED, VerificationStatus.VERIFIED, "Resume shortlisted by Google recruiter."),
            (jobs[1], student_profiles['21IT201'], ApplicationStage.OFFERED, VerificationStatus.VERIFIED, "Selected for Cloud Solutions Architect position."),
            (jobs[1], student_profiles['21CSE101'], ApplicationStage.ASSESSMENT, VerificationStatus.VERIFIED, "Invited for online coding evaluation."),
            (jobs[2], student_profiles['21IT203'], ApplicationStage.OFFERED, VerificationStatus.VERIFIED, "Offered Technology Consultant role."),
            (jobs[3], student_profiles['21ECE302'], ApplicationStage.OFFERED, VerificationStatus.VERIFIED, "Selected in TCS Digital drive."),
            (jobs[3], student_profiles['21ME402'], ApplicationStage.OFFERED, VerificationStatus.VERIFIED, "Selected in TCS Ninja drive."),
        ]

        for job, student, stage, vstatus, remarks in apps_data:
            JobApplication.objects.update_or_create(
                job_opening=job,
                student=student,
                defaults={
                    'stage': stage,
                    'verification_status': vstatus,
                    'remarks': remarks,
                    'verified_by': staff_users['assistant.cse@apex.edu.in']
                }
            )
        self.stdout.write(self.style.SUCCESS("Configured Student Job Applications across stages."))

        # 8. Study Materials
        materials_data = [
            ('Quantitative Aptitude & Logical Reasoning Master Handbook', 'Comprehensive formula booklet and 500+ solved practice questions for TCS NQT, Deloitte, and AMCAT.', ResourceCategory.APTITUDE, ResourceType.EXTERNAL_URL, 'https://drive.google.com/sample_aptitude_guide.pdf', None, None),
            ('Data Structures & Algorithms in Python & C++', 'LeetCode top 150 interview patterns with complete annotated solutions and complexity proofs.', ResourceCategory.TECHNICAL_CODING, ResourceType.EXTERNAL_URL, 'https://github.com/apex-tpms/dsa-interview-patterns', None, jobs[0]),
            ('System Design & Cloud Architecture Video Series', '10-part video masterclass on distributed systems, caching strategies, and REST API design.', ResourceCategory.TECHNICAL_CODING, ResourceType.VIDEO_LINK, 'https://youtube.com/playlist?list=sample_system_design', None, jobs[1]),
            ('HR & Behavioral Interview Competency Guide', 'STAR technique breakdown, standard behavioral interview questions, and salary negotiation tactics.', ResourceCategory.HR_INTERVIEW, ResourceType.EXTERNAL_URL, 'https://apex.edu.in/resources/hr_interview_guide.pdf', None, None),
        ]

        for title, desc, cat, rtype, url, dept, job in materials_data:
            StudyMaterial.objects.get_or_create(
                title=title,
                defaults={
                    'description': desc,
                    'category': cat,
                    'resource_type': rtype,
                    'external_url': url,
                    'department': dept,
                    'job_opening': job,
                    'uploaded_by': staff_users['tpo@apex.edu.in']
                }
            )
        self.stdout.write(self.style.SUCCESS("Configured Study & Preparation Resources."))

        # 9. In-App Notifications
        Notification.objects.get_or_create(
            recipient=student_profiles['21CSE101'].user,
            title="Google Drive: Technical Round Scheduled",
            defaults={
                'message': "Your technical round interview with Google India has been scheduled for tomorrow at 11:00 AM IST.",
                'action_url': "/student/applications/",
                'is_read': False
            }
        )
        Notification.objects.get_or_create(
            recipient=student_profiles['21CSE103'].user,
            title="🎉 Official Offer Letter: Google India",
            defaults={
                'message': "Congratulations! Your offer letter for Software Development Engineer - 1 (28.00 LPA) has been released.",
                'action_url': "/student/profile/",
                'is_read': False
            }
        )
        Notification.objects.get_or_create(
            recipient=staff_users['assistant.cse@apex.edu.in'],
            title="New Student Applications Pending Verification",
            defaults={
                'message': "3 students from Computer Science have applied to the Google campus drive. Please verify their marks.",
                'action_url': "/assistant/verify/",
                'is_read': False
            }
        )
        self.stdout.write(self.style.SUCCESS("Configured In-App Notifications."))

        # 10. Audit Logs
        AuditLog.objects.create(
            user=staff_users['admin@apex.edu.in'],
            action="SYSTEM_INIT_SEED",
            entity_type="System",
            details="Seeded complete demonstration dataset for Apex Institute of Technology."
        )

        self.stdout.write(self.style.SUCCESS("TPMS Database successfully seeded with 100% production-realistic data!"))
