import random
import shutil
import sys
from pathlib import Path
from PySide6.QtCore import Qt, QUrl, QSize, QSettings, QThread, Signal, QStandardPaths, QEvent
from PySide6.QtGui import QIcon, QPixmap, QShortcut, QKeySequence, QColor, QPalette
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget, QListWidgetItem, QTabWidget, QFileDialog, QSlider, QStackedWidget, QMessageBox, QPlainTextEdit, QLineEdit, QCheckBox)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from archive import scan
from thumbnails import thumbnail

APP_NAME = 'dlpTube'
APP_SLUG = 'dlptube'
APP_VERSION = '0.3.0'
LEGACY_SETTINGS = ('LocalTube', 'LocalTube')

def migrate_legacy_settings(settings):
    if settings.contains('folder') or settings.contains('volume'):
        return
    legacy = QSettings(*LEGACY_SETTINGS)
    for key in ('folder', 'volume'):
        value = legacy.value(key)
        if value is not None:
            settings.setValue(key, value)


def clock(ms):
    seconds = max(0, int(ms // 1000))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f'{h}:{m:02}:{s:02}' if h else f'{m}:{s:02}'

class Scanner(QThread):
    done = Signal(object, object)
    failed = Signal(str)
    def __init__(self, root):
        super().__init__()
        self.root = root
    def run(self):
        try:
            self.done.emit(*scan(self.root))
        except Exception as e:
            self.failed.emit(str(e))

class ThumbnailWorker(QThread):
    ready = Signal(object, object)
    def __init__(self, videos, cache):
        super().__init__()
        self.videos, self.cache = videos, cache
    def run(self):
        for video in self.videos:
            if self.isInterruptionRequested():
                break
            from dataclasses import replace
            path = thumbnail(replace(video, thumbnail=None), self.cache)
            if path:
                self.ready.emit(video.path, path)

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1100, 760)
        icon = Path(__file__).resolve().parent / 'packaging' / 'dlptube.svg'
        if icon.is_file():
            self.setWindowIcon(QIcon(str(icon)))
        self.settings = QSettings(APP_NAME, APP_NAME)
        migrate_legacy_settings(self.settings)
        self.videos = []
        self.worker = None
        self.thumb_worker = None
        self.thumbs = {}
        self.items = {}
        self.full = False
        self.closing = False
        self.pending_folder = None
        self.play_queue = []
        self.play_index = -1
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        library = QWidget()
        layout = QVBoxLayout(library)
        top = QHBoxLayout()
        self.folder = QPushButton('Open archive…')
        self.folder.clicked.connect(self.choose)
        self.reload = QPushButton('Rescan')
        self.reload.clicked.connect(lambda: self.load(self.settings.value('folder', '')))
        self.shuffle = QPushButton('Shuffle grid')
        self.shuffle.clicked.connect(self.fill_grid)
        self.status = QLabel('Choose your yt-dlp archive folder')
        self.status.setWordWrap(True)
        for w in (self.folder, self.reload, self.shuffle): top.addWidget(w)
        top.addWidget(self.status, 1)
        layout.addLayout(top)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search videos…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.filter_videos)
        layout.addWidget(self.search)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.ordered = QListWidget()
        self.ordered.setIconSize(QSize(144, 81))
        self.grid = QListWidget()
        self.grid.setViewMode(QListWidget.ViewMode.IconMode)
        self.grid.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.grid.setMovement(QListWidget.Movement.Static)
        self.grid.setIconSize(QSize(208, 117))
        self.grid.setGridSize(QSize(232, 172))
        self.grid.setWordWrap(True)
        self.tabs.addTab(self.ordered, 'Playlist')
        self.tabs.addTab(self.grid, 'Random grid')
        for view in (self.ordered, self.grid):
            view.itemClicked.connect(self.open_video)
            view.itemActivated.connect(self.open_video)
            view.setUniformItemSizes(True)
            palette = view.palette()
            for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive):
                palette.setColor(group, QPalette.ColorRole.HighlightedText, QColor('#eeeeee'))
            view.setPalette(palette)
        self.stack.addWidget(library)
        page = QWidget()
        self.play_layout = play_layout = QVBoxLayout(page)
        self.normal_margins = play_layout.contentsMargins()
        self.normal_spacing = play_layout.spacing()
        self.header_widget = QWidget()
        header = QHBoxLayout(self.header_widget)
        header.setContentsMargins(0, 0, 0, 0)
        back = QPushButton('← Library')
        back.clicked.connect(self.back)
        self.title = QLabel()
        self.title.setWordWrap(True)
        header.addWidget(back)
        header.addWidget(self.title, 1)
        play_layout.addWidget(self.header_widget)
        self.screen = QVideoWidget()
        play_layout.addWidget(self.screen, 1)
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.screen)
        self.seek = QSlider(Qt.Orientation.Horizontal)
        self.seek.sliderMoved.connect(self.player.setPosition)
        play_layout.addWidget(self.seek)
        self.controls_widget = QWidget()
        controls = QHBoxLayout(self.controls_widget)
        controls.setContentsMargins(0, 0, 0, 0)
        self.toggle = QPushButton('Play')
        self.toggle.clicked.connect(self.toggle_play)
        self.time = QLabel('0:00 / 0:00')
        volume = QSlider(Qt.Orientation.Horizontal)
        volume.setRange(0, 100)
        volume.setMaximumWidth(140)
        volume.setValue(int(self.settings.value('volume', 70)))
        self.audio.setVolume(volume.value()/100)
        volume.valueChanged.connect(self.set_volume)
        full = QPushButton('Fullscreen')
        full.clicked.connect(self.fullscreen)
        for w in (self.toggle, self.time): controls.addWidget(w)
        controls.addStretch()
        self.autoplay = QCheckBox('Autoplay')
        self.autoplay.setChecked(self.settings.value('autoplay', False, type=bool))
        self.autoplay.toggled.connect(lambda enabled: self.settings.setValue('autoplay', enabled))
        controls.addWidget(self.autoplay)
        for w in (QLabel('Volume'), volume, full): controls.addWidget(w)
        play_layout.addWidget(self.controls_widget)
        self.description_button = QPushButton('Show description')
        self.description_button.setCheckable(True)
        self.description_button.toggled.connect(self.show_description)
        play_layout.addWidget(self.description_button)
        self.description = QPlainTextEdit()
        self.description.setReadOnly(True)
        self.description.setMaximumHeight(180)
        self.description.hide()
        play_layout.addWidget(self.description)
        self.stack.addWidget(page)
        self.player.positionChanged.connect(self.update_time)
        self.player.durationChanged.connect(self.update_duration)
        self.player.mediaStatusChanged.connect(self.on_media_status)
        self.player.playbackStateChanged.connect(lambda state: self.toggle.setText('Pause' if state == QMediaPlayer.PlaybackState.PlayingState else 'Play'))
        self.player.errorOccurred.connect(lambda error, message: QMessageBox.warning(self, 'Playback error', message))
        self.space = QShortcut(QKeySequence('Space'), page)
        self.space.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.space.activated.connect(self.toggle_play)
        self.space.setAutoRepeat(False)
        self.full_shortcut = QShortcut(QKeySequence("F"), page)
        self.full_shortcut.activated.connect(self.fullscreen)
        self.escape = QShortcut(QKeySequence('Escape'), self)
        self.escape.activated.connect(self.escape_action)
        self.setStyleSheet('''QWidget {background:#171717;color:#eeeeee;font-size:14px;} QPushButton {background:#303030;border:0;padding:9px 14px;border-radius:6px;} QPushButton:hover {background:#454545;} QPushButton:disabled {color:#777;} QListWidget {border:0;outline:0;} QListWidget::item {padding:5px;border-radius:6px;} QListWidget::item:hover, QListWidget::item:selected {background:#333;color:#eeeeee;} QListWidget::item:selected:!active {background:#333;color:#eeeeee;} QTabBar::tab {padding:12px 24px;background:#222;} QTabBar::tab:selected {background:#404040;} QTabWidget::pane {border:0;}''')
        self.search.setStyleSheet("QLineEdit {background:#252525; border:1px solid #454545; border-radius:6px; padding:9px 12px;}")
        QApplication.instance().installEventFilter(self)
        saved = self.settings.value('folder', '')
        if saved: self.load(saved)
    def choose(self):
        path = QFileDialog.getExistingDirectory(self, 'Select yt-dlp archive', self.settings.value('folder', ''))
        if path: self.load(path)
    def load(self, path):
        if not path or (self.worker and self.worker.isRunning()): return
        if self.thumb_worker and self.thumb_worker.isRunning():
            self.thumb_worker.requestInterruption()
            self.pending_folder = path
            self.status.setText('Stopping thumbnail generation before rescanning…')
            self.folder.setEnabled(False)
            self.reload.setEnabled(False)
            return
        self.status.setText('Scanning archive…')
        self.folder.setEnabled(False)
        self.reload.setEnabled(False)
        self.worker = Scanner(Path(path))
        self.worker.done.connect(self.loaded)
        self.worker.failed.connect(self.failed)
        self.worker.finished.connect(lambda: self.folder.setEnabled(True))
        self.worker.finished.connect(lambda: self.reload.setEnabled(True))
        self.worker.start()
    def loaded(self, videos, warnings):
        self.settings.setValue('folder', str(self.worker.root))
        self.videos = videos
        self.status.setText(f'{len(videos)} videos · {len(warnings)} unreadable metadata files')
        self.status.setToolTip('\n'.join(warnings))
        self.thumbs.clear()
        self.items.clear()
        self.ordered.clear()
        for i, video in enumerate(videos, 1):
            self.add_item(self.ordered, video, f'{i}. ')
        self.fill_grid()
        missing = [v for v in videos if v.path not in self.thumbs]
        if missing and shutil.which('ffmpeg'):
            cache = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)) / 'thumbnails'
            self.thumb_worker = ThumbnailWorker(missing, cache)
            self.thumb_worker.ready.connect(self.thumbnail_ready)
            self.thumb_worker.finished.connect(self.thumbnails_finished)
            self.thumb_worker.start()
        elif missing:
            self.status.setText(self.status.text() + ' · Install ffmpeg for missing thumbnails')
    def thumbnails_finished(self):
        if self.pending_folder and not self.closing:
            path, self.pending_folder = self.pending_folder, None
            self.load(path)
    def thumbnail_ready(self, path, thumbnail_path):
        self.thumbs[path] = thumbnail_path
        for item in self.items.get(path, {}).values():
            item.setIcon(QIcon(str(thumbnail_path)))
    def failed(self, message):
        self.status.setText(message)
    def add_item(self, view, video, prefix=''):
        item = QListWidgetItem(f'{prefix}{video.title}\n{video.channel}  ·  {clock(video.duration*1000)}')
        item.setData(Qt.ItemDataRole.UserRole, video)
        item.setToolTip(video.title)
        path = self.thumbs.get(video.path) or video.thumbnail
        if path and not QPixmap(str(path)).isNull():
            self.thumbs[video.path] = path
            item.setIcon(QIcon(str(path)))
        else:
            pix = QPixmap(view.iconSize())
            pix.fill(Qt.GlobalColor.darkGray)
            item.setIcon(QIcon(pix))
        item.setForeground(QColor("#eeeeee"))
        view.addItem(item)
        self.items.setdefault(video.path, {})[view] = item
        item.setHidden(not self.matches_search(video))
    def matches_search(self, video):
        query = self.search.text().strip().casefold()
        return query in video.title.casefold() or query in video.path.name.casefold()
    def filter_videos(self, _text):
        for view in (self.ordered, self.grid):
            for i in range(view.count()):
                item = view.item(i)
                video = item.data(Qt.ItemDataRole.UserRole)
                item.setHidden(not self.matches_search(video))
    def fill_grid(self):
        videos = self.videos.copy()
        random.shuffle(videos)
        for views in self.items.values():
            views.pop(self.grid, None)
        self.grid.clear()
        for video in videos: self.add_item(self.grid, video)
    def open_video(self, item):
        if self.stack.currentIndex() == 1:
            return
        video = item.data(Qt.ItemDataRole.UserRole)
        if not video.path.is_file():
            QMessageBox.warning(self, 'Video unavailable', 'Reconnect your HDD and rescan if its mount path changed.')
            return
        view = item.listWidget()
        visible = [view.item(i) for i in range(view.count()) if not view.item(i).isHidden()]
        self.play_queue = [entry.data(Qt.ItemDataRole.UserRole) for entry in visible]
        self.play_index = visible.index(item)
        for view in (self.ordered, self.grid):
            view.clearSelection()
            view.setCurrentItem(None)
            view.viewport().update()
        self.stack.setCurrentIndex(1)
        self.play_video(video)
    def play_video(self, video):
        self.title.setText(video.title)
        self.description.setPlainText(video.description or 'No description saved for this video.')
        self.description_button.setChecked(False)
        self.player.setSource(QUrl.fromLocalFile(str(video.path)))
        self.player.play()
    def on_media_status(self, status):
        if (status != QMediaPlayer.MediaStatus.EndOfMedia
                or self.stack.currentIndex() != 1
                or not self.autoplay.isChecked()
                or self.play_index < 0 or self.closing):
            return
        next_index = self.play_index + 1
        if next_index >= len(self.play_queue):
            return
        video = self.play_queue[next_index]
        if not video.path.is_file():
            QMessageBox.warning(self, 'Video unavailable', 'Reconnect your HDD to continue playback.')
            return
        self.play_index = next_index
        self.play_video(video)
    def eventFilter(self, watched, event):
        # Handle seeking even when a slider or description has keyboard focus.
        if (event.type() in (QEvent.Type.ShortcutOverride, QEvent.Type.KeyPress)
                and self.stack.currentIndex() == 1
                and QApplication.activeWindow() is self
                and QApplication.activeModalWidget() is None
                and event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right)
                and event.modifiers() in (Qt.KeyboardModifier.NoModifier, Qt.KeyboardModifier.KeypadModifier)):
            if event.type() == QEvent.Type.KeyPress and self.player.isSeekable():
                delta = -10000 if event.key() == Qt.Key.Key_Left else 10000
                position = max(0, min(self.player.duration(), self.player.position() + delta))
                self.player.setPosition(position)
            event.accept()
            return True
        return super().eventFilter(watched, event)
    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState: self.player.pause()
        else: self.player.play()
    def update_time(self, position):
        if not self.seek.isSliderDown(): self.seek.setValue(position)
        self.time.setText(f'{clock(position)} / {clock(self.player.duration())}')
    def update_duration(self, duration):
        self.seek.setRange(0, duration)
        self.update_time(self.player.position())
    def set_volume(self, value):
        self.audio.setVolume(value/100)
        self.settings.setValue('volume', value)
    def show_description(self, checked):
        self.description_button.setText('Hide description' if checked else 'Show description')
        self.description.setVisible(checked and not self.full)
    def fullscreen(self):
        if self.stack.currentIndex() != 1:
            return
        self.full = not self.full
        for widget in (self.header_widget, self.seek, self.controls_widget, self.description_button):
            widget.setVisible(not self.full)
        self.description.setVisible(not self.full and self.description_button.isChecked())
        if self.full:
            self.was_maximized = self.isMaximized()
            self.play_layout.setContentsMargins(0, 0, 0, 0)
            self.play_layout.setSpacing(0)
            self.showFullScreen()
        else:
            self.play_layout.setContentsMargins(self.normal_margins)
            self.play_layout.setSpacing(self.normal_spacing)
            self.showMaximized() if self.was_maximized else self.showNormal()
    def escape_action(self):
        if self.full: self.fullscreen()
        elif self.stack.currentIndex() == 1: self.back()
    def back(self):
        self.play_queue = []
        self.play_index = -1
        if self.full: self.fullscreen()
        self.player.stop()
        self.player.setSource(QUrl())
        self.stack.setCurrentIndex(0)
        for view in (self.ordered, self.grid):
            view.viewport().update()
    def closeEvent(self, event):
        self.pending_folder = None
        if self.worker and self.worker.isRunning():
            self.status.setText('Scan still running; close after it finishes.')
            event.ignore()
        elif self.thumb_worker and self.thumb_worker.isRunning():
            event.ignore()
            self.thumb_worker.requestInterruption()
            if not self.closing:
                self.closing = True
                self.thumb_worker.finished.connect(self.close)
            self.status.setText('Finishing current thumbnail before closing…')
        else:
            self.play_queue = []
            self.play_index = -1
            self.player.stop()
            event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    icon = Path(__file__).resolve().parent / 'packaging' / 'dlptube.svg'
    app.setWindowIcon(QIcon(str(icon)))
    window = Window()
    window.show()
    sys.exit(app.exec())
