import os
import sys
from typing import List, Optional

from PyQt5.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    Qt,
    QSortFilterProxyModel,
    QDate,
    QItemSelectionModel,
    QSettings,
)
from PyQt5.QtGui import QColor, QFont, QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QCalendarWidget,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QTextEdit,
    QHeaderView,
    QMenu,
    QShortcut,
)

from database import Database, Task


class TaskDialog(QDialog):
    def __init__(self, parent=None, task: Optional[Task] = None):
        super().__init__(parent)
        self.task = task
        self.setWindowTitle('Новая задача' if task is None else 'Редактирование задачи')
        self.setModal(True)
        self.setMinimumWidth(520)
        self.init_ui()
        if task:
            self.load_task_data(task)

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText('Введите название задачи')
        form_layout.addRow('Название:', self.title_edit)

        self.project_edit = QLineEdit()
        self.project_edit.setPlaceholderText('Проект или категория')
        form_layout.addRow('Проект:', self.project_edit)

        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText('Теги через запятую')
        form_layout.addRow('Теги:', self.tags_edit)

        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        self.description_edit.setPlaceholderText('Описание задачи')
        form_layout.addRow('Описание:', self.description_edit)

        self.estimate_edit = QLineEdit()
        self.estimate_edit.setPlaceholderText('Оценка времени, например: 2 ч')
        form_layout.addRow('Оценка:', self.estimate_edit)

        self.priority_combo = QComboBox()
        self.priority_combo.addItems(['Низкий', 'Средний', 'Высокий'])
        form_layout.addRow('Приоритет:', self.priority_combo)

        self.status_combo = QComboBox()
        self.status_combo.addItems(['Активна', 'Выполнена', 'Отложена'])
        form_layout.addRow('Статус:', self.status_combo)

        self.recurrence_combo = QComboBox()
        self.recurrence_combo.addItems(['Нет', 'Ежедневно', 'Еженедельно', 'Ежемесячно'])
        form_layout.addRow('Повторение:', self.recurrence_combo)

        self.due_date_edit = QDateEdit()
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.setDate(QDate.currentDate())
        form_layout.addRow('Срок:', self.due_date_edit)

        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_task_data(self, task: Task) -> None:
        self.title_edit.setText(task.title)
        self.project_edit.setText(task.project)
        self.tags_edit.setText(task.tags)
        self.description_edit.setText(task.description)
        self.estimate_edit.setText(task.estimate)

        status_index = self.status_combo.findText(task.status)
        if status_index >= 0:
            self.status_combo.setCurrentIndex(status_index)

        priority_index = self.priority_combo.findText(task.priority)
        if priority_index >= 0:
            self.priority_combo.setCurrentIndex(priority_index)

        if task.due_date:
            due_date = QDate.fromString(task.due_date, 'yyyy-MM-dd')
            if due_date.isValid():
                self.due_date_edit.setDate(due_date)
        recurrence_index = self.recurrence_combo.findText(task.recurrence)
        if recurrence_index >= 0:
            self.recurrence_combo.setCurrentIndex(recurrence_index)

    def on_accept(self) -> None:
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, 'Ошибка', 'Название задачи не может быть пустым')
            return
        if self.due_date_edit.date() < QDate.currentDate():
            QMessageBox.warning(self, 'Ошибка', 'Срок выполнения не может быть прошедшим')
            return
        self.accept()

    def get_task_data(self) -> dict:
        return {
            'title': self.title_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'project': self.project_edit.text().strip(),
            'tags': self.tags_edit.text().strip(),
            'estimate': self.estimate_edit.text().strip(),
            'priority': self.priority_combo.currentText(),
            'status': self.status_combo.currentText(),
            'recurrence': self.recurrence_combo.currentText(),
            'due_date': self.due_date_edit.date().toString('yyyy-MM-dd'),
        }


class TaskTableModel(QAbstractTableModel):
    HEADERS = ['ID', 'Название', 'Проект', 'Приоритет', 'Статус', 'Повторение', 'Срок', 'Теги', 'Оценка']

    def __init__(self, tasks: Optional[List[Task]] = None, parent=None):
        super().__init__(parent)
        self._tasks = tasks or []

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._tasks)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        task = self._tasks[index.row()]
        if role == Qt.DisplayRole:
            return [
                task.id,
                task.title,
                task.project,
                task.priority,
                task.status,
                task.recurrence,
                task.due_date,
                task.tags,
                task.estimate,
            ][index.column()]
        if role == Qt.TextAlignmentRole:
            return Qt.AlignLeft | Qt.AlignVCenter if index.column() != 0 else Qt.AlignCenter
        if role == Qt.ForegroundRole:
            if index.column() == 3:
                if task.priority == 'Высокий':
                    return QColor('#d32f2f')
                if task.priority == 'Низкий':
                    return QColor('#1976d2')
            if index.column() == 4 and task.status == 'Выполнена':
                return QColor('#4CAF50')
            if task.status == 'Активна' and task.due_date:
                if QDate.fromString(task.due_date, 'yyyy-MM-dd') < QDate.currentDate():
                    return QColor('#d32f2f')
                if QDate.fromString(task.due_date, 'yyyy-MM-dd') == QDate.currentDate():
                    return QColor('#f57c00')
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return super().headerData(section, orientation, role)

    def update_tasks(self, tasks: List[Task]) -> None:
        self.beginResetModel()
        self._tasks = tasks
        self.endResetModel()

    def get_task(self, row: int) -> Optional[Task]:
        return self._tasks[row] if 0 <= row < len(self._tasks) else None


class TaskFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.status_filter = 'Все'
        self.project_filter = 'Все проекты'
        self.tag_filter = 'Все теги'
        self.search_text = ''

    def set_status_filter(self, status: str) -> None:
        self.status_filter = status
        self.invalidateFilter()

    def set_project_filter(self, project: str) -> None:
        self.project_filter = project
        self.invalidateFilter()

    def set_tag_filter(self, tag: str) -> None:
        self.tag_filter = tag
        self.invalidateFilter()

    def set_search_text(self, text: str) -> None:
        self.search_text = text.lower().strip()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        task = model.get_task(source_row) if model else None
        if not task:
            return False
        if self.status_filter != 'Все' and task.status != self.status_filter:
            return False
        if self.project_filter != 'Все проекты' and task.project != self.project_filter:
            return False
        if self.tag_filter != 'Все теги' and self.tag_filter not in task.tag_list():
            return False
        if self.search_text:
            terms = [term for term in self.search_text.split() if term]
            haystack = ' '.join([
                task.title,
                task.description,
                task.project,
                task.tags,
                task.estimate,
                task.status,
                task.recurrence,
            ]).lower()
            return all(term in haystack for term in terms)
        return True

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        model = self.sourceModel()
        left_task = model.get_task(left.row()) if model else None
        right_task = model.get_task(right.row()) if model else None
        if not left_task or not right_task:
            return False
        column = left.column()
        if column == 6:
            return (left_task.due_date or '9999-12-31') < (right_task.due_date or '9999-12-31')
        if column == 3:
            order = {'Высокий': 0, 'Средний': 1, 'Низкий': 2}
            return order.get(left_task.priority, 3) < order.get(right_task.priority, 3)
        if column == 4:
            order = {'Активна': 0, 'Отложена': 1, 'Выполнена': 2}
            return order.get(left_task.status, 3) < order.get(right_task.status, 3)
        return str(self.sourceModel().data(left, Qt.DisplayRole)) < str(self.sourceModel().data(right, Qt.DisplayRole))


class StatisticsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        self.cards = {}
        for title in ['Всего задач', 'Активных', 'Выполнено', 'Высокий приоритет', 'Просрочено']:
            row = QHBoxLayout()
            row.addWidget(QLabel(f'<b>{title}:</b>'))
            value_label = QLabel('0')
            value_label.setStyleSheet('font-size: 24px; font-weight: bold;')
            row.addWidget(value_label)
            row.addStretch()
            layout.addLayout(row)
            self.cards[title] = value_label
        self.progress = QLabel('Прогресс: 0%')
        self.progress.setStyleSheet('font-size: 14px; color: #555;')
        layout.addWidget(self.progress)

    def update_stats(self, stats: dict) -> None:
        self.cards['Всего задач'].setText(str(stats['total']))
        self.cards['Активных'].setText(str(stats['active']))
        self.cards['Выполнено'].setText(str(stats['completed']))
        self.cards['Высокий приоритет'].setText(str(stats['high_priority']))
        self.cards['Просрочено'].setText(str(stats['overdue']))
        percent = int((stats['completed'] / stats['total']) * 100) if stats['total'] else 0
        self.progress.setText(f'Прогресс: {percent}%')


class TodoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings('ToDoPlanner', 'SuperToDoPlanner')
        self.db = Database()
        self.init_ui()
        self.load_settings()
        self.load_tasks()
        self.update_statistics()

    def init_ui(self) -> None:
        self.dark_mode = False
        self.setWindowTitle('Super ToDo Planner')
        self.setGeometry(100, 100, 1320, 780)
        self.load_stylesheet()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.create_menu()
        self.create_toolbar(main_layout)
        self.create_tabs(main_layout)
        self.create_status_bar()

    def create_menu(self) -> None:
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu('Файл')

        import_action = QAction('Импорт JSON...', self, shortcut=QKeySequence('Ctrl+I'))
        export_action = QAction('Экспорт JSON...', self, shortcut=QKeySequence('Ctrl+S'))
        export_csv_action = QAction('Экспорт CSV...', self, shortcut=QKeySequence('Ctrl+Shift+S'))
        file_menu.addAction(import_action)
        file_menu.addAction(export_action)
        file_menu.addAction(export_csv_action)
        file_menu.addSeparator()
        file_menu.addAction(QAction('Выход', self, triggered=self.close))

        action_menu = menu_bar.addMenu('Действия')
        new_action = QAction('Новая задача', self, shortcut=QKeySequence('Ctrl+N'), triggered=self.add_task)
        edit_action = QAction('Редактировать задачу', self, shortcut=QKeySequence('Ctrl+E'), triggered=self.edit_task)
        complete_action = QAction('Отметить выполненной', self, shortcut=QKeySequence('Ctrl+Return'), triggered=self.complete_task)
        delete_action = QAction('Удалить задачу', self, shortcut=QKeySequence.Delete, triggered=self.delete_task)
        action_menu.addAction(new_action)
        action_menu.addAction(edit_action)
        action_menu.addAction(complete_action)
        action_menu.addAction(delete_action)

        view_menu = menu_bar.addMenu('Вид')
        theme_action = QAction('Сменить тему', self, shortcut=QKeySequence('Ctrl+T'), triggered=self.toggle_theme)
        view_menu.addAction(theme_action)

        import_action.triggered.connect(self.import_tasks)
        export_action.triggered.connect(self.export_tasks_json)
        export_csv_action.triggered.connect(self.export_tasks_csv)

    def create_toolbar(self, parent_layout) -> None:
        toolbar = QHBoxLayout()

        self.add_btn = QPushButton('➕ Новая')
        self.add_btn.clicked.connect(self.add_task)
        toolbar.addWidget(self.add_btn)

        self.edit_btn = QPushButton('✏️ Редактировать')
        self.edit_btn.clicked.connect(self.edit_task)
        toolbar.addWidget(self.edit_btn)

        self.complete_btn = QPushButton('✅ Выполнена')
        self.complete_btn.clicked.connect(self.complete_task)
        toolbar.addWidget(self.complete_btn)

        self.delete_btn = QPushButton('🗑️ Удалить')
        self.delete_btn.clicked.connect(self.delete_task)
        toolbar.addWidget(self.delete_btn)

        toolbar.addStretch()

        self.status_filter = QComboBox()
        self.status_filter.addItems(['Все', 'Активна', 'Выполнена', 'Отложена'])
        self.status_filter.currentTextChanged.connect(self.on_filter_changed)
        toolbar.addWidget(QLabel('Статус:'))
        toolbar.addWidget(self.status_filter)

        self.project_filter = QComboBox()
        self.project_filter.addItem('Все проекты')
        self.project_filter.currentTextChanged.connect(self.on_filter_changed)
        toolbar.addWidget(QLabel('Проект:'))
        toolbar.addWidget(self.project_filter)

        self.tag_filter = QComboBox()
        self.tag_filter.addItem('Все теги')
        self.tag_filter.currentTextChanged.connect(self.on_filter_changed)
        toolbar.addWidget(QLabel('Тег:'))
        toolbar.addWidget(self.tag_filter)

        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDate(QDate(1970, 1, 1))
        self.from_date.setMaximumWidth(110)
        self.from_date.dateChanged.connect(self.on_filter_changed)
        toolbar.addWidget(QLabel('Срок с:'))
        toolbar.addWidget(self.from_date)

        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDate(QDate(2099, 12, 31))
        self.to_date.setMaximumWidth(110)
        self.to_date.dateChanged.connect(self.on_filter_changed)
        toolbar.addWidget(QLabel('по:'))
        toolbar.addWidget(self.to_date)

        self.clear_date_btn = QPushButton('Сброс даты')
        self.clear_date_btn.clicked.connect(self.reset_date_filter)
        toolbar.addWidget(self.clear_date_btn)

        self.today_btn = QPushButton('Сегодня')
        self.today_btn.clicked.connect(self.filter_today)
        toolbar.addWidget(self.today_btn)

        self.week_btn = QPushButton('На неделю')
        self.week_btn.clicked.connect(self.filter_week)
        toolbar.addWidget(self.week_btn)

        self.overdue_btn = QPushButton('Просроченные')
        self.overdue_btn.clicked.connect(self.filter_overdue)
        toolbar.addWidget(self.overdue_btn)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText('Поиск по задачам...')
        self.search_edit.setMaximumWidth(220)
        self.search_edit.textChanged.connect(self.on_search_changed)
        toolbar.addWidget(self.search_edit)

        self.search_shortcut = QShortcut(QKeySequence('Ctrl+F'), self)
        self.search_shortcut.activated.connect(self.search_edit.setFocus)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(['По умолчанию', 'По сроку', 'По приоритету', 'По статусу'])
        self.sort_combo.currentTextChanged.connect(self.on_sort_changed)
        toolbar.addWidget(QLabel('Сортировка:'))
        toolbar.addWidget(self.sort_combo)

        self.theme_btn = QPushButton('Тёмная тема')
        self.theme_btn.clicked.connect(lambda: self.set_theme(not self.dark_mode))
        toolbar.addWidget(self.theme_btn)

        parent_layout.addLayout(toolbar)

    def create_tabs(self, parent_layout) -> None:
        self.tabs = QTabWidget()
        self.create_tasks_tab()
        self.create_overview_tab()
        parent_layout.addWidget(self.tabs)

    def create_tasks_tab(self) -> None:
        tasks_widget = QWidget()
        tasks_layout = QHBoxLayout(tasks_widget)

        self.task_model = TaskTableModel([])
        self.proxy_model = TaskFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.task_model)
        self.proxy_model.setDynamicSortFilter(True)

        self.table_view = QTableView()
        self.table_view.setModel(self.proxy_model)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSortingEnabled(True)
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.open_context_menu)
        self.table_view.doubleClicked.connect(self.edit_task)
        self.table_view.selectionModel().currentRowChanged.connect(self.on_selection_changed)

        tasks_layout.addWidget(self.table_view, 2)

        detail_group = QGroupBox('Детали задачи')
        detail_layout = QVBoxLayout(detail_group)
        self.detail_labels = {}
        for label_text in ['Название', 'Проект', 'Теги', 'Приоритет', 'Статус', 'Повторение', 'Срок', 'Оценка', 'Описание', 'Создано']:
            caption = QLabel(f'<b>{label_text}:</b>')
            value_label = QLabel('—')
            value_label.setWordWrap(True)
            detail_layout.addWidget(caption)
            detail_layout.addWidget(value_label)
            self.detail_labels[label_text] = value_label
        detail_layout.addStretch()
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        detail_layout.addWidget(self.calendar)

        tasks_layout.addWidget(detail_group, 1)
        self.tabs.addTab(tasks_widget, 'Задачи')

    def create_overview_tab(self) -> None:
        overview_widget = QWidget()
        overview_layout = QVBoxLayout(overview_widget)
        self.statistics_widget = StatisticsWidget()
        overview_layout.addWidget(self.statistics_widget)
        self.tabs.addTab(overview_widget, 'Обзор')

    def create_status_bar(self) -> None:
        self.status_label = QLabel('Готово')
        self.statusBar().addWidget(self.status_label)

    def load_stylesheet(self) -> None:
        path = os.path.join(os.path.dirname(__file__), 'styles.qss')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())

    def toggle_theme(self) -> None:
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            self.setStyleSheet(self.dark_stylesheet())
            self.theme_btn.setText('Светлая тема')
        else:
            self.load_stylesheet()
            self.theme_btn.setText('Тёмная тема')

    def dark_stylesheet(self) -> str:
        return '''
            QWidget { background-color: #2d2d2d; color: #dddddd; }
            QLineEdit, QTextEdit, QComboBox, QDateEdit { background-color: #3c3f41; color: #eeeeee; border: 1px solid #5a5a5a; }
            QPushButton { background-color: #5c6bc0; color: white; border-radius: 4px; }
            QPushButton:hover { background-color: #7986cb; }
            QHeaderView::section { background-color: #424242; color: white; }
            QTableView { background-color: #313335; alternate-background-color: #2d2d2d; gridline-color: #4f4f4f; }
            QGroupBox { border: 1px solid #5a5a5a; }
            QCalendarWidget QWidget { background-color: #2d2d2d; }
        '''

    def get_current_sort_key(self) -> Optional[str]:
        return {
            'По сроку': 'due',
            'По приоритету': 'priority',
            'По статусу': 'status',
        }.get(self.sort_combo.currentText())

    def load_tasks(self) -> None:
        tasks = self.db.get_all_tasks(
            status_filter=self.status_filter.currentText(),
            project_filter=self.project_filter.currentText(),
            tag_filter=self.tag_filter.currentText(),
            date_from=self.from_date.date().toString('yyyy-MM-dd'),
            date_to=self.to_date.date().toString('yyyy-MM-dd'),
            sort_by=self.get_current_sort_key(),
        )
        self.task_model.update_tasks(tasks)
        self.proxy_model.invalidate()
        self.update_filter_options()
        self.update_statistics()
        self.check_due_notifications(tasks)
        self.status_label.setText(f'Загружено {len(tasks)} задач')

    def update_statistics(self) -> None:
        self.statistics_widget.update_stats(self.db.get_statistics())

    def update_filter_options(self) -> None:
        projects = ['Все проекты'] + self.db.get_unique_projects()
        current_project = self.project_filter.currentText()
        self.project_filter.blockSignals(True)
        self.project_filter.clear()
        self.project_filter.addItems(projects)
        if current_project in projects:
            self.project_filter.setCurrentText(current_project)
        self.project_filter.blockSignals(False)

        tags = ['Все теги'] + self.db.get_unique_tags()
        current_tag = self.tag_filter.currentText()
        self.tag_filter.blockSignals(True)
        self.tag_filter.clear()
        self.tag_filter.addItems(tags)
        if current_tag in tags:
            self.tag_filter.setCurrentText(current_tag)
        self.tag_filter.blockSignals(False)

    def load_settings(self) -> None:
        geometry = self.settings.value('windowGeometry')
        if geometry is not None:
            self.restoreGeometry(geometry)
        window_state = self.settings.value('windowState')
        if window_state is not None:
            self.restoreState(window_state)

        self.set_theme(self.settings.value('darkMode', False, type=bool), save=False)
        self.status_filter.setCurrentText(self.settings.value('statusFilter', 'Все', type=str))
        self.project_filter.setCurrentText(self.settings.value('projectFilter', 'Все проекты', type=str))
        self.tag_filter.setCurrentText(self.settings.value('tagFilter', 'Все теги', type=str))
        self.search_edit.setText(self.settings.value('searchText', '', type=str))
        self.sort_combo.setCurrentText(self.settings.value('sortOption', 'По умолчанию', type=str))
        self.from_date.setDate(self.settings.value('fromDate', QDate(1970, 1, 1), type=QDate))
        self.to_date.setDate(self.settings.value('toDate', QDate(2099, 12, 31), type=QDate))
        self.tabs.setCurrentIndex(self.settings.value('lastTab', 0, type=int))

    def save_settings(self) -> None:
        self.settings.setValue('windowGeometry', self.saveGeometry())
        self.settings.setValue('windowState', self.saveState())
        self.settings.setValue('darkMode', self.dark_mode)
        self.settings.setValue('statusFilter', self.status_filter.currentText())
        self.settings.setValue('projectFilter', self.project_filter.currentText())
        self.settings.setValue('tagFilter', self.tag_filter.currentText())
        self.settings.setValue('searchText', self.search_edit.text())
        self.settings.setValue('sortOption', self.sort_combo.currentText())
        self.settings.setValue('fromDate', self.from_date.date())
        self.settings.setValue('toDate', self.to_date.date())
        self.settings.setValue('lastTab', self.tabs.currentIndex())

    def reset_date_filter(self) -> None:
        self.from_date.setDate(QDate(1970, 1, 1))
        self.to_date.setDate(QDate(2099, 12, 31))
        self.load_tasks()

    def filter_today(self) -> None:
        today = QDate.currentDate()
        self.from_date.setDate(today)
        self.to_date.setDate(today)
        self.status_filter.setCurrentText('Все')
        self.load_tasks()

    def filter_week(self) -> None:
        today = QDate.currentDate()
        self.from_date.setDate(today)
        self.to_date.setDate(today.addDays(7))
        self.status_filter.setCurrentText('Все')
        self.load_tasks()

    def filter_overdue(self) -> None:
        self.from_date.setDate(QDate(1970, 1, 1))
        self.to_date.setDate(QDate.currentDate().addDays(-1))
        self.status_filter.setCurrentText('Активна')
        self.load_tasks()

    def set_theme(self, dark_mode: bool, save: bool = True) -> None:
        self.dark_mode = dark_mode
        if self.dark_mode:
            self.setStyleSheet(self.dark_stylesheet())
            self.theme_btn.setText('Светлая тема')
        else:
            self.load_stylesheet()
            self.theme_btn.setText('Тёмная тема')
        if save:
            self.settings.setValue('darkMode', self.dark_mode)

    def on_filter_changed(self) -> None:
        self.load_tasks()

    def on_search_changed(self, text: str) -> None:
        self.proxy_model.set_search_text(text)

    def on_sort_changed(self, text: str) -> None:
        self.load_tasks()

    def get_selected_task(self) -> Optional[Task]:
        selection = self.table_view.currentIndex()
        if not selection.isValid():
            return None
        source_index = self.proxy_model.mapToSource(selection)
        return self.task_model.get_task(source_index.row())

    def add_task(self) -> None:
        dialog = TaskDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_task_data()
            self.db.add_task(
                data['title'],
                data['description'],
                data['priority'],
                data['due_date'],
                data['project'],
                data['tags'],
                data['estimate'],
                data['recurrence'],
            )
            self.load_tasks()
            self.status_label.setText(f"Задача '{data['title']}' добавлена")

    def edit_task(self) -> None:
        task = self.get_selected_task()
        if task is None:
            QMessageBox.information(self, 'Информация', 'Выберите задачу для редактирования')
            return
        dialog = TaskDialog(self, task)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_task_data()
            self.db.update_task(
                task.id,
                data['title'],
                data['description'],
                data['priority'],
                data['status'],
                data['due_date'],
                data['project'],
                data['tags'],
                data['estimate'],
                data['recurrence'],
            )
            self.load_tasks()
            self.status_label.setText('Задача обновлена')

    def complete_task(self) -> None:
        task = self.get_selected_task()
        if task is None:
            QMessageBox.information(self, 'Информация', 'Выберите задачу')
            return
        if task.status == 'Выполнена':
            QMessageBox.information(self, 'Информация', 'Задача уже выполнена')
            return
        if QMessageBox.question(self, 'Подтверждение', f"Отметить задачу '{task.title}' как выполненную?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.db.complete_task(task.id)
            self.load_tasks()
            self.status_label.setText(f"Задача '{task.title}' выполнена")

    def delete_task(self) -> None:
        task = self.get_selected_task()
        if task is None:
            QMessageBox.information(self, 'Информация', 'Выберите задачу для удаления')
            return
        if QMessageBox.question(self, 'Подтверждение', f"Удалить задачу '{task.title}'?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.db.delete_task(task.id)
            self.load_tasks()
            self.status_label.setText(f"Задача '{task.title}' удалена")

    def on_selection_changed(self, selected: QModelIndex, previous: QModelIndex) -> None:
        if not selected.isValid():
            return
        source_index = self.proxy_model.mapToSource(selected)
        task = self.task_model.get_task(source_index.row())
        if task:
            self.show_task_details(task)

    def show_task_details(self, task: Task) -> None:
        self.detail_labels['Название'].setText(task.title)
        self.detail_labels['Проект'].setText(task.project or '—')
        self.detail_labels['Теги'].setText(task.tags or '—')
        self.detail_labels['Приоритет'].setText(task.priority)
        self.detail_labels['Статус'].setText(task.status)
        self.detail_labels['Повторение'].setText(task.recurrence)
        self.detail_labels['Срок'].setText(task.due_date or '—')
        self.detail_labels['Оценка'].setText(task.estimate or '—')
        self.detail_labels['Описание'].setText(task.description or '—')
        self.detail_labels['Создано'].setText(task.created_date or '—')
        if task.due_date:
            date = QDate.fromString(task.due_date, 'yyyy-MM-dd')
            if date.isValid():
                self.calendar.setSelectedDate(date)

    def open_context_menu(self, position) -> None:
        index = self.table_view.indexAt(position)
        if not index.isValid():
            return
        self.table_view.selectionModel().setCurrentIndex(index, QItemSelectionModel.SelectCurrent)
        menu = QMenu(self)
        menu.addAction('Редактировать', self.edit_task)
        menu.addAction('✅ Выполнена', self.complete_task)
        menu.addAction('Удалить', self.delete_task)
        menu.exec_(self.table_view.viewport().mapToGlobal(position))

    def import_tasks(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Импорт JSON', '', 'JSON Files (*.json)')
        if not path:
            return
        try:
            self.db.import_from_json(path)
            self.load_tasks()
            self.status_label.setText('Импорт завершён')
        except Exception as exc:
            QMessageBox.critical(self, 'Ошибка импорта', f'Не удалось импортировать файл:\n{exc}')

    def export_tasks_json(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, 'Экспорт JSON', '', 'JSON Files (*.json)')
        if not path:
            return
        try:
            self.db.export_to_json(path)
            self.status_label.setText('Экспорт JSON завершён')
        except Exception as exc:
            QMessageBox.critical(self, 'Ошибка экспорта', f'Не удалось сохранить JSON:\n{exc}')

    def export_tasks_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, 'Экспорт CSV', '', 'CSV Files (*.csv)')
        if not path:
            return
        try:
            self.db.export_to_csv(path)
            self.status_label.setText('Экспорт CSV завершён')
        except Exception as exc:
            QMessageBox.critical(self, 'Ошибка экспорта', f'Не удалось сохранить CSV:\n{exc}')

    def check_due_notifications(self, tasks: List[Task]) -> None:
        overdue = [task for task in tasks if task.status == 'Активна' and task.due_date and QDate.fromString(task.due_date, 'yyyy-MM-dd') < QDate.currentDate()]
        due_today = [task for task in tasks if task.status == 'Активна' and task.due_date == QDate.currentDate().toString('yyyy-MM-dd')]
        if overdue:
            QMessageBox.warning(self, 'Просроченные задачи', f'У вас {len(overdue)} просроченных задач. (нажмите ОК для просмотра)')
            self.status_label.setText(f'Просрочено: {len(overdue)}')
        elif due_today:
            QMessageBox.information(self, 'Задачи на сегодня', f'Сегодня нужно выполнить {len(due_today)} задач.')
            self.status_label.setText(f'На сегодня: {len(due_today)}')

    def closeEvent(self, event) -> None:
        self.save_settings()
        self.db.close()
        event.accept()


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setFont(QFont('Segoe UI', 10))
    window = TodoApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
