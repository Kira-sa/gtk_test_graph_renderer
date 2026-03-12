#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тестовое приложение для демонстрации первого способа (ручной queue_draw).

Это приложение показывает график и позволяет управлять им через кнопки.
Данные хранятся в глобальном модуле, canvas регистрируется для автообновления.
"""

import sys
import math
import random
from typing import Optional

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

# Импортируем наши модули
import global_data
from renderers.graph_renderer import GraphRenderer


class TestApp:
    """
    Главный класс тестового приложения.
    """
    
    def __init__(self, glade_file: str = "test_window.glade"):
        """
        Инициализация приложения.
        
        Args:
            glade_file: Путь к файлу с UI
        """
        print("=" * 50)
        print("ЗАПУСК ТЕСТОВОГО ПРИЛОЖЕНИЯ (Способ 1 - ручной queue_draw)")
        print("=" * 50)
        
        # Загружаем UI из Glade
        self.builder = Gtk.Builder()
        try:
            self.builder.add_from_file(glade_file)
            print(f"[OK] Файл {glade_file} загружен")
        except Exception as e:
            print(f"[ERROR] Не удалось загрузить {glade_file}: {e}")
            print("Создаём UI программно (fallback)...")
            self._create_ui_fallback()
            return
        
        # Получаем виджеты
        self.window = self.builder.get_object("main_window")
        self.drawing_area = self.builder.get_object("drawing_area")
        self.statusbar = self.builder.get_object("statusbar")
        
        if not self.drawing_area:
            print("[ERROR] Не найден drawing_area в UI файле!")
            sys.exit(1)
        
        # Настройки для анимации
        self.animation_running = False
        self.animation_id = None
        
        # Создаём рендерер с красивыми настройками
        self.renderer = GraphRenderer(
            line_color=(0.2, 0.6, 1.0, 1.0),    # Синий
            line_width=2.5,
            point_color=(1.0, 0.2, 0.2, 1.0),   # Красный
            point_radius=4.0,
            axes_color=(0.3, 0.3, 0.3, 1.0),    # Тёмно-серый
            grid_color=(0.85, 0.85, 0.85, 1.0),  # Светло-серый
            background_color=(1.0, 1.0, 1.0, 1.0)  # Белый
        )
        
        # Регистрируем canvas в глобальном модуле (ключевой момент!)
        global_data.set_canvas(self.drawing_area)
        print(f"[OK] Canvas зарегистрирован в global_data")
        
        # Подключаем сигналы из Glade
        self.builder.connect_signals(self)
        
        # Показываем окно
        self.window.show_all()
        
        # Обновляем статус
        self._update_status()
        
        print("[OK] Приложение инициализировано")
        print("=" * 50)
    
    def _create_ui_fallback(self):
        """
        Создаёт UI программно, если не удалось загрузить из Glade.
        """
        self.window = Gtk.Window(title="Тест графиков (Fallback)")
        self.window.set_default_size(800, 600)
        self.window.connect("destroy", self.on_destroy)
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.window.add(vbox)
        
        # Drawing area
        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_hexpand(True)
        self.drawing_area.set_vexpand(True)
        self.drawing_area.connect("draw", self.on_draw)
        vbox.pack_start(self.drawing_area, True, True, 0)
        
        # Кнопки
        button_box = Gtk.Box(spacing=6, homogeneous=True)
        vbox.pack_start(button_box, False, False, 6)
        
        buttons = [
            ("🎲 Случайные", self.on_random_clicked),
            ("📈 Синусоида", self.on_sine_clicked),
            ("🗑️ Очистить", self.on_clear_clicked),
            ("🎬 Анимация", self.on_animate_clicked),
            ("🚪 Выход", self.on_exit_clicked)
        ]
        
        for label, handler in buttons:
            btn = Gtk.Button(label=label)
            btn.connect("clicked", handler)
            button_box.pack_start(btn, True, True, 0)
        
        # Статусбар
        self.statusbar = Gtk.Statusbar()
        vbox.pack_start(self.statusbar, False, False, 3)
        
        # Регистрируем canvas
        global_data.set_canvas(self.drawing_area)
        
        self.window.show_all()
    
    def on_draw(self, widget, cr):
        """
        Обработчик события отрисовки.
        Вызывается GTK при необходимости перерисовать виджет.
        
        Args:
            widget: Gtk.DrawingArea
            cr: Cairo context
            
        Returns:
            bool: False (чтобы GTK продолжил обработку)
        """
        # Получаем размеры виджета
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        
        # Получаем данные из глобального модуля
        points = global_data.get_points()
        points_count = len(points)
        
        # Рисуем график
        self.renderer.draw(cr, width, height, points)
        
        # Обновляем статус
        self._update_status()
        
        # Небольшая отладочная информация
        print(f"[draw] Отрисовано {points_count} точек")
        
        return False
    
    def _update_status(self):
        """Обновляет текст в статусной строке."""
        if not self.statusbar:
            return
        
        stats = global_data.get_stats()
        context_id = self.statusbar.get_context_id("graph")
        self.statusbar.pop(context_id)
        
        if stats["count"] == 0:
            text = "Нет данных для отображения"
        else:
            text = (f"Точек: {stats['count']} | "
                   f"Y: мин={stats['min_y']:.1f} макс={stats['max_y']:.1f} "
                   f"сред={stats['avg_y']:.1f} | "
                   f"Обновлений: {stats['update_counter']}")
        
        self.statusbar.push(context_id, text)
    
    # === Обработчики кнопок ===
    
    def on_random_clicked(self, button):
        """Обработчик кнопки 'Случайные данные'."""
        print("\n[ACTION] Генерация случайных данных")
        points = global_data.generate_random_points(random.randint(5, 20))
        global_data.update_points(points)
        # Не нужно вызывать queue_draw() - update_points сделает это!
    
    def on_sine_clicked(self, button):
        """Обработчик кнопки 'Синусоида'."""
        print("\n[ACTION] Генерация синусоиды")
        points = global_data.generate_sine_wave(50)
        global_data.update_points(points)
    
    def on_clear_clicked(self, button):
        """Обработчик кнопки 'Очистить'."""
        print("\n[ACTION] Очистка графика")
        global_data.clear_points()
    
    def on_animate_clicked(self, button):
        """Обработчик кнопки 'Анимация'."""
        if self.animation_running:
            # Останавливаем анимацию
            self.animation_running = False
            if self.animation_id:
                GLib.source_remove(self.animation_id)
                self.animation_id = None
            button.set_label("🎬 Анимация")
            print("[ACTION] Анимация остановлена")
        else:
            # Запускаем анимацию
            self.animation_running = True
            button.set_label("⏹️ Стоп")
            print("[ACTION] Анимация запущена")
            self._start_animation()
    
    def _start_animation(self):
        """Запускает анимацию - движущуюся синусоиду."""
        
        def animate():
            if not self.animation_running:
                return False
            
            # Получаем текущие точки или создаём новые
            points = global_data.get_points()
            if not points:
                points = global_data.generate_sine_wave(50)
            
            # Сдвигаем фазу синусоиды
            new_points = []
            phase = getattr(self, '_animation_phase', 0)
            phase += 0.2
            
            for i, (x, _) in enumerate(points):
                y = 50 + 40 * math.sin(i * 0.3 + phase)
                new_points.append((x, y))
            
            self._animation_phase = phase
            global_data.update_points(new_points)
            
            # Продолжаем анимацию
            return True
        
        # Запускаем таймер на 50 мс (20 кадров в секунду)
        self.animation_id = GLib.timeout_add(50, animate)
    
    def on_exit_clicked(self, button):
        """Обработчик кнопки 'Выход'."""
        print("\n[ACTION] Выход из приложения")
        self.on_destroy(button)
    
    def on_destroy(self, widget):
        """Обработчик закрытия окна."""
        print("\n[INFO] Завершение работы...")
        if self.animation_id:
            GLib.source_remove(self.animation_id)
        Gtk.main_quit()


def main():
    """Точка входа в приложение."""
    app = TestApp()
    Gtk.main()


if __name__ == "__main__":
    main()