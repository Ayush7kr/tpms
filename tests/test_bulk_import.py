import io
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.accounts.models import User
from apps.departments.models import Department
from apps.students.models import StudentProfile
from apps.students.services.bulk_import import BulkStudentImportService


class BulkImportTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(code='CSE', name='Computer Science')

    def test_csv_ingestion_creates_students(self):
        """CSV bulk import successfully parses records and creates User and Profile instances."""
        csv_content = (
            "roll_number,prn_number,first_name,last_name,email,phone,gender,batch_year,degree,tenth_percentage,twelfth_percentage,graduation_cgpa,active_backlogs,skills\n"
            "21CSE801,PRN801,Amit,Verma,amit.v@apex.edu.in,9800000001,MALE,2025,B.Tech,85.00,82.00,8.20,0,Python\n"
            "21CSE802,PRN802,Pooja,Deshmukh,pooja.d@apex.edu.in,9800000002,FEMALE,2025,B.Tech,90.00,88.00,8.90,0,Java\n"
        )
        csv_file = SimpleUploadedFile("students.csv", csv_content.encode('utf-8'), content_type="text/csv")

        result = BulkStudentImportService.parse_file(csv_file, department=self.dept)
        self.assertTrue(result['success'])
        self.assertEqual(result['created_count'], 2)
        self.assertEqual(result['skipped_count'], 0)

        self.assertTrue(User.objects.filter(email='amit.v@apex.edu.in').exists())
        self.assertTrue(StudentProfile.objects.filter(roll_number='21CSE801').exists())

    def test_duplicate_records_skipped(self):
        """Duplicate emails or roll numbers must be skipped without crashing the transaction."""
        csv_content_1 = (
            "roll_number,prn_number,first_name,last_name,email,phone,gender,batch_year,degree,tenth_percentage,twelfth_percentage,graduation_cgpa,active_backlogs,skills\n"
            "21CSE803,PRN803,Rahul,Kumar,rahul.k@apex.edu.in,9800000003,MALE,2025,B.Tech,80.00,78.00,7.80,0,C++\n"
        )
        csv_file_1 = SimpleUploadedFile("students1.csv", csv_content_1.encode('utf-8'), content_type="text/csv")
        result1 = BulkStudentImportService.parse_file(csv_file_1, department=self.dept)
        self.assertEqual(result1['created_count'], 1)

        # Upload duplicate
        csv_file_2 = SimpleUploadedFile("students2.csv", csv_content_1.encode('utf-8'), content_type="text/csv")
        result2 = BulkStudentImportService.parse_file(csv_file_2, department=self.dept)
        self.assertTrue(result2['success'])
        self.assertEqual(result2['created_count'], 0)
        self.assertEqual(result2['skipped_count'], 1)
