import flet as ft
import flet_audio as fa
import os
import random
import math
import time
import threading

#настя
class EqualizerAnimation(ft.Container):
    #конструктор класса, задаём ширину, высоту и количество полосок
    def __init__(self, width=300, height=265, bars=8):
        #вызываем конструктор родительского класса ft.Container, чтобы унаследовать его возможности
        super().__init__()
        #задаём ширину контейнера эквалайзера
        self.width = width
        #высоту
        self.height = height
        #кол-во полосок
        self.bars = bars
        #флаг, показывает, запущена ли анимация (изначально False, то есть выключена)
        self.running = False
        #переменная для хранения объекта таймера, который управляет анимацией (пока None)
        self._timer = None
        #создаём список полосок эквалайзера, каждая — объект ft.Container
        self.bar_rects = [
            #каждая полоска - контейнер с заданными параметрами
            ft.Container(
                #ширина полоски: делим ширину контейнера на (кол-во полосок + 2), чтобы оставить отступы
                width=width // (bars + 2),
                #начальная высота полоски — 30 пикселей, минимальная высота для старта анимации
                height=30,
                bgcolor=ft.Colors.PURPLE_ACCENT_400,
                #скругляем углы полоски на 6 пикселей
                border_radius=ft.border_radius.all(6),
                #выравниваем полоску по нижнему центру, чтобы она росла вверх
                alignment=ft.alignment.bottom_center,
                #убираем горизонтальные отступы, чтобы полоски стояли вплотную
                margin=ft.margin.symmetric(horizontal=0)
            ) for _ in range(bars)  #создаём полоски
        ]
        #задаём содержимое контейнера - ряд ft.Row из полосок
        self.content = ft.Row(
            #передаём список полосок как дочерние элементы ряда
            controls=self.bar_rects,
            #выравниваем полоски по левому краю ряда
            alignment=ft.MainAxisAlignment.START,
            #выравниваем полоски по нижнему краю, чтобы они росли вверх при анимации
            vertical_alignment=ft.CrossAxisAlignment.END,
            #ширина ряда = ширине контейнера
            width=width,
            #высота ряда = высоте контейнера
            height=height
        )

    #метод, который анимирует полоски, меняя их высоту по синусоиде
    def _animate(self):
        #если анимация не запущена, выходим
        if not self.running:
            return
        #берём текущее время в секундах для синхронизации анимации
        t = time.time()
        #проходим по каждой полоске и её индексу в списке
        for i, bar in enumerate(self.bar_rects):
            #меняем высоту полоски: базовая высота 30 + амплитуда 100 * |sin(t * 2 + i)|
            #t * 2 ускоряет анимацию, i создаёт смещение для каждой полоски, чтобы они двигались волной
            bar.height = 30 + 100 * abs(math.sin(t * 2 + i))
        #обновляем интерфейс, чтобы изменения высоты полосок отобразились
        self.update()
        #создаём таймер, который вызовет _animate снова через 0.05 с для плавной анимации
        self._timer = threading.Timer(0.05, self._animate)
        #запускаем таймер, чтобы анимация продолжалась
        self._timer.start()

    #метод для запуска анимации эквалайзера
    def start(self):
        #проверяем, не запущена ли анимация, чтобы не дублировать таймеры
        if not self.running:
            #включаем флаг анимации
            self.running = True
            #запускаем метод анимации
            self._animate()

    #метод для остановки анимации
    def stop(self):
        #выключаем флаг анимации, чтобы остановить цикл
        self.running = False
        #если таймер существует, отменяем его
        if self._timer:
            self._timer.cancel()
            #сбрасываем таймер
            self._timer = None

#настя
#для управления логикой: воспроизведение, переключение, повтор, перемешивание
class AudioPlayerManager:
    #конструктор класса, инициализируем плеер и его параметры
    def __init__(self, page, ui):
        #задаём начальное состояние плеера - на паузе
        self.current_state = ft.AudioState.PAUSED
        #задаём индекс текущего трека (начинаем с первого, индекс 0)
        self.current_track_index = 0
        #режим повтора трека изначально выключен
        self.repeat_mode = False
        #режим перемешивания треков изначально выключен
        self.shuffle_mode = False
        #папка, где хранятся треки
        self.tracks_folder = "tracks"
        #загружаем треки из папки в плейлист
        self.original_playlist = self.load_local_tracks()
        #создаём рабочую копию плейлиста, чтобы не ломать исходный при перемешивании
        self.playlist = self.original_playlist.copy()
        #создаём словарь для подсчёта прослушиваний каждого трека (изначально 0)
        self.play_counts = {track["title"]: 0 for track in self.original_playlist}
        #создаём объект аудиоплеера из библиотеки flet_audio
        self.audio_player = fa.Audio(
            #автозапуск выключен, чтобы трек не играл сразу при загрузке
            autoplay=False,
            #привязываем метод для обработки изменения состояния (играет, пауза, остановлен)
            on_state_changed=self.audio_state_changed,
            #привязываем метод для обработки изменения позиции трека (для слайдера)
            on_position_changed=self.audio_position_changed,
            #привязываем метод для обработки загрузки трека (для установки длительности)
            on_loaded=self.audio_loaded,
            #задаём начальную громкость 50% (значение от 0 до 1)
            volume=0.5
        )
        #если страница flet передана, добавляем плеер в её оверлей для работы с аудио
        if page is not None:
            page.overlay.append(self.audio_player)
        #сохраняем ссылку на объект интерфейса для обновления элементов
        self.ui = ui
        #флаг автозапуска трека при его загрузке (изначально выключен)
        self.autoplay_on_load = False

    #настя
    #метод для загрузки mp3-файлов из папки tracks
    def load_local_tracks(self):
        #создаём пустой список для хранения информации о треках
        tracks = []
        #проходим по всем файлам в папке tracks
        for file in os.listdir(self.tracks_folder):
            #проверяем, что файл имеет расширение .mp3
            if file.lower().endswith(".mp3"):
                #добавляем трек в список как словарь с двумя ключами
                tracks.append({
                    #путь к файлу, чтобы плеер мог его воспроизвести
                    "url": f"{self.tracks_folder}/{file}",
                    #имя файла без расширения .mp3 как название трека
                    "title": os.path.splitext(file)[0]
                })
        #возвращаем список всех найденных треков
        return tracks

    #настя
    #метод для вкл/выкл режима перемешивания плейлиста
    def toggle_shuffle(self, e, shuffle_button, page):
        #инвертируем режим перемешивания (вкл/выкл)
        self.shuffle_mode = not self.shuffle_mode
        #меняем цвет иконки кнопки: фиолетовый при включённом режиме, серый при выключенном
        if shuffle_button is not None:
            shuffle_button.icon_color = ft.Colors.PURPLE_ACCENT_400 if self.shuffle_mode else ft.Colors.GREY
        #если режим перемешивания включён
        if self.shuffle_mode:
            #сохраняем текущий трек, чтобы он остался на месте
            current_track = self.playlist[self.current_track_index]
            #создаём список остальных треков, исключая текущий
            other_tracks = [t for t in self.playlist if t != current_track]
            #перемешиваем остальные треки случайным образом
            random.shuffle(other_tracks)
            #собираем новый плейлист: треки до текущего + текущий + треки после
            self.playlist = other_tracks[:self.current_track_index] + [current_track] + other_tracks[self.current_track_index:]
        #если режим перемешивания выключен
        else:
            #сохраняем текущий трек
            current_track = self.playlist[self.current_track_index]
            #восстанавливаем исходный порядок плейлиста
            self.playlist = self.original_playlist.copy()
            #находим индекс текущего трека в новом плейлисте
            for i, track in enumerate(self.playlist):
                if track["url"] == current_track["url"]:
                    self.current_track_index = i
                    break
        #обновляем список очереди в интерфейсе
        if self.ui is not None:
            self.ui.update_queue_list()
        #обновляем страницу, чтобы изменения отобразились
        if page is not None:
            page.update()

    #настя
    #метод для форматирования времени из миллисекунд в формат mm:ss
    def format_time(self, ms):
        #если время не задано, возвращаем "00:00"
        if ms is None:
            return "00:00"
        #переводим миллисекунды в секунды
        seconds = int(ms / 1000)
        #вычисляем минуты
        minutes = seconds // 60
        #оставляем только секунды
        seconds %= 60
        #форматируем в строку вида mm:ss с ведущими нулями
        return f"{minutes:02d}:{seconds:02d}"

    #настя
    #метод для обработки нажатия кнопки играть/пауза
    def play_pause_click(self, e, play_pause_button, page):
        #если плеер сейчас играет
        if self.current_state == ft.AudioState.PLAYING:
            #ставим трек на паузу
            self.audio_player.pause()
            #обновляем состояние на пауза
            self.current_state = ft.AudioState.PAUSED
            #меняем иконку кнопки на играть
            play_pause_button.icon = "play_circle_filled_rounded"
            #останавливаем анимацию эквалайзера
            self.ui.equalizer.stop()
        #если плеер на паузе или остановлен, и есть загруженный трек
        elif self.current_state in [ft.AudioState.PAUSED, ft.AudioState.STOPPED] and self.audio_player.src:
            #возобновляем воспроизведение
            self.audio_player.resume()
            #обновляем состояние на играет
            self.current_state = ft.AudioState.PLAYING
            #меняем иконку кнопки на пауза
            play_pause_button.icon = "pause_circle_filled_rounded"
            #берём название текущего трека
            current_track = self.playlist[self.current_track_index]["title"]
            #увеличиваем счётчик прослушиваний для этого трека
            self.play_counts[current_track] += 1
            #обновляем список статистики в интерфейсе
            self.ui.update_stats_list()
            #запускаем анимацию эквалайзера
            self.ui.equalizer.start()
        #обновляем страницу, чтобы изменения отобразились
        page.update()

    #настя
    #метод для обработки изменения состояния плеера (играет, пауза, остановлен)
    def audio_state_changed(self, e):
        #если плеер начал воспроизведение
        if e.data == "playing":
            self.current_state = ft.AudioState.PLAYING
        #если на паузе
        elif e.data == "paused":
            self.current_state = ft.AudioState.PAUSED
        #если остановлен
        elif e.data == "stopped":
            self.current_state = ft.AudioState.STOPPED

    #настя
    #метод для обработки изменения позиции воспроизведения трека
    def audio_position_changed(self, e):
        #проверяем, что слайдер активен и есть данные о позиции
        if not self.ui.progress_slider.disabled and e.data is not None:
            #берём текущую позицию трека в мс
            position = int(e.data)
            #обновляем значение слайдера прогресса
            self.ui.progress_slider.value = position
            #форматируем и обновляем текст текущего времени
            self.ui.current_time_text.value = self.format_time(position)
            #получаем длительность трека
            duration = self.audio_player.get_duration()
            #если длительность известна и трек почти закончился
            if duration is not None and position >= duration - 100:
                #если включён режим повтора
                if self.repeat_mode:
                    #перематываем трек на начало
                    self.audio_player.seek(0)
                    #возобновляем воспроизведение
                    self.audio_player.resume()
                    #берём название текущего трека
                    current_track = self.playlist[self.current_track_index]["title"]
                    #увеличиваем счётчик прослушиваний
                    self.play_counts[current_track] += 1
                    #обновляем статистику в интерфейсе
                    self.ui.update_stats_list()
                #если повтор выключен
                else:
                    #переключаем на следующий трек
                    self.next_track(
                        e,
                        self.ui.track_title,
                        self.ui.play_pause_button,
                        self.ui.current_time_text,
                        self.ui.total_time_text,
                        self.ui.progress_slider,
                        self.ui.page
                    )
            #обновляем страницу, чтобы изменения отобразились
            self.ui.page.update()

    #настя
    #метод для обработки события загрузки трека
    def audio_loaded(self, e):
        #получаем длительность трека в мс
        duration_ms = self.audio_player.get_duration()
        #если длительность известна
        if duration_ms is not None:
            #форматируем и обновляем текст общей длительности трека
            self.ui.total_time_text.value = self.format_time(duration_ms)
            #задаём максимальное значение слайдера прогресса
            self.ui.progress_slider.max = duration_ms
            #обновляем страницу
            self.ui.page.update()
        #если включён автозапуск
        if self.autoplay_on_load:
            #запускаем воспроизведение трека
            self.audio_player.play()
            #обновляем состояние на играет
            self.current_state = ft.AudioState.PLAYING
            #меняем иконку кнопки на пауза
            self.ui.play_pause_button.icon = "pause_circle_filled_rounded"
            #берём название текущего трека
            track = self.playlist[self.current_track_index]["title"]
            #увеличиваем счётчик прослушиваний
            self.play_counts[track] += 1
            #обновляем статистику в интерфейсе
            self.ui.update_stats_list()
            #обновляем страницу
            self.ui.page.update()
            #запускаем анимацию эквалайзера
            self.ui.equalizer.start()
            #сбрасываем флаг автозапуска
            self.autoplay_on_load = False

    #настя
    #метод для вкл/выкл режима повтора текущего трека
    def toggle_repeat(self, e, repeat_button, page):
        #инвертируем режим повтора
        self.repeat_mode = not self.repeat_mode
        #меняем цвет иконки кнопки: фиолетовый при включённом режиме, серый при выключенном
        repeat_button.icon_color = ft.Colors.PURPLE_ACCENT_400 if self.repeat_mode else ft.Colors.GREY
        #обновляем страницу
        page.update()

    #настя
    #метод для загрузки трека по его индексу в плейлисте
    def load_track(self, track_index, autoplay, track_title, play_pause_button, current_time_text, total_time_text, progress_slider, page):
        #задаём индекс текущего трека
        self.current_track_index = track_index
        #берём данные о треке из плейлиста
        track = self.playlist[self.current_track_index]
        #обновляем текст названия трека в интерфейсе
        track_title.value = track["title"]
        #задаём состояние остановлен перед загрузкой нового трека
        self.current_state = ft.AudioState.STOPPED
        #меняем иконку кнопки на играть
        play_pause_button.icon = "play_circle_filled_rounded"
        #сбрасываем текст текущего времени
        current_time_text.value = "00:00"
        #сбрасываем текст общей длительности
        total_time_text.value = "00:00"
        #сбрасываем значение слайдера прогресса
        progress_slider.value = 0
        #задаём путь к файлу трека для плеера
        self.audio_player.src = track["url"]
        #обновляем список очереди в интерфейсе
        self.ui.update_queue_list()
        #обновляем статистику в интерфейсе
        self.ui.update_stats_list()
        #обновляем страницу
        page.update()
        #если включён автозапуск и трек загружен
        if autoplay and self.audio_player.src:
            #включаем флаг автозапуска
            self.autoplay_on_load = autoplay
            #задаём состояние играет
            self.current_state = ft.AudioState.PLAYING
            #меняем иконку кнопки на пауза
            play_pause_button.icon = "pause_circle_filled_rounded"
            #увеличиваем счётчик прослушиваний текущего трека
            self.play_counts[track["title"]] += 1
            #обновляем статистику
            self.ui.update_stats_list()
            #обновляем страницу
            page.update()

    #настя
    #метод для переключения на следующий трек
    def next_track(self, e, track_title, play_pause_button, current_time_text, total_time_text, progress_slider, page):
        #если включён режим перемешивания
        if self.shuffle_mode:
            #создаём список индексов всех треков, кроме текущего
            other_indices = [i for i in range(len(self.playlist)) if i != self.current_track_index]
            #выбираем случайный индекс из остальных, либо оставляем текущий, если других нет
            new_index = random.choice(other_indices) if other_indices else self.current_track_index
        #если перемешивание выключено
        else:
            #берём следующий индекс с учётом зацикливания, если последний, переходим к первому
            new_index = (self.current_track_index + 1) % len(self.playlist)
        #загружаем новый трек с автозапуском
        self.load_track(new_index, True, track_title, play_pause_button, current_time_text, total_time_text, progress_slider, page)

    #настя
    #метод для переключения на предыдущий трек
    def prev_track(self, e, track_title, play_pause_button, current_time_text, total_time_text, progress_slider, page):
        #если включён режим перемешивания
        if self.shuffle_mode:
            #создаём список индексов всех треков, кроме текущего
            other_indices = [i for i in range(len(self.playlist)) if i != self.current_track_index]
            #выбираем случайный индекс из остальных, либо оставляем текущий
            new_index = random.choice(other_indices) if other_indices else self.current_track_index
        #если перемешивание выключено
        else:
            #берём предыдущий индекс с учётом зацикливания, если первый, переходим к последнему
            new_index = (self.current_track_index - 1 + len(self.playlist)) % len(self.playlist)
        #загружаем новый трек с автозапуском
        self.load_track(new_index, True, track_title, play_pause_button, current_time_text, total_time_text, progress_slider, page)

#таня
class UIComponents:
    def __init__(self, page, audio_manager):
        # Инициализирует класс UIComponents с объектом страницы Flet и менеджером аудио.
        self.page = page
        # Сохраняет объект страницы Flet для управления интерфейсом.
        self.audio_manager = audio_manager
        # Сохраняет менеджер аудио для взаимодействия с логикой воспроизведения.
        self.build_ui()
        # Вызывает метод для создания пользовательского интерфейса.

    #таня
    def update_queue_list(self):
        # Обновляет список треков во вкладке "В очереди".
        self.queue_list.controls = [
            # Заполняет список queue_list виджетами ListTile для каждого трека.
            ft.ListTile(
                leading=ft.Text("•", color=ft.Colors.PURPLE_ACCENT_400) if i == self.audio_manager.current_track_index else None,
                # Добавляет точку для текущего трека, фиолетовую при активном треке, иначе пусто.
                title=ft.Text(
                    track["title"],
                    size=14,
                    color=ft.Colors.PURPLE_ACCENT_400 if i == self.audio_manager.current_track_index else ft.Colors.WHITE
                ),
                # Отображает название трека, фиолетовое для текущего, белое для остальных.
                on_click=lambda e, idx=i: self.audio_manager.load_track(idx, True, self.track_title, self.play_pause_button, self.current_time_text, self.total_time_text, self.progress_slider, self.page)
                # Устанавливает обработчик клика для загрузки и воспроизведения трека.
            ) for i, track in enumerate(self.audio_manager.playlist)
            # Перебирает плейлист для создания элемента ListTile для каждого трека.
        ]
        self.page.update()
        # Обновляет страницу для отображения изменений в списке очереди.

    #таня
    def update_stats_list(self):
        # Обновляет вкладку "Статистика" с данными о прослушиваниях треков.
        sorted_counts = sorted(self.audio_manager.play_counts.items(), key=lambda x: x[1], reverse=True)
        # Сортирует треки по количеству прослушиваний в порядке убывания.
        self.stats_list.controls = [
            # Заполняет stats_list виджетами ListTile с данными о прослушиваниях.
            ft.ListTile(
                title=ft.Text(
                    f"{i+1}. {track} ({count} прослушиваний)",
                    size=14,
                    color=ft.Colors.PURPLE_ACCENT_400 if count > 0 else ft.Colors.WHITE
                )
                # Показывает номер, название трека и число прослушиваний, фиолетовое если >0.
            ) for i, (track, count) in enumerate(sorted_counts)
            # Перебирает отсортированные данные для создания ListTile для каждого трека.
        ]
        self.page.update()
        # Обновляет страницу для отображения изменений в статистике.

    #таня
    def build_ui(self):
        # Создает основной интерфейс аудиоплеера.
        self.track_title = ft.Text(
            "Плеер готов",
            size=16,
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.LEFT
        )
        # Создает текст для названия трека, начально "Плеер готов", жирный шрифт.
        self.equalizer = EqualizerAnimation(width=300, height=265)
        # Инициализирует анимацию эквалайзера с шириной 300 и высотой 265.
        self.visualizer_placeholder = ft.Container(
            content=self.equalizer,
            width=300, height=265,
            bgcolor=ft.Colors.BLACK38,
            border_radius=ft.border_radius.all(8),
            alignment=ft.alignment.center,
            margin=ft.margin.only(top=5, bottom=5)
        )
        # Создает контейнер для эквалайзера с темным фоном и скругленными углами.
        self.current_time_text = ft.Text("00:00")
        # Создает текст для текущего времени воспроизведения, начально "00:00".
        self.total_time_text = ft.Text("00:00")
        # Создает текст для общей длительности трека, начально "00:00".
        self.progress_slider = ft.Slider(
            min=0, max=100, value=0,
            on_change_end=lambda e: self.audio_manager.audio_player.seek(int(e.control.value)),
            active_color=ft.Colors.PURPLE_ACCENT_100,
            thumb_color=ft.Colors.PURPLE_700,
            height=20
        )
        # Создает слайдер прогресса трека с функцией перемотки, фиолетовый стиль.
        
        self.time_row = ft.Row(
            controls=[self.current_time_text, self.total_time_text],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )
        # Создает строку для отображения текущего и общего времени, равномерно распределенных.

        self.shuffle_button = ft.IconButton(
            icon="shuffle_rounded",
            on_click=lambda e: self.audio_manager.toggle_shuffle(e, self.shuffle_button, self.page),
            icon_size=30,
            icon_color=ft.Colors.GREY,
            tooltip="Перемешать треки"
        )
        # Создает кнопку перемешивания, вызывает toggle_shuffle, изначально серая.
        self.prev_button = ft.IconButton(
            icon="skip_previous_rounded",
            on_click=lambda e: self.audio_manager.prev_track(e, self.track_title, self.play_pause_button, self.current_time_text, self.total_time_text, self.progress_slider, self.page),
            icon_size=40,
            icon_color=ft.Colors.PURPLE_ACCENT_400
        )
        # Создает кнопку предыдущего трека, вызывает prev_track, фиолетовая.
        self.play_pause_button = ft.IconButton(
            icon="play_circle_filled_rounded",
            visible=True,
            on_click=lambda e: self.audio_manager.play_pause_click(e, self.play_pause_button, self.page),
            icon_size=60,
            icon_color=ft.Colors.PURPLE_ACCENT_400
        )
        # Создает кнопку воспроизведения/паузы, вызывает play_pause_click, большая, фиолетовая.
        self.next_button = ft.IconButton(
            icon="skip_next_rounded",
            on_click=lambda e: self.audio_manager.next_track(e, self.track_title, self.play_pause_button, self.current_time_text, self.total_time_text, self.progress_slider, self.page),
            icon_size=40,
            icon_color=ft.Colors.PURPLE_ACCENT_400
        )
        # Создает кнопку следующего трека, вызывает next_track, фиолетовая.
        self.repeat_button = ft.IconButton(
            icon="repeat_rounded",
            on_click=lambda e: self.audio_manager.toggle_repeat(e, self.repeat_button, self.page),
            icon_size=30,
            icon_color=ft.Colors.GREY,
            tooltip="Повтор трека"
        )
        # Создает кнопку повтора, вызывает toggle_repeat, изначально серая.

        self.playback_controls = ft.Row(
            controls=[self.shuffle_button, self.prev_button, self.play_pause_button, self.next_button, self.repeat_button],
            alignment=ft.MainAxisAlignment.CENTER
        )
        # Создает строку для кнопок управления воспроизведением, центрированная.
        self.volume_down_button = ft.IconButton(
            icon="volume_down_rounded",
            on_click=self.volume_down,
            icon_size=30,
            icon_color=ft.Colors.PURPLE_ACCENT_400
        )
        # Создает кнопку уменьшения громкости, вызывает volume_down, фиолетовая.
        self.volume_up_button = ft.IconButton(
            icon="volume_up_rounded",
            on_click=self.volume_up,
            icon_size=30,
            icon_color=ft.Colors.PURPLE_ACCENT_400
        )
        # Создает кнопку увеличения громкости, вызывает volume_up, фиолетовая.

        self.volume_slider = ft.Slider(
            min=0, max=1, divisions=100, value=0.5,
            width=150, on_change=self.volume_change,
            active_color=ft.Colors.PURPLE_ACCENT_100,
            thumb_color=ft.Colors.PURPLE_700,
            height=20,
        )
        # Создает слайдер громкости, обновляет громкость при изменении, фиолетовый стиль.
        self.volume_controls = ft.Row(
            controls=[self.volume_down_button, self.volume_slider, self.volume_up_button],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10
        )
        # Создает строку для элементов управления громкостью, центрированная с отступами.

        self.power_switch = ft.Switch(
            label="On",
            on_change=self.toggle_player_power,
            value=True,
            active_color=ft.Colors.PURPLE_ACCENT_200
        )
        # Создает переключатель питания, вызывает toggle_player_power, изначально включен.
        self.help_button = ft.IconButton(
            icon="help_outline_rounded",
            on_click=self.toggle_help,
            tooltip="Справка",
            icon_color=ft.Colors.PURPLE_ACCENT_400
        )
        # Создает кнопку справки для показа/скрытия панели, с подсказкой, фиолетовая.
        self.extra_controls = ft.Row(
            controls=[self.power_switch, self.help_button],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
        # Создает строку для переключателя питания и кнопки справки, равномерно распределенных.

        self.help_text_content = ("▶️/⏸️: Запуск/пауза\n" "🔀: Перемешать треки\n" "⏪/⏩: Переключение\n" "🔉: Громкость\n" "🔁: Повтор трека\n" "On/Off: Вкл/Выкл")
        # Задает текст справки с описанием функций управления плеером.
        self.close_button = ft.ElevatedButton(
            "Закрыть",
            on_click=self.toggle_help,
            bgcolor=ft.Colors.PURPLE_ACCENT_400,
            color=ft.Colors.WHITE
        )
        # Создает кнопку закрытия панели справки, фиолетовый фон, белый текст.
        self.help_panel = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Справка", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(self.help_text_content, size=14),
                    self.close_button
                ],
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            width=300,
            height=250,
            padding=20,
            border_radius=ft.border_radius.all(8),
            bgcolor=ft.Colors.GREY_800.with_opacity(0.95, ft.Colors.GREY_800),
            alignment=ft.alignment.center
        )
        # Создает панель справки с заголовком, текстом и кнопкой, серый фон.
        self.help_container = ft.Container(
            content=self.help_panel,
            alignment=ft.alignment.center,
            visible=False,
            width=400,
            height=750,
            bgcolor=ft.Colors.BLACK.with_opacity(0.3, ft.Colors.BLACK)
        )
        # Создает контейнер для панели справки, изначально скрыт, полупрозрачный фон.
        self.page.overlay.append(self.help_container)
        # Добавляет панель справки в наложение страницы для отображения.

        self.player_layout = ft.Container(
            content=ft.Column(
                controls=[
                    self.extra_controls,
                    ft.Divider(height=10, color="transparent"),
                    self.visualizer_placeholder,
                    self.track_title,
                    self.progress_slider,
                    self.time_row,
                    self.playback_controls,
                    self.volume_controls
                ],
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH
            ),
            width=400,
            height=750,
            padding=20,
            border=ft.border.all(2, ft.Colors.PURPLE_ACCENT_100),
            border_radius=ft.border_radius.all(10),
            bgcolor=ft.Colors.BLACK26
        )
        # Создает контейнер плеера с элементами управления, эквалайзером, фиолетовая рамка.

        self.queue_list = ft.ListView(
            controls=[
                ft.ListTile(
                    leading=ft.Text("•", color=ft.Colors.PURPLE_ACCENT_400) if i == self.audio_manager.current_track_index else None,
                    title=ft.Text(
                        track["title"],
                        size=14,
                        color=ft.Colors.PURPLE_ACCENT_400 if i == self.audio_manager.current_track_index else ft.Colors.WHITE
                    ),
                    on_click=lambda e, idx=i: self.audio_manager.load_track(idx, True, self.track_title, self.play_pause_button, self.current_time_text, self.total_time_text, self.progress_slider, self.page)
                ) for i, track in enumerate(self.audio_manager.playlist)
            ],
            spacing=5,
            padding=10
        )
        # Создает список для вкладки очереди с треками и обработчиками кликов.

        self.stats_list = ft.ListView(
            controls=[
                ft.ListTile(
                    title=ft.Text(
                        f"{i+1}. {track} ({count} прослушиваний)",
                        size=14,
                        color=ft.Colors.PURPLE_ACCENT_400 if count > 0 else ft.Colors.WHITE
                    )
                ) for i, (track, count) in enumerate(sorted(self.audio_manager.play_counts.items(), key=lambda x: x[1], reverse=True))
            ],
            spacing=5,
            padding=10
        )
        # Создает список для вкладки статистики с треками, отсортированными по прослушиваниям.

        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text="Плеер",
                    content=ft.Container(
                        content=self.player_layout,
                        alignment=ft.alignment.top_left
                    ),
                    tab_content=ft.Text("Плеер", color=ft.Colors.WHITE)
                ),
                ft.Tab(
                    text="В очереди",
                    content=ft.Container(
                        content=self.queue_list,
                        alignment=ft.alignment.top_left
                    ),
                    tab_content=ft.Text("В очереди", color=ft.Colors.WHITE)
                ),
                ft.Tab(
                    text="Статистика",
                    content=ft.Container(
                        content=self.stats_list,
                        alignment=ft.alignment.top_left
                    ),
                    tab_content=ft.Text("Статистика", color=ft.Colors.WHITE)
                ),
            ],
            expand=True,
            tab_alignment=ft.MainAxisAlignment.CENTER,
            indicator_color=ft.Colors.PURPLE_ACCENT_400,
            label_color=ft.Colors.PURPLE_ACCENT_400
        )
        # Создает вкладки "Плеер", "В очереди", "Статистика" с фиолетовым стилем.

        self.page.window_width = 340
        # Устанавливает ширину окна приложения в 340 пикселей.
        self.page.window_height = 850
        # Устанавливает высоту окна приложения в 850 пикселей.
        self.page.window_resizable = False
        # Отключает возможность изменения размера окна.
        self.page.padding = 0
        # Убирает отступы страницы по умолчанию.
        self.page.horizontal_alignment = ft.CrossAxisAlignment.START
        # Выравнивает содержимое страницы по левому краю.
        self.page.vertical_alignment = ft.MainAxisAlignment.START
        # Выравнивает содержимое страницы по верхнему краю.

    #таня
    def volume_change(self, e):
        # Обрабатывает изменение значения слайдера громкости.
        self.audio_manager.audio_player.volume = self.volume_slider.value
        # Устанавливает громкость плеера равной значению слайдера.
        self.audio_manager.audio_player.update()
        # Обновляет плеер для применения изменений громкости.

    #таня
    def volume_down(self, e):
        # Обрабатывает нажатие кнопки уменьшения громкости.
        new_volume = max(0, self.audio_manager.audio_player.volume - 0.1)
        # Уменьшает громкость на 0.1, не опускаясь ниже 0.
        self.audio_manager.audio_player.volume = new_volume
        # Применяет новую громкость к плееру.
        self.volume_slider.value = new_volume
        # Обновляет значение слайдера громкости.
        self.page.update()
        # Обновляет страницу для отображения изменений.

    #таня
    def volume_up(self, e):
        # Обрабатывает нажатие кнопки увеличения громкости.
        new_volume = min(1, self.audio_manager.audio_player.volume + 0.1)
        # Увеличивает громкость на 0.1, не превышая 1.
        self.audio_manager.audio_player.volume = new_volume
        # Применяет новую громкость к плееру.
        self.volume_slider.value = new_volume
        # Обновляет значение слайдера громкости.
        self.page.update()
        # Обновляет страницу для отображения изменений.

    #таня
    def toggle_player_power(self, e):
        # Обрабатывает переключение состояния питания плеера.
        is_on = e.data == "true"
        # Проверяет, включен ли переключатель (true) или выключен (false).
        is_disabled = not is_on
        # Устанавливает состояние отключения для кнопок и слайдеров.
        self.power_switch.label = "On" if is_on else "Off"
        # Обновляет метку переключателя на "On" или "Off".
        button_color = ft.Colors.GREY if is_disabled else ft.Colors.PURPLE_ACCENT_400
        # Устанавливает серый цвет для отключенных кнопок, фиолетовый для включенных.
        for button in [self.shuffle_button, self.prev_button, self.play_pause_button, self.next_button, self.repeat_button, self.volume_down_button, self.volume_up_button]:
            button.disabled = is_disabled
            # Отключает или включает кнопки в зависимости от состояния питания.
            button.icon_color = button_color
            # Обновляет цвет иконок кнопок в зависимости от состояния.
        for slider in [self.progress_slider, self.volume_slider]:
            slider.disabled = is_disabled
            # Отключает или включает слайдеры в зависимости от состояния.
        if not is_on and self.audio_manager.audio_player.src:
            self.audio_manager.audio_player.pause()
            # Приостанавливает воспроизведение, если плеер выключен и трек загружен.
            self.audio_manager.current_state = ft.AudioState.PAUSED
            # Устанавливает состояние плеера как приостановленное.
            self.play_pause_button.icon = "play_circle_filled_rounded"
            # Обновляет иконку кнопки воспроизведения на "play".
            self.equalizer.stop()
            # Останавливает анимацию эквалайзера.
        self.page.update()
        # Обновляет страницу для отображения всех изменений.

    #таня
    def toggle_help(self, e):
        # Обрабатывает нажатие кнопки справки.
        self.help_container.visible = not self.help_container.visible
        # Переключает видимость панели справки (показать/скрыть).
        self.page.update()
        # Обновляет страницу для отображения или скрытия панели справки.

#таня
def main(page: ft.Page):
    # Определяет главную функцию для запуска приложения Flet.
    page.title = "Player"
    # Устанавливает заголовок окна приложения "Player".
    page.horizontal_alignment = ft.CrossAxisAlignment.START
    # Выравнивает содержимое страницы по левому краю.
    page.vertical_alignment = ft.MainAxisAlignment.START
    # Выравнивает содержимое страницы по верхнему краю.
    page.theme_mode = ft.ThemeMode.DARK
    # Устанавливает темную тему для приложения.

    audio_manager = AudioPlayerManager(page, None)
    # Создает экземпляр менеджера аудио, изначально без UI.
    ui = UIComponents(page, audio_manager)
    # Создает экземпляр UIComponents, передавая страницу и менеджер аудио.
    audio_manager.ui = ui
    # Связывает пользовательский интерфейс с менеджером аудио.
    page.add(ui.tabs)
    # Добавляет вкладки (Плеер, Очередь, Статистика) на страницу.
    audio_manager.load_track(0, False, ui.track_title, ui.play_pause_button, ui.current_time_text, ui.total_time_text, ui.progress_slider, page)
    # Загружает первый трек без автоматического воспроизведения, инициализируя UI.
if __name__ == "__main__":
    # Проверяет, запущен ли файл напрямую, а не импортирован как модуль.
    ft.app(target=main)
    # Запускает приложение Flet, передавая функцию "main" как основную точку входа.