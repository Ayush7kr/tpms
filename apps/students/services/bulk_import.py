import csv
import io
from decimal import Decimal, InvalidOperation
from django.db import transaction
from apps.accounts.models import User, UserRole
from apps.students.models import StudentProfile, Gender, PlacementStatus
from apps.departments.models import Department
import openpyxl


class BulkStudentImportService:
    @staticmethod
    def parse_file(uploaded_file, department, default_password='apex@123'):
        """
        Parses CSV or Excel (.xlsx) file and creates student accounts and profiles atomically.
        Strictly scopes student ingestion to the specified department.
        """
        # File size guard (Max 15MB)
        if hasattr(uploaded_file, 'size') and uploaded_file.size > 15 * 1024 * 1024:
            return {
                'success': False,
                'error': 'Uploaded file exceeds the maximum 15MB size limit.',
                'created_count': 0,
                'skipped_count': 0,
                'errors': ['File size exceeds 15MB threshold.']
            }

        filename = uploaded_file.name.lower()
        if filename.endswith('.csv'):
            return BulkStudentImportService._process_csv(uploaded_file, department, default_password)
        elif filename.endswith('.xlsx'):
            return BulkStudentImportService._process_excel(uploaded_file, department, default_password)
        else:
            return {
                'success': False,
                'error': 'Unsupported file format. Please upload a .csv or .xlsx file.',
                'created_count': 0,
                'errors': ['Only CSV and Excel (.xlsx) formats are accepted.']
            }

    @staticmethod
    def _process_csv(uploaded_file, department, default_password):
        try:
            content = uploaded_file.read().decode('utf-8-sig', errors='replace')
            reader = csv.DictReader(io.StringIO(content))
            return BulkStudentImportService._ingest_rows(reader, department, default_password)
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to read CSV: {str(e)}",
                'created_count': 0,
                'errors': [str(e)]
            }

    @staticmethod
    def _process_excel(uploaded_file, department, default_password):
        try:
            wb = openpyxl.load_workbook(uploaded_file, data_only=True)
            sheet = wb.active
            headers = [str(cell.value).strip().lower() if cell.value is not None else '' for cell in sheet[1]]

            rows = []
            for row in sheet.iter_rows(min_row=2, values_only=True):
                if not any(row):
                    continue
                row_dict = {}
                for idx, header in enumerate(headers):
                    if header and idx < len(row):
                        val = row[idx]
                        row_dict[header] = str(val).strip() if val is not None else ''
                rows.append(row_dict)

            return BulkStudentImportService._ingest_rows(rows, department, default_password)
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to read Excel workbook: {str(e)}",
                'created_count': 0,
                'errors': [str(e)]
            }

    @staticmethod
    def _ingest_rows(rows, department, default_password):
        created_count = 0
        skipped_count = 0
        errors = []

        with transaction.atomic():
            for idx, row in enumerate(rows, start=2):
                # Normalize keys (strip whitespace, lower)
                clean_row = {k.strip().lower(): v.strip() if isinstance(v, str) else v for k, v in row.items() if k}

                roll = str(clean_row.get('roll_number', clean_row.get('roll', ''))).strip().upper()
                prn = str(clean_row.get('prn_number', clean_row.get('prn', ''))).strip().upper()
                first_name = str(clean_row.get('first_name', clean_row.get('firstname', ''))).strip()
                last_name = str(clean_row.get('last_name', clean_row.get('lastname', ''))).strip()
                email = str(clean_row.get('email', '')).strip().lower()
                phone = str(clean_row.get('phone', clean_row.get('mobile', ''))).strip()
                gender_str = str(clean_row.get('gender', 'MALE')).strip().upper()
                batch_year_str = str(clean_row.get('batch_year', clean_row.get('batch', '2025'))).strip()
                degree = str(clean_row.get('degree', 'B.Tech')).strip()
                tenth_str = str(clean_row.get('tenth_percentage', clean_row.get('10th', '0.0'))).strip()
                twelfth_str = str(clean_row.get('twelfth_percentage', clean_row.get('12th', '0.0'))).strip()
                cgpa_str = str(clean_row.get('graduation_cgpa', clean_row.get('cgpa', '0.0'))).strip()
                backlogs_str = str(clean_row.get('active_backlogs', clean_row.get('backlogs', '0'))).strip()
                skills = str(clean_row.get('skills', '')).strip()

                if not roll or not email:
                    errors.append(f"Row {idx}: Missing mandatory roll_number or email.")
                    continue

                # Check duplicates
                if User.objects.filter(email=email).exists():
                    skipped_count += 1
                    continue
                if StudentProfile.objects.filter(roll_number=roll).exists():
                    skipped_count += 1
                    continue

                if not prn:
                    prn = f"PRN{roll}"

                if StudentProfile.objects.filter(prn_number=prn).exists():
                    skipped_count += 1
                    continue

                # Parse numbers
                try:
                    tenth = Decimal(tenth_str)
                    twelfth = Decimal(twelfth_str)
                    cgpa = Decimal(cgpa_str)
                    backlogs = int(backlogs_str)
                    batch_year = int(batch_year_str)
                except (InvalidOperation, ValueError):
                    errors.append(f"Row {idx} ({roll}): Numeric conversion error in percentage/CGPA/backlogs.")
                    continue

                # Range boundaries validation
                if not (Decimal('0.0') <= tenth <= Decimal('100.0')):
                    errors.append(f"Row {idx} ({roll}): 10th percentage must be between 0 and 100 (got {tenth}).")
                    continue
                if not (Decimal('0.0') <= twelfth <= Decimal('100.0')):
                    errors.append(f"Row {idx} ({roll}): 12th percentage must be between 0 and 100 (got {twelfth}).")
                    continue
                if not (Decimal('0.0') <= cgpa <= Decimal('10.0')):
                    errors.append(f"Row {idx} ({roll}): CGPA must be between 0.0 and 10.0 (got {cgpa}).")
                    continue
                if backlogs < 0:
                    errors.append(f"Row {idx} ({roll}): Active backlogs cannot be negative.")
                    continue

                gender = Gender.MALE
                if 'FEMALE' in gender_str:
                    gender = Gender.FEMALE
                elif 'OTHER' in gender_str:
                    gender = Gender.OTHER

                # Create user
                user = User.objects.create_user(
                    email=email,
                    password=default_password,
                    first_name=first_name or "Student",
                    last_name=last_name or roll,
                    role=UserRole.STUDENT,
                    phone=phone
                )

                # Create profile
                StudentProfile.objects.create(
                    user=user,
                    department=department,
                    roll_number=roll,
                    prn_number=prn,
                    gender=gender,
                    batch_year=batch_year,
                    degree=degree or 'B.Tech',
                    tenth_percentage=tenth,
                    twelfth_percentage=twelfth,
                    graduation_cgpa=cgpa,
                    active_backlogs=backlogs,
                    skills=skills,
                    placement_status=PlacementStatus.UNPLACED
                )
                created_count += 1

        if created_count == 0 and skipped_count == 0 and not errors:
            return {
                'success': False,
                'error': 'The uploaded file is empty or contains no valid candidate data rows.',
                'created_count': 0,
                'skipped_count': 0,
                'errors': ['No candidate records found in file.']
            }

        return {
            'success': True,
            'created_count': created_count,
            'skipped_count': skipped_count,
            'errors': errors
        }
