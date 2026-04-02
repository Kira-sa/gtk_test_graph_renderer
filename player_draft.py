# snapshot.py
from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple, Optional
import pickle
from copy import deepcopy

@dataclass
class ParserSnapshot:
    """
    Снепшот состояния парсера для восстановления.
    Содержит всё, что нужно для продолжения парсинга с определённого места.
    """
    packet_index: int
    internal_state: Dict[str, Any]  # внутреннее состояние вашего парсера
    # Например: buffer, last_packet_crc, sequence_number, и т.д.
    
    def __init__(self, packet_index: int, parser_object):
        self.packet_index = packet_index
        # Здесь нужно сохранить внутреннее состояние вашего парсера
        # Пример:
        if hasattr(parser_object, 'get_state'):
            self.internal_state = parser_object.get_state()
        else:
            # Если парсер не предоставляет метод, сохраняем нужные атрибуты
            self.internal_state = {
                'buffer': getattr(parser_object, 'buffer', b''),
                'last_seq': getattr(parser_object, 'last_sequence', 0),
                'crc_errors': getattr(parser_object, 'crc_errors', 0),
                # добавьте ваши поля
            }
    
    def restore(self, parser_object):
        """Восстанавливает состояние парсера из снепшота"""
        for key, value in self.internal_state.items():
            setattr(parser_object, key, value)

@dataclass
class LabelState:
    """Состояние всех лейблов на момент пакета"""
    packet_index: int
    values: Dict[str, Any] = field(default_factory=dict)
    
    def update_from_packet(self, packet, packet_index: int):
        """Обновляет состояние на основе пакета"""
        self.packet_index = packet_index
        # Обновляем только те поля, которые присутствуют в пакете
        for attr_name in ['altitude', 'speed', 'heading', 'temperature', 'pressure']:
            if hasattr(packet, attr_name):
                self.values[attr_name] = getattr(packet, attr_name)
        
        # Добавьте ваши специфические поля
    
    def get_display_values(self) -> Dict[str, str]:
        """Возвращает словарь для отображения в лейблах"""
        result = {}
        for key, value in self.values.items():
            if isinstance(value, float):
                result[key] = f"{value:.2f}"
            else:
                result[key] = str(value)
        return result

@dataclass
class MapState:
    """Состояние карты (все точки маршрута)"""
    packet_index: int
    points: List[Tuple[float, float]] = field(default_factory=list)
    
    def add_point(self, lat: float, lon: float, packet_index: int):
        self.packet_index = packet_index
        self.points.append((lat, lon))
    
    def get_points_upto(self, packet_index: int) -> List[Tuple[float, float]]:
        """Возвращает все точки до указанного пакета"""
        # При снепшотах points хранит все точки до packet_index
        # Для перемотки нужно взять точки до целевого пакета
        return self.points[:packet_index + 1] if packet_index < len(self.points) else self.points


# snapshot_manager.py
import os
import pickle
from typing import Dict, List, Optional
from collections import OrderedDict

class SnapshotManager:
    """
    Управляет снепшотами парсера и состояний для быстрой перемотки.
    Снепшоты хранятся в памяти с ограничением на количество.
    """
    
    def __init__(self, snapshot_interval: int = 500, max_snapshots: int = 20):
        self.snapshot_interval = snapshot_interval
        self.max_snapshots = max_snapshots
        self.parser_snapshots: Dict[int, ParserSnapshot] = OrderedDict()
        self.label_snapshots: Dict[int, LabelState] = OrderedDict()
        self.map_snapshots: Dict[int, MapState] = OrderedDict()
    
    def take_snapshot(self, packet_index: int, parser, label_state: LabelState, map_state: MapState):
        """Создаёт снепшоты на указанном пакете"""
        if packet_index % self.snapshot_interval == 0:
            # Сохраняем снепшот парсера
            self.parser_snapshots[packet_index] = ParserSnapshot(packet_index, parser)
            
            # Сохраняем снепшот лейблов (глубокую копию)
            label_copy = LabelState(packet_index, label_state.values.copy())
            self.label_snapshots[packet_index] = label_copy
            
            # Сохраняем снепшот карты (копию списка точек)
            map_copy = MapState(packet_index, map_state.points.copy())
            self.map_snapshots[packet_index] = map_copy
            
            # Ограничиваем размер кэша
            while len(self.parser_snapshots) > self.max_snapshots:
                self.parser_snapshots.popitem(last=False)
            while len(self.label_snapshots) > self.max_snapshots:
                self.label_snapshots.popitem(last=False)
            while len(self.map_snapshots) > self.max_snapshots:
                self.map_snapshots.popitem(last=False)
    
    def get_nearest_snapshot(self, target_packet: int) -> Optional[int]:
        """Возвращает индекс ближайшего снепшота <= target_packet"""
        if not self.parser_snapshots:
            return None
        
        # Находим ближайший ключ <= target_packet
        snapshot_indices = sorted(self.parser_snapshots.keys())
        for idx in reversed(snapshot_indices):
            if idx <= target_packet:
                return idx
        return None
    
    def restore_from_snapshot(self, packet_index: int, parser, label_state: LabelState, map_state: MapState) -> int:
        """
        Восстанавливает состояние из ближайшего снепшота.
        Возвращает индекс пакета, с которого нужно продолжить воспроизведение.
        """
        snapshot_idx = self.get_nearest_snapshot(packet_index)
        
        if snapshot_idx is not None and snapshot_idx in self.parser_snapshots:
            # Восстанавливаем парсер
            self.parser_snapshots[snapshot_idx].restore(parser)
            
            # Восстанавливаем лейблы
            if snapshot_idx in self.label_snapshots:
                label_state.values = self.label_snapshots[snapshot_idx].values.copy()
                label_state.packet_index = snapshot_idx
            
            # Восстанавливаем карту
            if snapshot_idx in self.map_snapshots:
                map_state.points = self.map_snapshots[snapshot_idx].points.copy()
                map_state.packet_index = snapshot_idx
            
            return snapshot_idx + 1  # следующий пакет после снепшота
        else:
            # Нет снепшота - начинаем с нуля
            # Сбрасываем парсер в начальное состояние
            if hasattr(parser, 'reset'):
                parser.reset()
            label_state.values.clear()
            map_state.points.clear()
            return 0


# playback_engine.py
import threading
import time
from enum import Enum
from typing import Optional, Callable, Any
from gi.repository import GLib

class PlaybackState(Enum):
    STOPPED = 0
    PLAYING = 1
    PAUSED = 2
    SEEKING = 3  # состояние перемотки

class PlaybackEngine:
    """
    Движок воспроизведения для stateful парсера с поддержкой перемотки через снепшоты.
    """
    
    def __init__(self, parser_module, snapshot_interval: int = 500):
        self.parser = parser_module
        self.parser_instance = None  # будет создан при загрузке файла
        self.snapshot_manager = SnapshotManager(snapshot_interval)
        
        # Состояние
        self.filepath: Optional[str] = None
        self.packet_offsets: List[int] = []  # смещения всех пакетов в файле
        self.total_packets = 0
        self.current_packet_idx = 0
        
        # Текущие состояния
        self.current_label_state = LabelState(-1)
        self.current_map_state = MapState(-1)
        
        self.state = PlaybackState.STOPPED
        self.speed = 1.0
        self.base_rate_sec_per_packet = 0.1  # 10 пакетов/сек из ТЗ
        self._timer_id = None
        self._seek_thread = None
        
        # Callbacks для UI
        self.on_frame_update = None  # func(label_values: dict, points: list, progress: float)
        self.on_seek_progress = None  # func(percent: int) - для прогресс-бара перемотки
        self.on_finished = None
        self.on_state_changed = None
    
    def load_file(self, filepath: str, progress_callback: Optional[Callable[[int], None]] = None) -> bool:
        """
        Загружает файл, строит индекс пакетов и создаёт экземпляр парсера.
        """
        try:
            # Строим индекс пакетов
            self.packet_offsets = self._build_packet_index(filepath, progress_callback)
            self.total_packets = len(self.packet_offsets)
            self.filepath = filepath
            
            # Создаём свежий экземпляр парсера
            self.parser_instance = self.parser.PacketParser()  # предполагаем класс
            
            # Сбрасываем состояния
            self.snapshot_manager = SnapshotManager(self.snapshot_manager.snapshot_interval)
            self.current_label_state = LabelState(-1)
            self.current_map_state = MapState(-1)
            self.current_packet_idx = 0
            
            # Воспроизводим первый пакет для инициализации UI
            self._replay_from_packet(0, silent=False)
            
            return True
            
        except Exception as e:
            print(f"Ошибка загрузки: {e}")
            return False
    
    def _build_packet_index(self, filepath: str, progress_callback=None) -> List[int]:
        """
        Строит список смещений всех пакетов в файле.
        Адаптируйте под ваш протокол.
        """
        offsets = []
        file_size = os.path.getsize(filepath)
        
        with open(filepath, 'rb') as f:
            pos = 0
            while pos < file_size:
                # Ищем начало пакета (адаптируйте под ваш протокол)
                # Пример для протокола с заголовком 0xAA 0x55
                data = f.read(1)
                if not data:
                    break
                
                if data[0] == 0xAA:
                    # Проверяем следующий байт
                    next_byte = f.read(1)
                    if next_byte and next_byte[0] == 0x55:
                        # Нашли начало пакета
                        offsets.append(pos)
                        # Пропускаем пакет (нужно знать его длину)
                        # Упрощённо: читаем до 0xBB
                        while True:
                            b = f.read(1)
                            if not b or b[0] == 0xBB:
                                break
                        pos = f.tell()
                    else:
                        pos += 1
                        f.seek(pos)
                else:
                    pos += 1
                    f.seek(pos)
                
                if progress_callback and len(offsets) % 100 == 0:
                    progress_callback(int((pos / file_size) * 100))
        
        return offsets
    
    def _read_packet(self, index: int) -> Optional[bytes]:
        """Читает пакет из файла по индексу"""
        if index >= len(self.packet_offsets):
            return None
        
        with open(self.filepath, 'rb') as f:
            f.seek(self.packet_offsets[index])
            # Читаем до маркера конца пакета (адаптируйте)
            data = []
            while True:
                byte = f.read(1)
                if not byte:
                    break
                data.append(byte)
                if byte[0] == 0xBB:  # конец пакета
                    break
            return b''.join(data)
    
    def _replay_from_packet(self, start_index: int, silent: bool = False, 
                           target_index: Optional[int] = None, 
                           progress_callback: Optional[Callable[[int], None]] = None):
        """
        Воспроизводит пакеты от start_index до target_index (или до конца).
        Если silent=True, не вызывает UI-колбэки (только для восстановления состояния).
        """
        if target_index is None:
            target_index = self.total_packets - 1
        
        total_to_process = target_index - start_index + 1
        
        for i, idx in enumerate(range(start_index, target_index + 1)):
            raw_packet = self._read_packet(idx)
            if raw_packet:
                # Парсим пакет (обновляет внутреннее состояние парсера)
                parsed = self.parser_instance.parse(raw_packet)
                if parsed:
                    # Обновляем состояния
                    self.current_label_state.update_from_packet(parsed, idx)
                    if hasattr(parsed, 'latitude') and hasattr(parsed, 'longitude'):
                        self.current_map_state.add_point(parsed.latitude, parsed.longitude, idx)
                    
                    # Создаём снепшоты
                    self.snapshot_manager.take_snapshot(
                        idx, self.parser_instance, 
                        self.current_label_state, 
                        self.current_map_state
                    )
                    
                    # Уведомляем UI (если не silent)
                    if not silent and self.on_frame_update:
                        fraction = idx / self.total_packets
                        self.on_frame_update(
                            self.current_label_state.get_display_values(),
                            self.current_map_state.get_points_upto(idx),
                            fraction
                        )
            
            # Прогресс перемотки
            if progress_callback and i % 10 == 0:
                percent = int((i + 1) / total_to_process * 100)
                GLib.idle_add(progress_callback, percent)
    
    def _seek_async(self, target_packet_idx: int):
        """
        Асинхронная перемотка в отдельном потоке.
        """
        try:
            # Уведомляем о начале перемотки
            GLib.idle_add(self._notify_seek_start)
            
            # Восстанавливаем из ближайшего снепшота
            restore_start = self.snapshot_manager.restore_from_snapshot(
                target_packet_idx,
                self.parser_instance,
                self.current_label_state,
                self.current_map_state
            )
            
            # Доигрываем до целевого пакета
            def seek_progress(percent):
                GLib.idle_add(self.on_seek_progress, percent) if self.on_seek_progress else None
            
            self._replay_from_packet(
                restore_start, 
                silent=False,  # обновляем UI в процессе
                target_index=target_packet_idx,
                progress_callback=seek_progress
            )
            
            self.current_packet_idx = target_packet_idx
            
            # Завершаем перемотку
            GLib.idle_add(self._notify_seek_end)
            
        except Exception as e:
            print(f"Ошибка перемотки: {e}")
            GLib.idle_add(self._notify_seek_end)
    
    def _notify_seek_start(self):
        self.state = PlaybackState.SEEKING
        if self.on_state_changed:
            self.on_state_changed(self.state)
    
    def _notify_seek_end(self):
        if self.state == PlaybackState.SEEKING:
            # Если после перемотки не было вызова play/pause, останавливаем
            self.state = PlaybackState.STOPPED
        if self.on_state_changed:
            self.on_state_changed(self.state)
        if self.on_seek_progress:
            self.on_seek_progress(100)
    
    def seek(self, fraction: float):
        """
        Перемотка на позицию (0..1).
        Выполняется асинхронно, чтобы не блокировать UI.
        """
        if not self.total_packets:
            return
        
        target_idx = int(fraction * self.total_packets)
        target_idx = max(0, min(target_idx, self.total_packets - 1))
        
        # Останавливаем текущее воспроизведение
        was_playing = (self.state == PlaybackState.PLAYING)
        self.pause()
        
        # Запускаем перемотку в отдельном потоке
        if self._seek_thread and self._seek_thread.is_alive():
            # Ждём завершения предыдущей перемотки (упрощённо)
            pass
        
        self._seek_thread = threading.Thread(
            target=self._seek_async,
            args=(target_idx,),
            daemon=True
        )
        self._seek_thread.start()
        
        # Если нужно продолжить воспроизведение после перемотки
        if was_playing:
            # Сохраняем флаг, но не стартуем до завершения перемотки
            def start_after_seek():
                if not self._seek_thread.is_alive():
                    self.play()
                else:
                    GLib.timeout_add(100, start_after_seek)
            GLib.timeout_add(100, start_after_seek)
    
    def _timer_callback(self) -> bool:
        """Таймер воспроизведения в главном потоке"""
        if self.state != PlaybackState.PLAYING:
            return False
        
        if self.current_packet_idx >= self.total_packets - 1:
            self.stop()
            if self.on_finished:
                self.on_finished()
            return False
        
        # Обрабатываем следующий пакет
        next_idx = self.current_packet_idx + 1
        raw_packet = self._read_packet(next_idx)
        if raw_packet:
            parsed = self.parser_instance.parse(raw_packet)
            if parsed:
                self.current_label_state.update_from_packet(parsed, next_idx)
                if hasattr(parsed, 'latitude') and hasattr(parsed, 'longitude'):
                    self.current_map_state.add_point(parsed.latitude, parsed.longitude, next_idx)
                
                self.snapshot_manager.take_snapshot(
                    next_idx, self.parser_instance,
                    self.current_label_state,
                    self.current_map_state
                )
                
                self.current_packet_idx = next_idx
                
                # Обновляем UI
                if self.on_frame_update:
                    fraction = self.current_packet_idx / self.total_packets
                    self.on_frame_update(
                        self.current_label_state.get_display_values(),
                        self.current_map_state.get_points_upto(self.current_packet_idx),
                        fraction
                    )
        
        return True
    
    def play(self):
        if self.state == PlaybackState.SEEKING:
            # Ждём окончания перемотки
            def delayed_play():
                if self.state != PlaybackState.SEEKING:
                    self.play()
                else:
                    GLib.timeout_add(100, delayed_play)
            GLib.timeout_add(100, delayed_play)
            return
        
        if self.state == PlaybackState.PLAYING:
            return
        
        self.state = PlaybackState.PLAYING
        self._schedule_timer()
        if self.on_state_changed:
            self.on_state_changed(self.state)
    
    def pause(self):
        if self.state == PlaybackState.PLAYING:
            self.state = PlaybackState.PAUSED
            if self._timer_id:
                GLib.source_remove(self._timer_id)
                self._timer_id = None
            if self.on_state_changed:
                self.on_state_changed(self.state)
    
    def stop(self):
        self.pause()
        self.state = PlaybackState.STOPPED
        self.current_packet_idx = 0
        self._replay_from_packet(0, silent=False)
        if self.on_state_changed:
            self.on_state_changed(self.state)
    
    def set_speed(self, speed: float):
        self.speed = max(0.1, min(10.0, speed))  # ограничиваем 0.1x - 10x
        # Скорость применяется через интервал таймера
        if self.state == PlaybackState.PLAYING:
            self._schedule_timer()
    
    def _schedule_timer(self):
        if self._timer_id:
            GLib.source_remove(self._timer_id)
        
        # Интервал в миллисекундах с учётом скорости
        interval_ms = int((self.base_rate_sec_per_packet / self.speed) * 1000)
        interval_ms = max(10, min(500, interval_ms))  # ограничиваем 10-500 мс
        self._timer_id = GLib.timeout_add(interval_ms, self._timer_callback)


# main_window_integration.py (фрагмент)
class MainWindow:
    def __init__(self, builder, parser_module):
        self.builder = builder
        self.playback = PlaybackEngine(parser_module, snapshot_interval=500)
        
        # Подключаем колбэки
        self.playback.on_frame_update = self.update_display
        self.playback.on_seek_progress = self.update_seek_progress
        self.playback.on_finished = self.on_playback_finished
        self.playback.on_state_changed = self.on_state_changed
        
        # UI элементы
        self.play_button = builder.get_object("play_button")
        self.pause_button = builder.get_object("pause_button")
        self.stop_button = builder.get_object("stop_button")
        self.speed_spin = builder.get_object("speed_spin")  # GtkSpinButton
        self.seek_scale = builder.get_object("seek_scale")  # GtkScale
        self.seek_progress = builder.get_object("seek_progress")  # GtkProgressBar
        
        # Лейблы (пример)
        self.labels = {
            'altitude': builder.get_object("altitude_label"),
            'speed': builder.get_object("speed_label"),
            'heading': builder.get_object("heading_label"),
        }
        
        # Карта (ваш виджет)
        self.map_widget = builder.get_object("map_widget")
        
        # Сигналы
        self.play_button.connect("clicked", lambda _: self.playback.play())
        self.pause_button.connect("clicked", lambda _: self.playback.pause())
        self.stop_button.connect("clicked", lambda _: self.playback.stop())
        self.speed_spin.connect("value-changed", self.on_speed_changed)
        self.seek_scale.connect("change-value", self.on_seek)
    
    def update_display(self, label_values: dict, points: list, progress: float):
        """Обновляет UI в главном потоке"""
        # Обновляем лейблы
        for key, label in self.labels.items():
            value = label_values.get(key, '---')
            label.set_text(str(value))
        
        # Обновляем карту (полностью)
        self.map_widget.set_points(points)
        self.map_widget.queue_draw()
        
        # Обновляем позицию скролла
        self.seek_scale.set_value(progress)
    
    def update_seek_progress(self, percent: int):
        """Обновляет прогресс-бар перемотки"""
        if percent >= 100:
            self.seek_progress.hide()
        else:
            self.seek_progress.show()
            self.seek_progress.set_fraction(percent / 100)
    
    def on_seek(self, scale, scroll, value):
        if self.playback.total_packets > 0:
            self.playback.seek(value)
    
    def on_speed_changed(self, spin):
        speed = spin.get_value()
        self.playback.set_speed(speed)
    
    def on_state_changed(self, state):
        is_playing = (state == PlaybackState.PLAYING)
        is_seeking = (state == PlaybackState.SEEKING)
        
        self.play_button.set_sensitive(not is_playing and not is_seeking)
        self.pause_button.set_sensitive(is_playing)
        self.stop_button.set_sensitive(not is_seeking)
        self.seek_scale.set_sensitive(not is_seeking)
    
    def on_playback_finished(self):
        self.play_button.set_sensitive(True)
        self.pause_button.set_sensitive(False)