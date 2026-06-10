import sqlite3
from datetime import datetime

class Database:
    def __init__(self, db_name="tasks.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()
    
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
        return self.cursor.lastrowid
    
    def get_all_tasks(self, status_filter="Все"):
        """Получение всех задач с возможностью фильтрации по статусу"""
        if status_filter == "Все":
            self.cursor.execute('''
                SELECT id, title, description, priority, status, 
                       created_date, due_date, completed_date 
                FROM tasks ORDER BY 
                    CASE priority 
                        WHEN 'Высокий' THEN 1
                        WHEN 'Средний' THEN 2
                        WHEN 'Низкий' THEN 3
                    END, due_date
            ''')
        else:
            self.cursor.execute('''
                SELECT id, title, description, priority, status, 
                       created_date, due_date, completed_date 
                FROM tasks WHERE status = ? 
                ORDER BY CASE priority 
                    WHEN 'Высокий' THEN 1
                    WHEN 'Средний' THEN 2
                    WHEN 'Низкий' THEN 3
                END, due_date
            ''', (status_filter,))
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
        return self.cursor.rowcount > 0
    
    def delete_task(self, task_id):
        """Удаление задачи"""
        self.cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def update_task(self, task_id, title, description, priority, due_date):
        """Обновление задачи"""
        self.cursor.execute('''
            UPDATE tasks 
            SET title = ?, description = ?, priority = ?, due_date = ?
            WHERE id = ?
        ''', (title, description, priority, due_date, task_id))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def search_tasks(self, search_term):
        """Поиск задач по названию или описанию"""
        self.cursor.execute('''
            SELECT id, title, description, priority, status, 
                   created_date, due_date, completed_date 
            FROM tasks 
            WHERE title LIKE ? OR description LIKE ?
            ORDER BY 
                CASE priority 
                    WHEN 'Высокий' THEN 1
                    WHEN 'Средний' THEN 2
                    WHEN 'Низкий' THEN 3
                END, due_date
        ''', (f'%{search_term}%', f'%{search_term}%'))
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