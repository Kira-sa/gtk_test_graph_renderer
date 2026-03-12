#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для отрисовки графиков на Cairo контексте.
Не зависит от глобальных данных, получает всё через параметры.
"""

from typing import List, Tuple, Optional
import math


class GraphRenderer:
    """
    Класс для отрисовки графиков.
    Содержит настройки внешнего вида и методы рисования.
    """
    
    def __init__(self, 
                 line_color: Tuple[float, float, float, float] = (0.2, 0.6, 1.0, 1.0),
                 line_width: float = 2.5,
                 point_color: Tuple[float, float, float, float] = (1.0, 0.2, 0.2, 1.0),
                 point_radius: float = 3.0,
                 axes_color: Tuple[float, float, float, float] = (0.7, 0.7, 0.7, 1.0),
                 grid_color: Tuple[float, float, float, float] = (0.9, 0.9, 0.9, 1.0),
                 background_color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)):
        """
        Инициализация рендерера с настройками внешнего вида.
        
        Args:
            line_color: Цвет линии графика (RGBA)
            line_width: Толщина линии
            point_color: Цвет точек
            point_radius: Радиус точек
            axes_color: Цвет осей
            grid_color: Цвет сетки
            background_color: Цвет фона
        """
        self.line_color = line_color
        self.line_width = line_width
        self.point_color = point_color
        self.point_radius = point_radius
        self.axes_color = axes_color
        self.grid_color = grid_color
        self.background_color = background_color
        
        # Отступы от краёв холста (для осей и подписей)
        self.margin_left = 50
        self.margin_right = 30
        self.margin_top = 30
        self.margin_bottom = 50
    
    def draw(self, cr, width: int, height: int, data_points: List[Tuple[float, float]]) -> None:
        """
        Основной метод рисования.
        
        Args:
            cr: Cairo context
            width: Ширина области рисования
            height: Высота области рисования
            data_points: Список точек для отрисовки
        """
        # Очищаем фон
        self._draw_background(cr, width, height)
        
        if not data_points:
            self._draw_no_data_message(cr, width, height)
            return
        
        # Рисуем сетку
        self._draw_grid(cr, width, height)
        
        # Рисуем оси
        self._draw_axes(cr, width, height)
        
        # Рисуем линии графика
        self._draw_lines(cr, width, height, data_points)
        
        # Рисуем точки
        self._draw_points(cr, width, height, data_points)
        
        # Рисуем подписи
        self._draw_labels(cr, width, height, data_points)
    
    def _draw_background(self, cr, width: int, height: int) -> None:
        """Рисует фон."""
        cr.set_source_rgba(*self.background_color)
        cr.rectangle(0, 0, width, height)
        cr.fill()
    
    def _draw_no_data_message(self, cr, width: int, height: int) -> None:
        """Рисует сообщение об отсутствии данных."""
        cr.set_source_rgba(0.5, 0.5, 0.5, 1.0)
        cr.set_font_size(16)
        
        text = "Нет данных для отображения"
        x_bearing, y_bearing, text_width, text_height = cr.text_extents(text)[:4]
        cr.move_to(width/2 - text_width/2, height/2)
        cr.show_text(text)
    
    def _transform_coordinates(self, x: float, y: float, width: int, height: int) -> Tuple[float, float]:
        """
        Преобразует координаты данных (0-100) в координаты холста с учётом отступов.
        
        Args:
            x: X в координатах данных (0-100)
            y: Y в координатах данных (0-100)
            width: Ширина холста
            height: Высота холста
            
        Returns:
            Tuple[float, float]: Координаты на холсте
        """
        # Область рисования графика (с учётом отступов)
        plot_width = width - self.margin_left - self.margin_right
        plot_height = height - self.margin_top - self.margin_bottom
        
        # Масштабируем и смещаем
        canvas_x = self.margin_left + (x / 100.0) * plot_width
        # Инвертируем Y (в GTK/Cairo Y идёт сверху вниз)
        canvas_y = self.margin_top + plot_height - (y / 100.0) * plot_height
        
        return canvas_x, canvas_y
    
    def _draw_lines(self, cr, width: int, height: int, points: List[Tuple[float, float]]) -> None:
        """Рисует линии графика."""
        if len(points) < 2:
            return
        
        cr.set_source_rgba(*self.line_color)
        cr.set_line_width(self.line_width)
        cr.set_line_join(cr.LINE_JOIN_ROUND)
        cr.set_line_cap(cr.LINE_CAP_ROUND)
        
        # Рисуем линию
        first = True
        for x, y in points:
            canvas_x, canvas_y = self._transform_coordinates(x, y, width, height)
            
            if first:
                cr.move_to(canvas_x, canvas_y)
                first = False
            else:
                cr.line_to(canvas_x, canvas_y)
        
        cr.stroke()
    
    def _draw_points(self, cr, width: int, height: int, points: List[Tuple[float, float]]) -> None:
        """Рисует точки графика."""
        cr.set_source_rgba(*self.point_color)
        
        for x, y in points:
            canvas_x, canvas_y = self._transform_coordinates(x, y, width, height)
            
            # Рисуем круг
            cr.arc(canvas_x, canvas_y, self.point_radius, 0, 2 * math.pi)
            cr.fill()
    
    def _draw_grid(self, cr, width: int, height: int) -> None:
        """Рисует сетку."""
        cr.set_source_rgba(*self.grid_color)
        cr.set_line_width(0.5)
        
        plot_width = width - self.margin_left - self.margin_right
        plot_height = height - self.margin_top - self.margin_bottom
        
        # Вертикальные линии (каждые 10% от 0 до 100)
        for i in range(0, 101, 10):
            x = self.margin_left + (i / 100.0) * plot_width
            cr.move_to(x, self.margin_top)
            cr.line_to(x, self.margin_top + plot_height)
        
        # Горизонтальные линии (каждые 10% от 0 до 100)
        for i in range(0, 101, 10):
            y = self.margin_top + plot_height - (i / 100.0) * plot_height
            cr.move_to(self.margin_left, y)
            cr.line_to(self.margin_left + plot_width, y)
        
        cr.stroke()
    
    def _draw_axes(self, cr, width: int, height: int) -> None:
        """Рисует оси координат."""
        cr.set_source_rgba(*self.axes_color)
        cr.set_line_width(1.5)
        
        plot_width = width - self.margin_left - self.margin_right
        plot_height = height - self.margin_top - self.margin_bottom
        
        # Ось X
        cr.move_to(self.margin_left, self.margin_top + plot_height)
        cr.line_to(self.margin_left + plot_width, self.margin_top + plot_height)
        
        # Ось Y
        cr.move_to(self.margin_left, self.margin_top)
        cr.line_to(self.margin_left, self.margin_top + plot_height)
        
        # Стрелочки на осях
        arrow_size = 8
        
        # Стрелка на оси X
        cr.move_to(self.margin_left + plot_width - arrow_size, self.margin_top + plot_height - arrow_size/2)
        cr.line_to(self.margin_left + plot_width, self.margin_top + plot_height)
        cr.line_to(self.margin_left + plot_width - arrow_size, self.margin_top + plot_height + arrow_size/2)
        
        # Стрелка на оси Y
        cr.move_to(self.margin_left - arrow_size/2, self.margin_top + arrow_size)
        cr.line_to(self.margin_left, self.margin_top)
        cr.line_to(self.margin_left + arrow_size/2, self.margin_top + arrow_size)
        
        cr.stroke()
    
    def _draw_labels(self, cr, width: int, height: int, points: List[Tuple[float, float]]) -> None:
        """Рисует подписи осей и значения."""
        cr.set_source_rgba(0.2, 0.2, 0.2, 1.0)
        cr.set_font_size(10)
        
        plot_width = width - self.margin_left - self.margin_right
        plot_height = height - self.margin_top - self.margin_bottom
        
        # Подписи по оси X (каждые 20%)
        for i in range(0, 101, 20):
            x = self.margin_left + (i / 100.0) * plot_width
            label = str(i)
            
            x_bearing, y_bearing, text_width, text_height = cr.text_extents(label)[:4]
            cr.move_to(x - text_width/2, self.margin_top + plot_height + 20)
            cr.show_text(label)
        
        # Подписи по оси Y (каждые 20%)
        for i in range(0, 101, 20):
            y = self.margin_top + plot_height - (i / 100.0) * plot_height
            label = str(i)
            
            x_bearing, y_bearing, text_width, text_height = cr.text_extents(label)[:4]
            cr.move_to(self.margin_left - text_width - 10, y - text_height/2)
            cr.show_text(label)
        
        # Подписи осей
        cr.set_font_size(12)
        cr.set_source_rgba(0, 0, 0, 1.0)
        
        # Подпись оси X
        cr.move_to(width - 30, height - 10)
        cr.show_text("X →")
        
        # Подпись оси Y
        cr.move_to(15, 20)
        cr.show_text("↑ Y")