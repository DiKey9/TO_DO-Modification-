import sys
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QLabel, QLineEdit,
    QComboBox, QTextEdit, QDateEdit, QMessageBox, QTabWidget,
    QHeaderView, QSplitter, QFrame, QDialog, QDialogButtonBox,
    QFormLayout, QGroupBox, QGridLayout, QProgressBar
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QColor

from database import Database


class TaskDialog(QDialog):
    """Диалог для добавления/редактирования задачи"""
    
    def __init__(self, parent=None, task_data=None):
        super().__init__(parent)
        self.task_data = task_data
        self.setWindowTitle("Новая задача" if task_data is None else "Редактирование задачи")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.init_ui()
        
        if task_data:
            self.load_task_data()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Форма для ввода данных
        form_layout = QFormLayout()
        
        # Название задачи
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Введите название задачи")
        form_layout.addRow("Название:", self.title_edit)
        
        # Описание
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(100)
        self.desc_edit.setPlaceholderText("Введите описание задачи (необязательно)")
        form_layout.addRow("Описание:", self.desc_edit)
        
        # Приоритет
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Низкий", "Средний", "Высокий"])
        form_layout.addRow("Приоритет:", self.priority_combo)
        
        # Срок выполнения
        self.due_date_edit = QDateEdit()
        self.due_date_edit.setDate(QDate.currentDate().addDays(7))
        self.due_date_edit.setCalendarPopup(True)
        form_layout.addRow("Срок:", self.due_date_edit)
        
        layout.addLayout(form_layout)
        
        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def load_task_data(self):
        """Загрузка данных задачи для редактирования"""
        # self.task_data: (id, title, description, priority, status, created, due, completed)
        self.title_edit.setText(self.task_data[1])
        self.desc_edit.setText(self.task_data[2] if self.task_data[2] else "")
        
        index = self.priority_combo.findText(self.task_data[3])
        if index >= 0:
            self.priority_combo.setCurrentIndex(index)
        
        if self.task_data[6]:
            due_date = QDate.fromString(self.task_data[6], "yyyy-MM-dd hh:mm")
            self.due_date_edit.setDate(due_date)
    
    def get_task_data(self):
        """Получение данных из формы"""
        return {
            'title': self.title_edit.text().strip(),
            'description': self.desc_edit.toPlainText().strip(),
            'priority': self.priority_combo.currentText(),
            'due_date': self.due_date_edit.date().toString("yyyy-MM-dd")
        }


class StatisticsWidget(QWidget):
    """Виджет для отображения статистики"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QGridLayout(self)
        
        # Карточки со статистикой
        self.total_label = self.create_stat_card("Всего задач", "0", 0, 0, "#2196F3")
        self.active_label = self.create_stat_card("Активных", "0", 0, 1, "#4CAF50")
        self.completed_label = self.create_stat_card("Выполнено", "0", 0, 2, "#9C27B0")
        self.high_priority_label = self.create_stat_card("Высокий приоритет", "0", 1, 0, "#FF5722")
        self.overdue_label = self.create_stat_card("Просрочено", "0", 1, 1, "#F44336")
        
        # Прогресс-бар выполнения
        progress_group = QGroupBox("Прогресс выполнения")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% (%v из %m задач)")
        progress_layout.addWidget(self.progress_bar)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group, 2, 0, 1, 3)
    
    def create_stat_card(self, title, value, row, col, color):
        """Создание карточки статистики"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Box)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                color: white;
                border-radius: 5px;
                padding: 10px;
                margin: 5px;
            }}
            QLabel {{
                color: white;
                background: transparent;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        value_label.setAlignment(Qt.AlignRight)
        layout.addWidget(value_label)
        
        self.layout().addWidget(frame, row, col)
        return value_label
    
    def update_stats(self, stats):
        """Обновление статистики"""
        self.total_label.setText(str(stats['total']))
        self.active_label.setText(str(stats['active']))
        self.completed_label.setText(str(stats['completed']))
        self.high_priority_label.setText(str(stats['high_priority']))
        self.overdue_label.setText(str(stats['overdue']))
        
        if stats['total'] > 0:
            progress = int((stats['completed'] / stats['total']) * 100)
            self.progress_bar.setValue(progress)
            self.progress_bar.setFormat(f"%p% ({stats['completed']} из {stats['total']} задач)")
        else:
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Нет задач")


class TodoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.current_filter = "Все"
        self.init_ui()
        self.load_tasks()
        self.update_statistics()
    
    def init_ui(self):
        self.setWindowTitle("Менеджер задач")
        self.setGeometry(100, 100, 1200, 700)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        main_layout = QVBoxLayout(central_widget)
        
        # Верхняя панель с кнопками
        self.create_toolbar(main_layout)
        
        # Статистика
        self.statistics = StatisticsWidget()
        main_layout.addWidget(self.statistics)
        
        # Таблица задач
        self.create_task_table(main_layout)
        
        # Нижняя панель
        self.create_status_bar()
        
        # Применение стилей
        self.apply_styles()
    
    def create_toolbar(self, parent_layout):
        """Создание верхней панели инструментов"""
        toolbar = QHBoxLayout()
        
        # Кнопка добавления
        self.add_btn = QPushButton("➕ Новая задача")
        self.add_btn.setMinimumHeight(40)
        self.add_btn.clicked.connect(self.add_task)
        toolbar.addWidget(self.add_btn)
        
        # Кнопка редактирования
        self.edit_btn = QPushButton("✏️ Редактировать")
        self.edit_btn.setMinimumHeight(40)
        self.edit_btn.clicked.connect(self.edit_task)
        toolbar.addWidget(self.edit_btn)
        
        # Кнопка выполнения
        self.complete_btn = QPushButton("✅ Выполнить")
        self.complete_btn.setMinimumHeight(40)
        self.complete_btn.clicked.connect(self.complete_task)
        toolbar.addWidget(self.complete_btn)
        
        # Кнопка удаления
        self.delete_btn = QPushButton("🗑️ Удалить")
        self.delete_btn.setMinimumHeight(40)
        self.delete_btn.clicked.connect(self.delete_task)
        toolbar.addWidget(self.delete_btn)
        
        toolbar.addStretch()
        
        # Фильтр по статусу
        toolbar.addWidget(QLabel("Фильтр:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Все", "Активна", "Выполнена"])
        self.filter_combo.currentTextChanged.connect(self.on_filter_changed)
        toolbar.addWidget(self.filter_combo)
        
        # Поиск
        toolbar.addWidget(QLabel("Поиск:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Введите текст для поиска...")
        self.search_edit.setMaximumWidth(200)
        self.search_edit.textChanged.connect(self.on_search_changed)
        toolbar.addWidget(self.search_edit)
        
        parent_layout.addLayout(toolbar)
    
    def create_task_table(self, parent_layout):
        """Создание таблицы задач"""
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Название", "Описание", "Приоритет", 
            "Статус", "Создано", "Срок"
        ])
        
        # Настройка таблицы
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(True)
        
        # Двойной клик для редактирования
        self.table.doubleClicked.connect(self.edit_task)
        
        parent_layout.addWidget(self.table)
    
    def create_status_bar(self):
        """Создание строки состояния"""
        self.status_label = QLabel("Готов к работе")
        self.statusBar().addWidget(self.status_label)
    
    def apply_styles(self):
        """Применение стилей к приложению"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QTableWidget {
                background-color: white;
                alternate-background-color: #f9f9f9;
                selection-background-color: #BBDEFB;
                gridline-color: #E0E0E0;
            }
            QHeaderView::section {
                background-color: #2196F3;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QComboBox, QLineEdit, QDateEdit {
                padding: 5px;
                border: 1px solid #BDBDBD;
                border-radius: 4px;
                min-height: 20px;
            }
            QComboBox:focus, QLineEdit:focus, QDateEdit:focus {
                border: 2px solid #2196F3;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #BDBDBD;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
    
    def load_tasks(self):
        """Загрузка задач в таблицу"""
        if hasattr(self, 'search_edit') and self.search_edit.text():
            tasks = self.db.search_tasks(self.search_edit.text())
        else:
            tasks = self.db.get_all_tasks(self.current_filter)
        
        self.table.setRowCount(len(tasks))
        
        for row, task in enumerate(tasks):
            for col, value in enumerate(task):
                item = QTableWidgetItem(str(value) if value else "")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                
                # Цветовая индикация приоритета
                if col == 3:  # Приоритет
                    if value == "Высокий":
                        item.setForeground(QColor("#F44336"))
                    elif value == "Средний":
                        item.setForeground(QColor("#FF9800"))
                
                # Цветовая индикация статуса
                if col == 4:  # Статус
                    if value == "Выполнена":
                        item.setForeground(QColor("#4CAF50"))
                
                self.table.setItem(row, col, item)
    
    def update_statistics(self):
        """Обновление статистики"""
        stats = self.db.get_statistics()
        self.statistics.update_stats(stats)
    
    def add_task(self):
        """Добавление новой задачи"""
        dialog = TaskDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_task_data()
            if data['title']:
                self.db.add_task(
                    data['title'],
                    data['description'],
                    data['priority'],
                    data['due_date']
                )
                self.load_tasks()
                self.update_statistics()
                self.status_label.setText(f"Задача '{data['title']}' добавлена")
            else:
                QMessageBox.warning(self, "Ошибка", "Название задачи не может быть пустым")
    
    def edit_task(self):
        """Редактирование выбранной задачи"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Информация", "Выберите задачу для редактирования")
            return
        
        task_id = int(self.table.item(current_row, 0).text())
        
        # Получаем полные данные задачи из БД
        tasks = self.db.get_all_tasks()
        task_data = next((t for t in tasks if t[0] == task_id), None)
        
        if task_data:
            dialog = TaskDialog(self, task_data)
            if dialog.exec_() == QDialog.Accepted:
                data = dialog.get_task_data()
                if data['title']:
                    self.db.update_task(
                        task_id,
                        data['title'],
                        data['description'],
                        data['priority'],
                        data['due_date']
                    )
                    self.load_tasks()
                    self.status_label.setText(f"Задача обновлена")
                else:
                    QMessageBox.warning(self, "Ошибка", "Название задачи не может быть пустым")
    
    def complete_task(self):
        """Отметить задачу как выполненную"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Информация", "Выберите задачу")
            return
        
        task_id = int(self.table.item(current_row, 0).text())
        task_title = self.table.item(current_row, 1).text()
        
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Отметить задачу '{task_title}' как выполненную?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.db.complete_task(task_id):
                self.load_tasks()
                self.update_statistics()
                self.status_label.setText(f"Задача '{task_title}' выполнена")
    
    def delete_task(self):
        """Удаление задачи"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Информация", "Выберите задачу для удаления")
            return
        
        task_id = int(self.table.item(current_row, 0).text())
        task_title = self.table.item(current_row, 1).text()
        
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить задачу '{task_title}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.db.delete_task(task_id):
                self.load_tasks()
                self.update_statistics()
                self.status_label.setText(f"Задача '{task_title}' удалена")
    
    def on_filter_changed(self, filter_text):
        """Обработка изменения фильтра"""
        filter_map = {
            "Все": "Все",
            "Активна": "Активна",
            "Выполнена": "Выполнена"
        }
        self.current_filter = filter_map.get(filter_text, "Все")
        self.load_tasks()
    
    def on_search_changed(self, search_text):
        """Обработка поиска"""
        self.load_tasks()
    
    def closeEvent(self, event):
        """Обработка закрытия приложения"""
        self.db.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Современный стиль
    
    # Установка шрифта по умолчанию
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = TodoApp()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()