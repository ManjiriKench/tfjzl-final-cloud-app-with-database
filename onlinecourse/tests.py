import os
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from onlinecourse.models import Course, Lesson, Question, Choice, Submission, Enrollment


class ExamFlowTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='learner1', password='testpassword', first_name='Learner')
        self.course = Course.objects.create(name='Django Cloud Course', description='Test Course Description')
        self.lesson = Lesson.objects.create(title='Intro to Django', order=0, course=self.course, content='Lesson content')
        
        # Question 1: Single choice correct
        self.q1 = Question.objects.create(course=self.course, question_text='Is Django a Python framework?', question_point=50)
        self.q1.lessons.add(self.lesson)
        self.c1_1 = Choice.objects.create(question=self.q1, choice_text='Yes', is_correct=True)
        self.c1_2 = Choice.objects.create(question=self.q1, choice_text='No', is_correct=False)
        
        # Question 2: Multi-choice question
        self.q2 = Question.objects.create(course=self.course, question_text='Which are Python web frameworks?', question_point=50)
        self.q2.lessons.add(self.lesson)
        self.c2_1 = Choice.objects.create(question=self.q2, choice_text='Django', is_correct=True)
        self.c2_2 = Choice.objects.create(question=self.q2, choice_text='Flask', is_correct=True)
        self.c2_3 = Choice.objects.create(question=self.q2, choice_text='React', is_correct=False)

    def test_model_fields_and_properties(self):
        # Test question_point and grade compatibility
        self.assertEqual(self.q1.question_point, 50)
        self.assertEqual(self.q1.grade, 50)
        self.q1.grade = 40
        self.assertEqual(self.q1.question_point, 40)
        self.q1.grade = 50

        # Test string representations
        self.assertIn('Django Cloud Course', str(self.course))
        self.assertEqual(str(self.lesson), 'Intro to Django')
        self.assertIn('Is Django a Python framework?', str(self.q1))
        self.assertEqual(str(self.c1_1), 'Yes')

    def test_is_get_score_logic(self):
        # Exact match
        self.assertTrue(self.q1.is_get_score([self.c1_1.id]))
        self.assertTrue(self.q1.is_get_grade([self.c1_1.id]))
        # Wrong choice selected
        self.assertFalse(self.q1.is_get_score([self.c1_2.id]))
        # Multi-choice question tests
        self.assertTrue(self.q2.is_get_score([self.c2_1.id, self.c2_2.id]))
        # Incomplete correct choices
        self.assertFalse(self.q2.is_get_score([self.c2_1.id]))
        # Includes a wrong choice
        self.assertFalse(self.q2.is_get_score([self.c2_1.id, self.c2_2.id, self.c2_3.id]))

    def test_exam_submission_and_result_flow(self):
        self.client.login(username='learner1', password='testpassword')
        
        # Submit correct answers
        post_data = {
            f'choice_{self.c1_1.id}': str(self.c1_1.id),
            f'choice_{self.c2_1.id}': str(self.c2_1.id),
            f'choice_{self.c2_2.id}': str(self.c2_2.id),
        }
        submit_url = reverse('onlinecourse:submit', args=[self.course.id])
        response = self.client.post(submit_url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['grade'], 100)
        self.assertContains(response, 'Congratulations')
        self.assertContains(response, '100/100')

    def test_exam_failure_result(self):
        self.client.login(username='learner1', password='testpassword')
        
        # Submit wrong answers
        post_data = {
            f'choice_{self.c1_2.id}': str(self.c1_2.id),
            f'choice_{self.c2_3.id}': str(self.c2_3.id),
        }
        submit_url = reverse('onlinecourse:submit', args=[self.course.id])
        response = self.client.post(submit_url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['grade'], 0)
        self.assertContains(response, 'Sorry')

    def test_root_files_synchronization(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        synced_pairs = [
            (os.path.join(base_dir, 'models.py'), os.path.join(base_dir, 'onlinecourse', 'models.py')),
            (os.path.join(base_dir, 'admin.py'), os.path.join(base_dir, 'onlinecourse', 'admin.py')),
            (os.path.join(base_dir, 'views.py'), os.path.join(base_dir, 'onlinecourse', 'views.py')),
            (os.path.join(base_dir, 'urls.py'), os.path.join(base_dir, 'onlinecourse', 'urls.py')),
            (os.path.join(base_dir, 'course_details_bootstrap.html'), 
             os.path.join(base_dir, 'onlinecourse', 'templates', 'onlinecourse', 'course_details_bootstrap.html')),
        ]
        for root_file, app_file in synced_pairs:
            self.assertTrue(os.path.exists(root_file), f'{root_file} does not exist')
            self.assertTrue(os.path.exists(app_file), f'{app_file} does not exist')
            with open(root_file, 'r', encoding='utf-8') as f1, open(app_file, 'r', encoding='utf-8') as f2:
                self.assertEqual(f1.read(), f2.read(), f'{root_file} and {app_file} have diverged!')
