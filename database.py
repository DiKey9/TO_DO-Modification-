import sqlite3
from datetime import datetime
import json
import os

class Database:
    def __init__(self, db_name="tasks.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()
        # При старте загружаем данные из JSON, если файл существует
        self.load_from_json()
    
    def create_table(self):
        """Создание таблицы задач, если она не существует"""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT DEFAULT 'Средний',
                status TEXT DEFAULT 'Активна',
                created_date TEXT NOT NULL,
                due_date TEXT,
                completed_date TEXT
            )
        ''')
        self.conn.commit()
    
    def add_task(self, title, description, priority, due_date):
        """Добавление новой задачи"""
        created_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.cursor.execute('''
            INSERT INTO tasks (title, description, priority, due_date, created_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, description, priority, due_date, created_date))
        self.conn.commit()
        rowid = self.cursor.lastrowid
        # Сохраняем текущее состояние в JSON
        try:
            self.export_to_json()
        except Exception:
            pass
        return rowid
    
    def get_all_tasks(self, status_filter="Все", sort_by=None):
        """Получение всех задач с возможностью фильтрации по статусу и сортировки."""
        return self.get_all_tasks_with_sort(status_filter, sort_by=sort_by)

    def get_all_tasks_with_sort(self, status_filter="Все", sort_by=None):
        """Получение всех задач с возможностью фильтрации по статусу и сортировки.
        sort_by: None | 'due' | 'priority' | 'status'
        """
        base = '''
            SELECT id, title, description, priority, status,
                   created_date, due_date, completed_date
            FROM tasks
        '''

        params = []
        where = ''
        if status_filter != "Все":
            where = 'WHERE status = ?'
            params.append(status_filter)

        # Определяем ORDER BY в зависимости от sort_by
        if sort_by == 'due':
            order = "ORDER BY (due_date IS NULL), date(due_date) ASC"
        elif sort_by == 'priority':
            order = ("ORDER BY CASE priority WHEN 'Высокий' THEN 1 WHEN 'Средний' THEN 2 "
                     "WHEN 'Низкий' THEN 3 ELSE 4 END, date(due_date) ASC")
        elif sort_by == 'status':
            order = ("ORDER BY CASE status WHEN 'Активна' THEN 1 WHEN 'Выполнена' THEN 2 ELSE 3 END, "
                     "CASE priority WHEN 'Высокий' THEN 1 WHEN 'Средний' THEN 2 WHEN 'Низкий' THEN 3 ELSE 4 END")
        else:
            order = ("ORDER BY CASE priority WHEN 'Высокий' THEN 1 WHEN 'Средний' THEN 2 "
                     "WHEN 'Низкий' THEN 3 ELSE 4 END, (due_date IS NULL), date(due_date) ASC")

        query = ' '.join([base, where, order])
        if params:
            self.cursor.execute(query, tuple(params))
        else:
            self.cursor.execute(query)
        return self.cursor.fetchall()
    
    def complete_task(self, task_id):
        """Отметить задачу как выполненную"""
        completed_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.cursor.execute('''
            UPDATE tasks 
            SET status = 'Выполнена', completed_date = ? 
            WHERE id = ?
        ''', (completed_date, task_id))
        self.conn.commit()
        updated = self.cursor.rowcount > 0
        if updated:
            try:
                self.export_to_json()
            except Exception:
                pass
        return updated
    
    def delete_task(self, task_id):
        """Удаление задачи"""
        self.cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.conn.commit()
        deleted = self.cursor.rowcount > 0
        if deleted:
            try:
                self.export_to_json()
            except Exception:
                pass
        return deleted
    
    def update_task(self, task_id, title, description, priority, due_date):
        """Обновление задачи"""
        self.cursor.execute('''
            UPDATE tasks 
            SET title = ?, description = ?, priority = ?, due_date = ?
            WHERE id = ?
        ''', (title, description, priority, due_date, task_id))
        self.conn.commit()
        updated = self.cursor.rowcount > 0
        if updated:
            try:
                self.export_to_json()
            except Exception:
                pass
        return updated

    def export_to_json(self, file_path="tasks.js"):
        """Экспорт всех задач в JSON-файл (file_path)"""
        rows = self.get_all_tasks("Все")
        tasks = []
        for row in rows:
            tasks.append({
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'priority': row[3],
                'status': row[4],
                'created_date': row[5],
                'due_date': row[6],
                'completed_date': row[7],
            })
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)

    def load_from_json(self, file_path="tasks.js"):
        """Загрузка задач из JSON-файла при старте (перезаписывает таблицу)"""
        if not os.path.exists(file_path):
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            return

        if not isinstance(data, list):
            return

        # Перезаписываем таблицу задач данными из JSON
        self.cursor.execute("DELETE FROM tasks")
        for task in data:
            self.cursor.execute('''
                INSERT INTO tasks (id, title, description, priority, status, created_date, due_date, completed_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task.get('id'),
                task.get('title'),
                task.get('description'),
                task.get('priority'),
                task.get('status') or 'Активна',
                task.get('created_date') or datetime.now().strftime("%Y-%m-%d %H:%M"),
                task.get('due_date'),
                task.get('completed_date')
            ))
        self.conn.commit()

        # Поддержка корректной autoincrement последовательности
        try:
            max_id = max((t.get('id') or 0) for t in data) if data else 0
            if max_id:
                self.cursor.execute("UPDATE sqlite_sequence SET seq = ? WHERE name = 'tasks'", (max_id,))
                self.conn.commit()
        except Exception:
            pass
    
    def search_tasks(self, search_term, sort_by=None):
        """Поиск задач по названию или описанию с поддержкой сортировки"""
        return self.search_tasks_with_sort(search_term, sort_by=sort_by)

    def search_tasks_with_sort(self, search_term, sort_by=None):
        """Поиск задач с поддержкой сортировки"""
        base = '''
            SELECT id, title, description, priority, status,
                   created_date, due_date, completed_date
            FROM tasks
            WHERE title LIKE ? OR description LIKE ?
        '''
        params = [f'%{search_term}%', f'%{search_term}%']

        if sort_by == 'due':
            order = "ORDER BY (due_date IS NULL), date(due_date) ASC"
        elif sort_by == 'priority':
            order = ("ORDER BY CASE priority WHEN 'Высокий' THEN 1 WHEN 'Средний' THEN 2 "
                     "WHEN 'Низкий' THEN 3 ELSE 4 END, date(due_date) ASC")
        elif sort_by == 'status':
            order = ("ORDER BY CASE status WHEN 'Активна' THEN 1 WHEN 'Выполнена' THEN 2 ELSE 3 END, "
                     "CASE priority WHEN 'Высокий' THEN 1 WHEN 'Средний' THEN 2 WHEN 'Низкий' THEN 3 ELSE 4 END")
        else:
            order = ("ORDER BY CASE priority WHEN 'Высокий' THEN 1 WHEN 'Средний' THEN 2 "
                     "WHEN 'Низкий' THEN 3 ELSE 4 END, (due_date IS NULL), date(due_date) ASC")

        query = ' '.join([base, order])
        self.cursor.execute(query, tuple(params))
        return self.cursor.fetchall()
    
    def get_statistics(self):
        """Получение статистики по задачам"""
        self.cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'Активна' THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN status = 'Выполнена' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN priority = 'Высокий' AND status = 'Активна' THEN 1 ELSE 0 END) as high_priority,
                SUM(CASE WHEN date(due_date) < date('now') AND status = 'Активна' THEN 1 ELSE 0 END) as overdue
            FROM tasks
        ''')
        stats = self.cursor.fetchone()
        return {
            'total': stats[0] or 0,
            'active': stats[1] or 0,
            'completed': stats[2] or 0,
            'high_priority': stats[3] or 0,
            'overdue': stats[4] or 0
        }
    
    def close(self):
        """Закрытие соединения с базой данных"""
        self.conn.close()