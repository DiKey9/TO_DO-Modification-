import csv
import json
import os
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


@dataclass
class Task:
    id: Optional[int]
    title: str
    description: str = ""
    priority: str = "Средний"
    status: str = "Активна"
    project: str = ""
    tags: str = ""
    estimate: str = ""
    created_date: str = ""
    due_date: str = ""
    completed_date: str = ""
    recurrence: str = "Нет"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def tag_list(self) -> List[str]:
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]


class Database:
    DEFAULT_COLUMNS = {
        'project': "TEXT DEFAULT ''",
        'tags': "TEXT DEFAULT ''",
        'estimate': "TEXT DEFAULT ''",
        'recurrence': "TEXT DEFAULT 'Нет'",
    }

    def __init__(self, db_name: str = "tasks.db", json_backup: str = "tasks.json") -> None:
        self.db_name = db_name
        self.json_backup = json_backup
        self.conn = sqlite3.connect(self.db_name)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.create_table()
        self.ensure_columns()
        if self.is_empty() and os.path.exists(self.json_backup):
            self.import_from_json(self.json_backup)

    def create_table(self) -> None:
        self.cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT DEFAULT 'Средний',
                status TEXT DEFAULT 'Активна',
                project TEXT DEFAULT '',
                tags TEXT DEFAULT '',
                estimate TEXT DEFAULT '',
                created_date TEXT NOT NULL,
                due_date TEXT,
                completed_date TEXT,
                recurrence TEXT DEFAULT 'Нет'
            )
            '''
        )
        self.conn.commit()

    def ensure_columns(self) -> None:
        self.cursor.execute("PRAGMA table_info(tasks)")
        existing = {row['name'] for row in self.cursor.fetchall()}
        for column, definition in self.DEFAULT_COLUMNS.items():
            if column not in existing:
                self.cursor.execute(f"ALTER TABLE tasks ADD COLUMN {column} {definition}")
        self.conn.commit()

    def is_empty(self) -> bool:
        self.cursor.execute("SELECT COUNT(*) FROM tasks")
        return self.cursor.fetchone()[0] == 0

    def add_task(
        self,
        title: str,
        description: str,
        priority: str,
        due_date: str,
        project: str = "",
        tags: str = "",
        estimate: str = "",
        recurrence: str = "Нет",
    ) -> int:
        created_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.cursor.execute(
            '''
            INSERT INTO tasks (title, description, priority, status, project, tags, estimate, due_date, recurrence, created_date)
            VALUES (?, ?, ?, 'Активна', ?, ?, ?, ?, ?, ?)
            ''',
            (title, description, priority, project, tags, estimate, due_date, recurrence, created_date),
        )
        self.conn.commit()
        rowid = self.cursor.lastrowid
        self.export_to_json()
        return rowid

    def get_task(self, task_id: int) -> Optional[Task]:
        self.cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
        row = self.cursor.fetchone()
        return self._row_to_task(row) if row else None

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        return Task(
            id=row['id'],
            title=row['title'],
            description=row['description'] or "",
            priority=row['priority'] or 'Средний',
            status=row['status'] or 'Активна',
            project=row['project'] or "",
            tags=row['tags'] or "",
            estimate=row['estimate'] or "",
            created_date=row['created_date'] or "",
            due_date=row['due_date'] or "",
            completed_date=row['completed_date'] or "",
            recurrence=row['recurrence'] or 'Нет',
        )

    def get_all_tasks(
        self,
        status_filter: str = "Все",
        project_filter: Optional[str] = None,
        tag_filter: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> List[Task]:
        base = 'SELECT * FROM tasks'
        conditions = []
        params: List[Any] = []
        if status_filter != "Все":
            conditions.append('status = ?')
            params.append(status_filter)
        if project_filter and project_filter != "Все проекты":
            conditions.append('project = ?')
            params.append(project_filter)
        if tag_filter and tag_filter != "Все теги":
            conditions.append('tags LIKE ?')
            params.append(f'%{tag_filter}%')
        if date_from:
            conditions.append('due_date >= ?')
            params.append(date_from)
        if date_to:
            conditions.append('due_date <= ?')
            params.append(date_to)
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ''
        order = self._build_order_clause(sort_by)
        query = ' '.join([base, where_clause, order])
        self.cursor.execute(query, tuple(params))
        return [self._row_to_task(row) for row in self.cursor.fetchall()]

    def _calculate_next_due_date(self, due_date: str, recurrence: str) -> Optional[str]:
        try:
            current = datetime.strptime(due_date, '%Y-%m-%d')
        except (ValueError, TypeError):
            return None
        if recurrence == 'Ежедневно':
            next_date = current + timedelta(days=1)
        elif recurrence == 'Еженедельно':
            next_date = current + timedelta(weeks=1)
        elif recurrence == 'Ежемесячно':
            month = current.month + 1
            year = current.year + (month - 1) // 12
            month = (month - 1) % 12 + 1
            day = min(current.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
            next_date = datetime(year, month, day)
        else:
            return None
        return next_date.strftime('%Y-%m-%d')

    def _build_order_clause(self, sort_by: Optional[str]) -> str:
        if sort_by == 'due':
            return "ORDER BY (due_date IS NULL), due_date ASC"
        if sort_by == 'priority':
            return ("ORDER BY CASE priority WHEN 'Высокий' THEN 1 WHEN 'Средний' THEN 2 "
                    "WHEN 'Низкий' THEN 3 ELSE 4 END, due_date ASC")
        if sort_by == 'status':
            return ("ORDER BY CASE status WHEN 'Активна' THEN 1 WHEN 'Выполнена' THEN 2 "
                    "WHEN 'Отложена' THEN 3 ELSE 4 END, due_date ASC")
        return "ORDER BY (due_date IS NULL), due_date ASC"

    def search_tasks(
        self,
        search_term: str,
        status_filter: str = "Все",
        project_filter: Optional[str] = None,
        tag_filter: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> List[Task]:
        pattern = f"%{search_term}%"
        base = (
            'SELECT * FROM tasks '
            'WHERE (title LIKE ? OR description LIKE ? OR project LIKE ? OR tags LIKE ?)'
        )
        params: List[Any] = [pattern, pattern, pattern, pattern]
        if status_filter != "Все":
            base += ' AND status = ?'
            params.append(status_filter)
        if project_filter and project_filter != "Все проекты":
            base += ' AND project = ?'
            params.append(project_filter)
        if tag_filter and tag_filter != "Все теги":
            base += ' AND tags LIKE ?'
            params.append(f'%{tag_filter}%')
        if date_from:
            base += ' AND due_date >= ?'
            params.append(date_from)
        if date_to:
            base += ' AND due_date <= ?'
            params.append(date_to)
        order = self._build_order_clause(sort_by)
        query = ' '.join([base, order])
        self.cursor.execute(query, tuple(params))
        return [self._row_to_task(row) for row in self.cursor.fetchall()]

    def update_task(
        self,
        task_id: int,
        title: str,
        description: str,
        priority: str,
        status: str,
        due_date: str,
        project: str,
        tags: str,
        estimate: str,
        recurrence: str,
    ) -> bool:
        self.cursor.execute(
            '''
            UPDATE tasks
            SET title = ?, description = ?, priority = ?, status = ?,
                project = ?, tags = ?, estimate = ?, due_date = ?, recurrence = ?
            WHERE id = ?
            ''',
            (title, description, priority, status, project, tags, estimate, due_date, recurrence, task_id),
        )
        self.conn.commit()
        updated = self.cursor.rowcount > 0
        if updated:
            self.export_to_json()
        return updated

    def complete_task(self, task_id: int) -> bool:
        task = self.get_task(task_id)
        completed_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.cursor.execute(
            '''
            UPDATE tasks
            SET status = 'Выполнена', completed_date = ?
            WHERE id = ?
            ''',
            (completed_date, task_id),
        )
        self.conn.commit()
        updated = self.cursor.rowcount > 0
        if updated and task and task.recurrence != 'Нет':
            next_due = self._calculate_next_due_date(task.due_date, task.recurrence)
            if next_due:
                self.add_task(
                    task.title,
                    task.description,
                    task.priority,
                    next_due,
                    project=task.project,
                    tags=task.tags,
                    estimate=task.estimate,
                    recurrence=task.recurrence,
                )
        if updated:
            self.export_to_json()
        return updated

    def delete_task(self, task_id: int) -> bool:
        self.cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        self.conn.commit()
        deleted = self.cursor.rowcount > 0
        if deleted:
            self.export_to_json()
        return deleted

    def export_to_json(self, file_path: Optional[str] = None) -> None:
        if file_path is None:
            file_path = self.json_backup
        tasks = [task.to_dict() for task in self.get_all_tasks()]
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)

    def import_from_json(self, file_path: Optional[str] = None) -> None:
        if file_path is None:
            file_path = self.json_backup
        if not os.path.exists(file_path):
            return
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, list):
            return
        for task_data in data:
            self.cursor.execute(
                '''
                INSERT OR REPLACE INTO tasks (
                    id, title, description, priority, status, project, tags, estimate, recurrence,
                    created_date, due_date, completed_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    task_data.get('id'),
                    task_data.get('title'),
                    task_data.get('description'),
                    task_data.get('priority', 'Средний'),
                    task_data.get('status', 'Активна'),
                    task_data.get('project', ''),
                    task_data.get('tags', ''),
                    task_data.get('estimate', ''),
                    task_data.get('recurrence', 'Нет'),
                    task_data.get('created_date', datetime.now().strftime("%Y-%m-%d %H:%M")),
                    task_data.get('due_date'),
                    task_data.get('completed_date'),
                ),
            )
        self.conn.commit()
        self._update_sqlite_sequence()

    def export_to_csv(self, file_path: str) -> None:
        tasks = [task.to_dict() for task in self.get_all_tasks()]
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    'id', 'title', 'description', 'priority', 'status',
                    'project', 'tags', 'estimate', 'recurrence', 'created_date', 'due_date', 'completed_date',
                ],
            )
            writer.writeheader()
            writer.writerows(tasks)

    def _update_sqlite_sequence(self) -> None:
        self.cursor.execute('SELECT MAX(id) FROM tasks')
        max_id = self.cursor.fetchone()[0] or 0
        self.cursor.execute(
            "UPDATE sqlite_sequence SET seq = ? WHERE name = 'tasks'",
            (max_id,),
        )
        self.conn.commit()

    def get_unique_projects(self) -> List[str]:
        self.cursor.execute(
            "SELECT DISTINCT project FROM tasks WHERE project IS NOT NULL AND project <> '' ORDER BY project"
        )
        return [row['project'] for row in self.cursor.fetchall()]

    def get_unique_tags(self) -> List[str]:
        self.cursor.execute("SELECT tags FROM tasks WHERE tags IS NOT NULL AND tags <> ''")
        tags: List[str] = []
        for row in self.cursor.fetchall():
            for tag in row['tags'].split(','):
                normalized = tag.strip()
                if normalized and normalized not in tags:
                    tags.append(normalized)
        return sorted(tags)

    def get_statistics(self) -> Dict[str, int]:
        self.cursor.execute(
            '''
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'Активна' THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN status = 'Выполнена' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN priority = 'Высокий' AND status = 'Активна' THEN 1 ELSE 0 END) as high_priority,
                SUM(CASE WHEN date(due_date) < date('now') AND status = 'Активна' THEN 1 ELSE 0 END) as overdue
            FROM tasks
            '''
        )
        stats = self.cursor.fetchone()
        return {
            'total': stats['total'] or 0,
            'active': stats['active'] or 0,
            'completed': stats['completed'] or 0,
            'high_priority': stats['high_priority'] or 0,
            'overdue': stats['overdue'] or 0,
        }

    def close(self) -> None:
        self.conn.close()
