import psutil
import logging
import tkinter as tk
from tkinter import ttk
from threading import Thread
import time
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

# Настройка логирования
logging.basicConfig(
    filename='detailed_system_monitor.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Данные для графиков
process_stats = {'time': [], 'running': [], 'sleeping': [], 'zombie': []}

# Флаг остановки мониторинга
monitoring_active = False

# Ссылка на текущий график
current_canvas = None

def monitor_system():
    """Функция для сбора статистики процессов."""
    try:
        running, sleeping, zombie = 0, 0, 0
        processes = {}

        for process in psutil.process_iter(['pid', 'name', 'username', 'status', 'memory_info', 'cpu_percent', 'create_time']):
            try:
                pid = process.info['pid']
                name = process.info['name']
                username = process.info['username']
                status = process.info['status']
                memory_usage = process.info['memory_info'].rss / (1024 * 1024)  # В МБ
                cpu_usage = process.info['cpu_percent']
                start_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(process.info['create_time']))

                processes[pid] = (name, username, status, f"{memory_usage:.2f} MB", f"{cpu_usage:.2f}%", start_time)

                if status == psutil.STATUS_RUNNING:
                    running += 1
                elif status == psutil.STATUS_SLEEPING:
                    sleeping += 1
                elif status == psutil.STATUS_ZOMBIE:
                    zombie += 1

                # Логирование информации о процессе
                logging.info(
                    f"PID: {pid}, Name: {name}, User: {username}, "
                    f"Status: {status}, Memory: {memory_usage:.2f} MB, "
                    f"CPU: {cpu_usage:.2f}%, Start Time: {start_time}"
                )

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                logging.warning(f"Cannot retrieve info for a process: {e}")
                continue

        # Обновление статистики
        current_time = time.strftime("%H:%M:%S")
        process_stats['time'].append(current_time)
        process_stats['running'].append(running)
        process_stats['sleeping'].append(sleeping)
        process_stats['zombie'].append(zombie)

        # Логирование сводной информации
        logging.info(f"Summary - Running: {running}, Sleeping: {sleeping}, Zombie: {zombie}")
        return processes
    except Exception as e:
        logging.error(f"Error while monitoring system: {e}", exc_info=True)
        return {}


def update_process_table():
    """Обновление таблицы процессов."""
    try:
        processes = monitor_system()
        existing_pids = {int(table.item(iid, 'values')[0]) for iid in table.get_children()}
        current_pids = set(processes.keys())

        # Добавляем новые процессы
        for pid in current_pids - existing_pids:
            table.insert("", "end", values=(pid, *processes[pid]))

        # Обновляем существующие процессы
        for item in table.get_children():
            pid = int(table.item(item, 'values')[0])
            if pid in current_pids:
                table.item(item, values=(pid, *processes[pid]))

        for item in table.get_children():
            pid = int(table.item(item, 'values')[0])
            if pid not in current_pids:
                table.delete(item)

        if monitoring_active:
            app.after(5000, update_process_table)
    except Exception as e:
        logging.error(f"Error while updating process table: {e}", exc_info=True)


def toggle_monitoring():
    """Включение/выключение мониторинга процессов."""
    global monitoring_active
    if start_button['text'] == "Начать мониторинг":
        monitoring_active = True
        logging.info("Monitoring started.")
        start_button.config(text="Остановить мониторинг")
        update_process_table()  # Запускаем обновление таблицы
    else:
        monitoring_active = False
        logging.info("Monitoring stopped.")
        start_button.config(text="Начать мониторинг")


def show_statistics():
    """Отображение или обновление графиков статистики процессов."""
    global current_canvas

    if current_canvas:
        current_canvas.get_tk_widget().destroy()

    figure = Figure(figsize=(10, 6), dpi=100)
    ax = figure.add_subplot(111)

    ax.plot(process_stats['time'], process_stats['running'], label='Running')
    ax.plot(process_stats['time'], process_stats['sleeping'], label='Sleeping')
    ax.plot(process_stats['time'], process_stats['zombie'], label='Zombie')

    ax.set_title("Process Statistics Over Time")
    ax.set_xlabel("Time")
    ax.set_ylabel("Process Count")
    ax.legend()

    current_canvas = FigureCanvasTkAgg(figure, master=stats_frame)
    current_canvas.draw()
    current_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    toolbar = NavigationToolbar2Tk(current_canvas, stats_frame)
    toolbar.update()
    current_canvas.get_tk_widget().pack()


# Создание основного окна
app = tk.Tk()
app.title("Мониторинг процессов")
app.geometry("1400x800")

# Создание вкладок
tabs = ttk.Notebook(app)
process_tab = ttk.Frame(tabs)
stats_tab = ttk.Frame(tabs)
tabs.add(process_tab, text="Процессы")
tabs.add(stats_tab, text="Статистика")
tabs.pack(fill=tk.BOTH, expand=True)

# Раздел для управления мониторингом
control_frame = ttk.Frame(process_tab)
control_frame.pack(side=tk.LEFT, padx=10, pady=10)

start_button = ttk.Button(control_frame, text="Начать мониторинг", command=toggle_monitoring)
start_button.pack(pady=10)

# Раздел для отображения таблицы процессов
table_frame = ttk.Frame(process_tab)
table_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

columns = ("PID", "Name", "User", "Status", "Memory", "CPU", "Start Time")
table = ttk.Treeview(table_frame, columns=columns, show="headings", height=30)
for col in columns:
    table.heading(col, text=col)
    table.column(col, width=150 if col != "Name" else 250)
table.pack(fill=tk.BOTH, expand=True)

# Раздел для отображения графиков
stats_frame = ttk.Frame(stats_tab)
stats_frame.pack(fill=tk.BOTH, expand=True)

stats_button = ttk.Button(stats_tab, text="Показать статистику", command=show_statistics)
stats_button.pack(pady=10)

# Запуск приложения
app.mainloop()
