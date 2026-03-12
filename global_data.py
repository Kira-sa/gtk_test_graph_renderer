#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль глобальных данных для тестового приложения.
Содержит данные графика и ссылку на canvas для обновления.
"""

from typing import List, Tuple, Optional
import math
import random

# Глобальные переменные (да, это "плохая практика", но для первого способа - ок)
_canvas_widget = None
_data_points = [(10, 20), (20, 40), (30, 25), (40, 60), (50, 45), (60, 30), (70, 55), (80, 35), (90, 70)]

# Для отладки - считаем количество обновлений
_update_counter = 0


def set_canvas(widget) -> None:
    """
    Регистрирует виджет canvas для последующего автоматического обновления.
    
    Args:
        widget: Gtk.DrawingArea виджет
    """
    global _canvas_widget
    _canvas_widget = widget
    print(f"[global_data] Canvas зарегистрирован: {widget}")


def get_points() -> List[Tuple[float, float]]:
    """
    Возвращает копию текущих точек графика.
    
    Returns:
        List[Tuple[float, float]]: Список координат (x, y)
    """
    return _data_points.copy()


def get_points_count() -> int:
    """Возвращает количество точек."""
    return len(_data_points)


def update_points(new_points: List[Tuple[float, float]]) -> None:
    """
    Обновляет данные графика и вызывает перерисовку canvas.
    
    Args:
        new_points: Новый список точек
    """
    global _data_points, _update_counter
    _data_points = new_points
    _update_counter += 1
    
    print(f"[global_data] Данные обновлены. Новая версия #{_update_counter}, точек: {len(new_points)}")
    
    # Инициируем перерисовку, если canvas зарегистрирован
    if _canvas_widget is not None:
        print(f"[global_data] Запрашиваем перерисовку canvas")
        _canvas_widget.queue_draw()
    else:
        print(f"[global_data] ВНИМАНИЕ: Canvas не зарегистрирован! График не обновится.")


def generate_random_points(count: int = 15) -> List[Tuple[float, float]]:
    """
    Генерирует случайные точки для тестирования.
    
    Args:
        count: Количество точек
        
    Returns:
        List[Tuple[float, float]]: Список случайных точек
    """
    points = []
    for i in range(count):
        x = i * (100 / max(1, count - 1))  # Равномерно распределяем по X от 0 до 100
        y = random.randint(10, 90)
        points.append((x, y))
    return points


def generate_sine_wave(points_count: int = 50) -> List[Tuple[float, float]]:
    """
    Генерирует синусоиду.
    
    Args:
        points_count: Количество точек
        
    Returns:
        List[Tuple[float, float]]: Точки синусоиды
    """
    points = []
    for i in range(points_count):
        x = i * (100 / max(1, points_count - 1))
        # Синусоида с амплитудой 40 и смещением 50 (чтобы была в центре)
        y = 50 + 40 * math.sin(i * 0.3)
        points.append((x, y))
    return points


def clear_points() -> None:
    """Очищает все точки (устанавливает пустой список)."""
    update_points([])


def add_point(x: float, y: float) -> None:
    """
    Добавляет одну точку к существующему графику.
    
    Args:
        x: Координата X
        y: Координата Y
    """
    new_points = _data_points.copy()
    new_points.append((x, y))
    update_points(new_points)


def get_stats() -> dict:
    """
    Возвращает статистику по текущим данным.
    
    Returns:
        dict: Статистика
    """
    if not _data_points:
        return {"count": 0, "min_y": None, "max_y": None, "avg_y": None}
    
    y_values = [y for _, y in _data_points]
    return {
        "count": len(_data_points),
        "min_y": min(y_values),
        "max_y": max(y_values),
        "avg_y": sum(y_values) / len(y_values),
        "update_counter": _update_counter
    }