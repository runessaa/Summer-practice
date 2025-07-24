import flet as ft
import flet_audio as fa
import os
import random
import math
import time
import threading

#настя
class EqualizerAnimation(ft.Container):
    def __init__(self, width=300, height=265, bars=8):
        super().__init__()
        self.width = width
        self.height = height
        self.bars = bars
        self.running = False
        self._timer = None
        self.bar_rects = [
            ft.Container(
                width=width // (bars + 2),
                height=30,
                bgcolor=ft.Colors.PURPLE_ACCENT_400,
                border_radius=ft.border_radius.all(6),
                alignment=ft.alignment.bottom_center,
                margin=ft.margin.symmetric(horizontal=0)
            ) for _ in range(bars)
        ]
        self.content = ft.Row(
            controls=self.bar_rects,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.END,
            width=width,
            height=height
        )

    def _animate(self):
        if not self.running:
            return
        t = time.time()
        for i, bar in enumerate(self.bar_rects):
            bar.height = 30 + 100 * abs(math.sin(t * 2 + i))
        self.update()
        self._timer = threading.Timer(0.05, self._animate)
        self._timer.start()

    def start(self):
        if not self.running:
            self.running = True
            self._animate()

    def stop(self):
        self.running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None

#настя
class AudioPlayerManager:
    def __init__(self, page, ui):
        self.current_state = ft.AudioState.PAUSED
        self.current_track_index = 0
        self.repeat_mode = False
        self.shuffle_mode = False
        self.tracks_folder = "tracks"
        self.original_playlist = self.load_local_tracks()
        self.playlist = self.original_playlist.copy()
        self.play_counts = {track["title"]: 0 for track in self.original_playlist}
        self.audio_player = fa.Audio(
            autoplay=False,
            on_state_changed=self.audio_state_changed,
            on_position_changed=self.audio_position_changed,
            on_loaded=self.audio_loaded,
            volume=0.5
        )
        if page is not None:
            page.overlay.append(self.audio_player)
        self.ui = ui
        self.autoplay_on_load = False

    #настя
    def load_local_tracks(self):
        tracks = []
        for file in os.listdir(self.tracks_folder):
            if file.lower().endswith(".mp3"):
                tracks.append({
                    "url": f"{self.tracks_folder}/{file}",
                    "title": os.path.splitext(file)[0]
                })
        return tracks

    #настя
    def toggle_shuffle(self, e, shuffle_button, page):
        self.shuffle_mode = not self.shuffle_mode
        if shuffle_button is not None:
            shuffle_button.icon_color = ft.Colors.PURPLE_ACCENT_400 if self.shuffle_mode else ft.Colors.GREY
        if self.shuffle_mode:
            current_track = self.playlist[self.current_track_index]
            other_tracks = [t for t in self.playlist if t != current_track]
            random.shuffle(other_tracks)
            self.playlist = other_tracks[:self.current_track_index] + [current_track] + other_tracks[self.current_track_index:]
        else:
            current_track = self.playlist[self.current_track_index]
            self.playlist = self.original_playlist.copy()
            for i, track in enumerate(self.playlist):
                if track["url"] == current_track["url"]:
                    self.current_track_index = i
                    break
        if self.ui is not None:
            self.ui.update_queue_list()
        if page is not None:
            page.update()

    #настя
    def format_time(self, ms):
        if ms is None:
            return "00:00"
        seconds = int(ms / 1000)
        minutes = seconds // 60
        seconds %= 60
        return f"{minutes:02d}:{seconds:02d}"

    #настя
    def play_pause_click(self, e, play_pause_button, page):
        if self.current_state == ft.AudioState.PLAYING:
            self.audio_player.pause()
            self.current_state = ft.AudioState.PAUSED
            play_pause_button.icon = "play_circle_filled_rounded"
            self.ui.equalizer.stop()
        elif self.current_state in [ft.AudioState.PAUSED, ft.AudioState.STOPPED] and self.audio_player.src:
            self.audio_player.resume()
            self.current_state = ft.AudioState.PLAYING
            play_pause_button.icon = "pause_circle_filled_rounded"
            current_track = self.playlist[self.current_track_index]["title"]
            self.play_counts[current_track] += 1
            self.ui.update_stats_list()
            self.ui.equalizer.start()
        page.update()

    #настя
    def audio_state_changed(self, e):
        if e.data == "playing":
            self.current_state = ft.AudioState.PLAYING
        elif e.data == "paused":
            self.current_state = ft.AudioState.PAUSED
        elif e.data == "stopped":
            self.current_state = ft.AudioState.STOPPED

    #настя
    def audio_position_changed(self, e):
        if not self.ui.progress_slider.disabled and e.data is not None:
            position = int(e.data)
            self.ui.progress_slider.value = position
            self.ui.current_time_text.value = self.format_time(position)
            duration = self.audio_player.get_duration()
            if duration is not None and position >= duration - 100:
                if self.repeat_mode:
                    self.audio_player.seek(0)
                    self.audio_player.resume()
                    current_track = self.playlist[self.current_track_index]["title"]
                    self.play_counts[current_track] += 1
                    self.ui.update_stats_list()
                else:
                    self.next_track(
                        e,
                        self.ui.track_title,
                        self.ui.play_pause_button,
                        self.ui.current_time_text,
                        self.ui.total_time_text,
                        self.ui.progress_slider,
                        self.ui.page
                    )
            self.ui.page.update()

    #настя
    def audio_loaded(self, e):
        duration_ms = self.audio_player.get_duration()
        if duration_ms is not None:
            self.ui.total_time_text.value = self.format_time(duration_ms)
            self.ui.progress_slider.max = duration_ms
            self.ui.page.update()
        if self.autoplay_on_load:
            self.audio_player.play()
            self.current_state = ft.AudioState.PLAYING
            self.ui.play_pause_button.icon = "pause_circle_filled_rounded"
            track = self.playlist[self.current_track_index]["title"]
            self.play_counts[track] += 1
            self.ui.update_stats_list()
            self.ui.page.update()
            self.ui.equalizer.start()
            self.autoplay_on_load = False

    #настя
    def toggle_repeat(self, e, repeat_button, page):
        self.repeat_mode = not self.repeat_mode
        repeat_button.icon_color = ft.Colors.PURPLE_ACCENT_400 if self.repeat_mode else ft.Colors.GREY
        page.update()

    #настя
    def load_track(self, track_index, autoplay, track_title, play_pause_button, current_time_text, total_time_text, progress_slider, page):
        self.current_track_index = track_index
        track = self.playlist[self.current_track_index]
        track_title.value = track["title"]
        self.current_state = ft.AudioState.STOPPED
        play_pause_button.icon = "play_circle_filled_rounded"
        current_time_text.value = "00:00"
        total_time_text.value = "00:00"
        progress_slider.value = 0
        self.audio_player.src = track["url"]
        self.ui.update_queue_list()
        self.ui.update_stats_list()
        page.update()
        if autoplay and self.audio_player.src:
            self.autoplay_on_load = autoplay
            self.current_state = ft.AudioState.PLAYING
            play_pause_button.icon = "pause_circle_filled_rounded"
            self.play_counts[track["title"]] += 1
            self.ui.update_stats_list()
            page.update()

    #настя
    def next_track(self, e, track_title, play_pause_button, current_time_text, total_time_text, progress_slider, page):
        if self.shuffle_mode:
            other_indices = [i for i in range(len(self.playlist)) if i != self.current_track_index]
            new_index = random.choice(other_indices) if other_indices else self.current_track_index
        else:
            new_index = (self.current_track_index + 1) % len(self.playlist)
        self.load_track(new_index, True, track_title, play_pause_button, current_time_text, total_time_text, progress_slider, page)

    #настя
    def prev_track(self, e, track_title, play_pause_button, current_time_text, total_time_text, progress_slider, page):
        if self.shuffle_mode:
            other_indices = [i for i in range(len(self.playlist)) if i != self.current_track_index]
            new_index = random.choice(other_indices) if other_indices else self.current_track_index
        else:
            new_index = (self.current_track_index - 1 + len(self.playlist)) % len(self.playlist)
        self.load_track(new_index, True, track_title, play_pause_button, current_time_text, total_time_text, progress_slider, page)

#таня
class UIComponents:
    def __init__(self, page, audio_manager):
        self.page = page
        self.audio_manager = audio_manager
        self.build_ui()

    #таня
    def update_queue_list(self):
        self.queue_list.controls = [
            ft.ListTile(
                leading=ft.Text("•", color=ft.Colors.PURPLE_ACCENT_400) if i == self.audio_manager.current_track_index else None,
                title=ft.Text(
                    track["title"],
                    size=14,
                    color=ft.Colors.PURPLE_ACCENT_400 if i == self.audio_manager.current_track_index else ft.Colors.WHITE
                ),
                on_click=lambda e, idx=i: self.audio_manager.load_track(idx, True, self.track_title, self.play_pause_button, self.current_time_text, self.total_time_text, self.progress_slider, self.page)
            ) for i, track in enumerate(self.audio_manager.playlist)
        ]
        self.page.update()

    #таня
    def update_stats_list(self):
        sorted_counts = sorted(self.audio_manager.play_counts.items(), key=lambda x: x[1], reverse=True)
        self.stats_list.controls = [
            ft.ListTile(
                title=ft.Text(
                    f"{i+1}. {track} ({count} прослушиваний)",
                    size=14,
                    color=ft.Colors.PURPLE_ACCENT_400 if count > 0 else ft.Colors.WHITE
                )
            ) for i, (track, count) in enumerate(sorted_counts)
        ]
        self.page.update()

    #таня
    def build_ui(self):
        self.track_title = ft.Text(
            "Плеер готов",
            size=16,
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.LEFT
        )
        self.equalizer = EqualizerAnimation(width=300, height=265)
        self.visualizer_placeholder = ft.Container(
            content=self.equalizer,
            width=300, height=265,
            bgcolor=ft.Colors.BLACK38,
            border_radius=ft.border_radius.all(8),
            alignment=ft.alignment.center,
            margin=ft.margin.only(top=5, bottom=5)
        )
        self.current_time_text = ft.Text("00:00")
        self.total_time_text = ft.Text("00:00")
        self.progress_slider = ft.Slider(
            min=0, max=100, value=0,
            on_change_end=lambda e: self.audio_manager.audio_player.seek(int(e.control.value)),
            active_color=ft.Colors.PURPLE_ACCENT_100,
            thumb_color=ft.Colors.PURPLE_700,
            height=20
        )
        
        self.time_row = ft.Row(
            controls=[self.current_time_text, self.total_time_text],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )

        self.shuffle_button = ft.IconButton(
            icon="shuffle_rounded",
            on_click=lambda e: self.audio_manager.toggle_shuffle(e, self.shuffle_button, self.page),
            icon_size=30,
            icon_color=ft.Colors.GREY,
            tooltip="Перемешать треки"
        )
        self.prev_button = ft.IconButton(
            icon="skip_previous_rounded",
            on_click=lambda e: self.audio_manager.prev_track(e, self.track_title, self.play_pause_button, self.current_time_text, self.total_time_text, self.progress_slider, self.page),
            icon_size=40,
            icon_color=ft.Colors.PURPLE_ACCENT_400
        )
        self.play_pause_button = ft.IconButton(
            icon="play_circle_filled_rounded",
            visible=True,
            on_click=lambda e: self.audio_manager.play_pause_click(e, self.play_pause_button, self.page),
            icon_size=60,
            icon_color=ft.Colors.PURPLE_ACCENT_400
        )
        self.next_button = ft.IconButton(
            icon="skip_next_rounded",
            on_click=lambda e: self.audio_manager.next_track(e, self.track_title, self.play_pause_button, self.current_time_text, self.total_time_text, self.progress_slider, self.page),
            icon_size=40,
            icon_color=ft.Colors.PURPLE_ACCENT_400
        )
        self.repeat_button = ft.IconButton(
            icon="repeat_rounded",
            on_click=lambda e: self.audio_manager.toggle_repeat(e, self.repeat_button, self.page),
            icon_size=30,
            icon_color=ft.Colors.GREY,
            tooltip="Повтор трека"
        )

        self.playback_controls = ft.Row(
            controls=[self.shuffle_button, self.prev_button, self.play_pause_button, self.next_button, self.repeat_button],
            alignment=ft.MainAxisAlignment.CENTER
        )
        self.volume_down_button = ft.IconButton(
            icon="volume_down_rounded",
            on_click=self.volume_down,
            icon_size=30,
            icon_color=ft.Colors.PURPLE_ACCENT_400
        )
        self.volume_up_button = ft.IconButton(
            icon="volume_up_rounded",
            on_click=self.volume_up,
            icon_size=30,
            icon_color=ft.Colors.PURPLE_ACCENT_400
        )

        self.volume_slider = ft.Slider(
            min=0, max=1, divisions=100, value=0.5,
            width=150, on_change=self.volume_change,
            active_color=ft.Colors.PURPLE_ACCENT_100,
            thumb_color=ft.Colors.PURPLE_700,
            height=20,
        )
        self.volume_controls = ft.Row(
            controls=[self.volume_down_button, self.volume_slider, self.volume_up_button],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10
        )

        self.power_switch = ft.Switch(
            label="On",
            on_change=self.toggle_player_power,
            value=True,
            active_color=ft.Colors.PURPLE_ACCENT_200
        )
        self.help_button = ft.IconButton(
            icon="help_outline_rounded",
            on_click=self.toggle_help,
            tooltip="Справка",
            icon_color=ft.Colors.PURPLE_ACCENT_400
        )
        self.extra_controls = ft.Row(
            controls=[self.power_switch, self.help_button],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

        self.help_text_content = ("▶️/⏸️: Запуск/пауза\n" "🔀: Перемешать треки\n" "⏪/⏩: Переключение\n" "🔉: Громкость\n" "🔁: Повтор трека\n" "On/Off: Вкл/Выкл")
        self.close_button = ft.ElevatedButton(
            "Закрыть",
            on_click=self.toggle_help,
            bgcolor=ft.Colors.PURPLE_ACCENT_400,
            color=ft.Colors.WHITE
        )
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
        self.help_container = ft.Container(
            content=self.help_panel,
            alignment=ft.alignment.center,
            visible=False,
            width=400,
            height=750,
            bgcolor=ft.Colors.BLACK.with_opacity(0.3, ft.Colors.BLACK)
        )
        self.page.overlay.append(self.help_container)

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

        self.page.window_width = 340
        self.page.window_height = 850
        self.page.window_resizable = False
        self.page.padding = 0
        self.page.horizontal_alignment = ft.CrossAxisAlignment.START
        self.page.vertical_alignment = ft.MainAxisAlignment.START

    #таня
    def volume_change(self, e):
        self.audio_manager.audio_player.volume = self.volume_slider.value
        self.audio_manager.audio_player.update()

    #таня
    def volume_down(self, e):
        new_volume = max(0, self.audio_manager.audio_player.volume - 0.1)
        self.audio_manager.audio_player.volume = new_volume
        self.volume_slider.value = new_volume
        self.page.update()

    #таня
    def volume_up(self, e):
        new_volume = min(1, self.audio_manager.audio_player.volume + 0.1)
        self.audio_manager.audio_player.volume = new_volume
        self.volume_slider.value = new_volume
        self.page.update()

    #таня
    def toggle_player_power(self, e):
        is_on = e.data == "true"
        is_disabled = not is_on
        self.power_switch.label = "On" if is_on else "Off"
        button_color = ft.Colors.GREY if is_disabled else ft.Colors.PURPLE_ACCENT_400
        for button in [self.shuffle_button, self.prev_button, self.play_pause_button, self.next_button, self.repeat_button, self.volume_down_button, self.volume_up_button]:
            button.disabled = is_disabled
            button.icon_color = button_color
        for slider in [self.progress_slider, self.volume_slider]:
            slider.disabled = is_disabled
        if not is_on and self.audio_manager.audio_player.src:
            self.audio_manager.audio_player.pause()
            self.audio_manager.current_state = ft.AudioState.PAUSED
            self.play_pause_button.icon = "play_circle_filled_rounded"
            self.equalizer.stop()
        self.page.update()

    #таня
    def toggle_help(self, e):
        self.help_container.visible = not self.help_container.visible
        self.page.update()

#таня
def main(page: ft.Page):
    page.title = "Player"
    page.horizontal_alignment = ft.CrossAxisAlignment.START
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.theme_mode = ft.ThemeMode.DARK

    audio_manager = AudioPlayerManager(page, None)
    ui = UIComponents(page, audio_manager)
    audio_manager.ui = ui
    page.add(ui.tabs)
    audio_manager.load_track(0, False, ui.track_title, ui.play_pause_button, ui.current_time_text, ui.total_time_text, ui.progress_slider, page)

if __name__ == "__main__":
    ft.app(target=main)