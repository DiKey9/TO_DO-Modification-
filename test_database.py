import json
import os
import tempfile
import unittest

from database import Database, Task


class DatabaseTest(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.db_fd)
        self.json_path = tempfile.mktemp(suffix='.json')
        self.db = Database(db_name=self.db_path, json_backup=self.json_path)

    def tearDown(self):
        self.db.close()
        for path in [self.db_path, self.json_path]:
            if os.path.exists(path):
                os.remove(path)

    def test_add_update_complete_delete(self):
        task_id = self.db.add_task(
            'Тестовая задача',
            'Описание',
            'Высокий',
            '2026-06-30',
            project='Тест',
            tags='bug,urgent',
            estimate='2 ч',
        )
        task = self.db.get_task(task_id)
        self.assertIsNotNone(task)
        self.assertEqual(task.title, 'Тестовая задача')

        updated = self.db.update_task(
            task.id,
            'Тестовая задача 2',
            'Обновлённое описание',
            'Средний',
            'Отложена',
            '2026-07-01',
            'Тест',
            'bug',
            '3 ч',
        )
        self.assertTrue(updated)

        task = self.db.get_task(task_id)
        self.assertEqual(task.title, 'Тестовая задача 2')
        self.assertEqual(task.status, 'Отложена')

        completed = self.db.complete_task(task_id)
        self.assertTrue(completed)
        task = self.db.get_task(task_id)
        self.assertEqual(task.status, 'Выполнена')
        self.assertTrue(bool(task.completed_date))

        deleted = self.db.delete_task(task_id)
        self.assertTrue(deleted)
        self.assertIsNone(self.db.get_task(task_id))

    def test_unique_projects_and_tags(self):
        self.db.add_task('П1', '', 'Средний', '2026-07-01', project='A', tags='x,y')
        self.db.add_task('П2', '', 'Средний', '2026-07-02', project='B', tags='y,z')
        self.assertListEqual(self.db.get_unique_projects(), ['A', 'B'])
        self.assertListEqual(self.db.get_unique_tags(), ['x', 'y', 'z'])

    def test_export_import_json(self):
        export_path = tempfile.mktemp(suffix='.json')
        task_id = self.db.add_task('Экспорт', 'Импорт', 'Средний', '2026-07-05', project='P', tags='t1')
        self.db.export_to_json(export_path)
        self.db.delete_task(task_id)
        self.assertIsNone(self.db.get_task(task_id))

        self.db.import_from_json(export_path)
        restored_tasks = self.db.get_all_tasks()
        self.assertEqual(len(restored_tasks), 1)
        self.assertEqual(restored_tasks[0].title, 'Экспорт')
        if os.path.exists(export_path):
            os.remove(export_path)

    def test_date_range_filter(self):
        self.db.add_task('Летняя', '', 'Средний', '2026-07-10', project='P', tags='t')
        self.db.add_task('Осенняя', '', 'Средний', '2026-09-01', project='P', tags='t')
        summer_tasks = self.db.get_all_tasks(date_from='2026-07-01', date_to='2026-08-01')
        self.assertEqual(len(summer_tasks), 1)
        self.assertEqual(summer_tasks[0].title, 'Летняя')


if __name__ == '__main__':
    unittest.main()
