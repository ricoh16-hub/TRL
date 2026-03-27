import math
import os
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QGraphicsDropShadowEffect
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QConicalGradient, QRegion, QPainterPath, QRadialGradient, QPaintEvent

class CircularProgress(QWidget):
    def __init__(self, diameter: int = 120, parent: QWidget | None = None):
        super().__init__(parent)
        self.diameter = diameter
        self.angle = 0
        self.base_thickness = 2.0
        self.amp_thickness = 0.4
        self.pulse_period = 2200  # ms (luxury breathing)
        self.rotation_period = 1400  # ms (smooth rotation)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_anim)
        self.timer.start(16)  # ~60 FPS
        self.setFixedSize(diameter, diameter)
        self._t = 0
        # Stroke dash animation
        self.arc_anim_period = 2000  # ms (luxury arc motion)
        self.arc_min_span = 36       # degrees
        self.arc_max_span = 288      # degrees
        self.arc_start_angle = 0
        self.arc_span_angle = self.arc_min_span
        # Glow/Drop Shadow Effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180))  # Lebih gelap, lebih terlihat
        shadow.setOffset(6, 6)
        self.setGraphicsEffect(shadow)

    def update_anim(self):
        self._t += 16
        # Circular Rotational Motion
        self.angle = (self.angle + 360 * 16 / self.rotation_period) % 360
        # Luxury breathing thickness
        phase = ((self._t % self.pulse_period) / self.pulse_period) * 2 * math.pi
        self.thickness = self.base_thickness + self.amp_thickness * math.sin(phase)
        # Stroke Dash Animation + Ease-in-out Curve
        arc_phase = ((self._t % self.arc_anim_period) / self.arc_anim_period)
        def ease_in_out(t: float) -> float:
            return 0.5 * (1 - math.cos(math.pi * t))
        if arc_phase < 0.5:
            eased = ease_in_out(arc_phase * 2)
            self.arc_span_angle = self.arc_min_span + (self.arc_max_span - self.arc_min_span) * eased
        else:
            eased = ease_in_out((1 - arc_phase) * 2)
            self.arc_span_angle = self.arc_min_span + (self.arc_max_span - self.arc_min_span) * eased
        self.arc_start_angle = (self.angle + 90 + 360 * arc_phase) % 360
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            # Luxury gradient, hue stability
            rect = QRectF(self.thickness, self.thickness, self.diameter-2*self.thickness, self.diameter-2*self.thickness)
            grad = QConicalGradient(rect.center(), -self.angle)
            # Kemewahan: gradasi biru aqua, platinum, royal blue, emas, putih
            aqua = QColor(62, 166, 255)
            aqua.setAlpha(0)
            platinum = QColor(180,220,255)
            royal = QColor(60,120,255)
            gold = QColor(255,215,80)
            white = QColor(255,255,255)
            grad.setColorAt(0.0, aqua)
            grad.setColorAt(0.25, platinum)
            grad.setColorAt(0.45, royal)
            grad.setColorAt(0.65, gold)
            grad.setColorAt(0.85, white)
            grad.setColorAt(1.0, aqua)
            pen = QPen()
            pen.setBrush(grad)
            pen.setWidthF(self.thickness)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            # Draw glow under arc for extra luxury
            glow_pen = QPen(QColor(62,166,255,30))
            glow_pen.setWidthF(self.thickness*1.5)
            glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(glow_pen)
            painter.drawArc(rect, int(self.arc_start_angle*16), int(self.arc_span_angle*16))
            # Draw main arc
            painter.setPen(pen)
            painter.drawArc(rect, int(self.arc_start_angle*16), int(self.arc_span_angle*16))
            # Draw shimmer highlight (arc shine)
            shimmer_pen = QPen(QColor(255,255,255,180))
            shimmer_pen.setWidthF(self.thickness*0.55)
            shimmer_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(shimmer_pen)
            shimmer_start = self.arc_start_angle + self.arc_span_angle*0.18
            shimmer_span = self.arc_span_angle*0.13
            painter.drawArc(rect, int(shimmer_start*16), int(shimmer_span*16))
            # Glow for logo globe
            globe = getattr(self.parent(), 'globe_widget', None)
            if globe is not None:
                globe_effect = QGraphicsDropShadowEffect()
                globe_effect.setBlurRadius(24)
                globe_effect.setColor(QColor(180,220,255,120))
                globe_effect.setOffset(0, 0)
                globe.setGraphicsEffect(globe_effect)
            # Glow for particles
            # ...existing code...
            # After drawing each particle ellipse:
            # glow_pen = QPen(QColor(255,255,255,80))
            # painter.setPen(glow_pen)
            # painter.drawEllipse(QPointF(particle_x, particle_y), particle_size*1.7, particle_size*1.7)
            # painter.restore() jika sebelumnya ada painter.save()
        except Exception as e:
            import traceback
            print('[ERROR] paintEvent CircularProgress:', e)
            traceback.print_exc()



# --- Circular text widget for animated status ---
class CircularText(QWidget):
    def __init__(self, text_list: list[str], diameter: int, parent: QWidget | None = None, child_widget: QWidget | None = None):
        super().__init__(parent)
        self.text_list = text_list
        self.current_index = 0
        self.angle = 0
        self.diameter = diameter
        self.setFixedSize(diameter, diameter)
        self.child_widget = child_widget  # Add child_widget attribute
        
        # Formation timing for 3s animation showcase + 2s branding
        self.start_time = None
        self.formation_complete = False
        self.formation_duration = 3000  # 3 seconds for full animation showcase
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_angle)
        self.timer.start(16)
    def set_text_index(self, idx: int):
        self.current_index = idx % len(self.text_list)
        self.update()
    def update_angle(self):
        # Initialize start time on first call
        if self.start_time is None:
            from PySide6.QtCore import QTime
            self.start_time = QTime.currentTime()
        
        # Calculate elapsed time in milliseconds
        from PySide6.QtCore import QTime
        current_time = QTime.currentTime()
        elapsed_ms = self.start_time.msecsTo(current_time)
        
        # Check if formation is complete (6.5 seconds)
        if elapsed_ms >= self.formation_duration:
            if not self.formation_complete:
                self.formation_complete = True
                self.angle = 0  # Perfect alignment
                self.update()  # Final update
            return  # Stop rotation
        
        # Continue rotation only if formation is not complete
        self.angle = (self.angle - 6) % 360  # Counter-clockwise rotation
        self.update()
    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Efek depth blur (bokeh) di belakang lingkaran
        bokeh_center = self.rect().center()
        bokeh_layers = [
            (self.rect().width()//2 - 10, 80, 0.18),
            (self.rect().width()//2 - 30, 120, 0.12),
            (self.rect().width()//2 - 50, 180, 0.08),
            (self.rect().width()//2 - 70, 255, 0.05)
        ]
        for radius, alpha, opacity in bokeh_layers:
            color = QColor(255,255,255,alpha)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.setOpacity(opacity)
            painter.drawEllipse(bokeh_center, radius, radius)
        painter.setOpacity(1.0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        font = painter.font()
        font.setFamily('SF Pro Display')
        font.setPointSize(5)
        font.setBold(True)
        painter.setFont(font)
        color = QColor(255,255,255)
        painter.setPen(color)
        # Particle rendering handled by self._draw_rectangle_particles
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        thickness = getattr(self, 'base_thickness', 2.0)
        margin = thickness + 4
        rect = self.rect().adjusted(int(margin), int(margin), -int(margin), -int(margin))
        liquid_length = 215
        liquid_angle = self.angle
        base = 1.875
        # Reduce dynamic effects when formation is complete
        if self.formation_complete:
            dynamic = 1.0  # Static thickness
        else:
            dynamic = 1.2 + 0.8 * math.sin(liquid_angle * math.pi / 180)
        liquid_thickness = base * dynamic
        self._draw_arcs(painter, QRectF(rect), liquid_angle, liquid_length, liquid_thickness)
        # self._draw_caustics(painter, rect)  # Caustics Effect dinonaktifkan
        # Skip dynamic effects when formation is complete
        # Particle rendering is currently disabled due to missing implementation
        # if not self.formation_complete:
        #     self._draw_particles(painter, rect, liquid_angle, liquid_length)
        # if hasattr(self, '_draw_embers'):
        #     self._draw_embers(painter, rect)

        # Draw strong visible shadow for rounded rectangle
        shadow_rect = self.rect().adjusted(int(margin), int(margin), -int(margin), -int(margin))
        shadow_radius = (shadow_rect.width()) * 0.2
        shadow_offset_x = 6
        shadow_offset_y = 8
        shadow_path = QPainterPath()
        shadow_path.addRoundedRect(
            shadow_rect.translated(shadow_offset_x, shadow_offset_y),
            shadow_radius + 6,
            shadow_radius + 6
        )
        grad = QRadialGradient(
            shadow_rect.center().x() + shadow_offset_x,
            shadow_rect.center().y() + shadow_offset_y + 8,
            shadow_rect.width() * 0.8
        )
        grad.setColorAt(0.0, QColor(0, 0, 0, 180))
        grad.setColorAt(0.5, QColor(0, 0, 0, 120))
        grad.setColorAt(0.8, QColor(0, 0, 0, 60))
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(grad)
        painter.drawPath(shadow_path)
        painter.restore()
        # Draw animated rounded rectangle outer layer FIRST
        self._draw_animated_rounded_rectangle_layer(painter)

        # Then apply circular clipping for the logo
        painter.setClipRegion(QRegion(self.rect(), QRegion.RegionType.Ellipse))
        # Render logo with circular mask
        from PySide6.QtCore import QPoint
        if hasattr(self, 'child_widget') and isinstance(self.child_widget, QWidget):
            self.child_widget.render(painter, QPoint(0, 0))

    def _draw_arcs(
        self,
        painter: QPainter,
        rect: QRectF,
        angle: float,
        length: float,
        thickness: float
    ) -> None:
        """
        Draws a circular arc with the given parameters.
        """
        painter.save()
        pen = QPen(QColor(62, 166, 255, 220))
        pen.setWidthF(thickness)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        # Calculate start and span angles for the arc
        start_angle = (angle + 90) % 360
        span_angle = length
        painter.drawArc(rect, int(start_angle * 16), int(span_angle * 16))
        painter.restore()
        
    def _draw_animated_rounded_rectangle_layer(self, painter: QPainter) -> None:
        """
        Draw animated rounded rectangle border dengan efek rotasi, caustics, dan hardening.
        Efek border dan partikel dipanggil dari fungsi terpisah.
        """
        center_x = self.diameter // 2
        center_y = self.diameter // 2
        rect_size = self.diameter * 0.85 * getattr(self, 'pulse_scale', 1.0)
        rect_x = center_x - rect_size // 2
        rect_y = center_y - rect_size // 2
        corner_radius = rect_size * 0.2
        rounded_rect = QPainterPath()
        rounded_rect.addRoundedRect(rect_x, rect_y, rect_size, rect_size, corner_radius, corner_radius)
        painter.save()
        if not getattr(self, 'formation_complete', False):
            painter.translate(center_x, center_y)
            painter.rotate(getattr(self, 'animation_angle', 0))
            painter.translate(-center_x, -center_y)
                    # Perfect alignment logic removed
        self._draw_rectangle_border_layers(painter, rounded_rect)
        # --- Animated particles ---
        if not getattr(self, 'formation_complete', False):
            self._draw_rectangle_particles(painter, rect_x, rect_y, rect_size, corner_radius)
        painter.restore()

    def _draw_rectangle_border_layers(self, painter: QPainter, rounded_rect: QPainterPath) -> None:
        """Draw multiple border layers for glow effect"""
        # Layer 1: Premium outline (platinum)
        painter.setPen(QPen(QColor(220, 220, 235, int(220 * 0.22)), 0.012, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(rounded_rect)

        # Layer 2: Gold gradient glow (ukuran diperbesar 5x)
        from PySide6.QtGui import QLinearGradient
        grad = QLinearGradient(rounded_rect.boundingRect().left(), rounded_rect.boundingRect().top(), rounded_rect.boundingRect().right(), rounded_rect.boundingRect().bottom())
        grad.setColorAt(0.0, QColor(255, 215, 80, int(120 * 0.28)))  # Gold, lebih tebal
        grad.setColorAt(0.5, QColor(180, 220, 255, int(80 * 0.18)))  # Platinum
        grad.setColorAt(1.0, QColor(60, 120, 255, int(100 * 0.22)))  # Royal blue
        painter.setPen(QPen(grad, 0.12, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(rounded_rect)

        # Layer 3: Extended luxury glow (soft blur, diperbesar 5x)
        for i in range(3):
            alpha = int(60 * (1 - i / 3) * 0.18)
            width_val = (1.6 + i * 2.6) * 0.0825
            if i == 0:
                color = QColor(255, 215, 80, alpha)  # Gold
            elif i == 1:
                color = QColor(180, 220, 255, alpha)  # Platinum
            else:
                color = QColor(60, 120, 255, alpha)  # Royal blue
            painter.setPen(QPen(color, width_val, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(rounded_rect)
    # Layer 4: Dynamic highlight shimmer (disabled, removed by user request)
    # (Efek highlight berputar searah jarum jam telah dihapus)

        # Layer 5: Subtle multi-layer blur (luxury aura)
        for i in range(2):
            painter.setPen(QPen(QColor(255, 255, 255, int(18 * 0.18)), (2.2 + i * 2.2) * 0.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(rounded_rect)
        
    def _draw_rectangle_particles(
        self,
        painter: QPainter,
        rect_x: float,
        rect_y: float,
        rect_size: float,
        corner_radius: float
    ) -> None:
        """Draw animated particles around rectangle perimeter"""
        particle_count = 12
        
        particle_color = QColor(62, 166, 255, 180)  # Aqua blue with some transparency
        for i in range(particle_count):
            # Calculate position on rounded rectangle perimeter
            t = (i / particle_count + getattr(self, 'animation_angle', 0) / 360) % 1.0
            particle_x, particle_y = self._get_rounded_rect_perimeter_point(
                t, rect_x, rect_y, rect_size, corner_radius
            )
            particle_x = float(particle_x)
            particle_y = float(particle_y)
            # Particle animation
            pulse = 0.5 + 0.5 * math.sin(getattr(self, 'animation_angle', 0) * math.pi / 180 + i * 0.8)
            particle_size = 1.5 + 1.0 * pulse
            particle_alpha = int(150 + 105 * pulse)
            painter.setBrush(particle_color)
            painter.drawEllipse(
                QPointF(particle_x, particle_y), 
                particle_size, particle_size
            )
            # Particle glow
            glow_size = particle_size * 2.0
            glow_alpha = int(particle_alpha * 0.3)
            glow_color = QColor(255, 255, 255, glow_alpha)
            painter.setBrush(glow_color)
            painter.drawEllipse(
                QPointF(particle_x, particle_y),
                glow_size, glow_size
            )
    
    def _get_rounded_rect_perimeter_point(
        self,
        t: float,
        rect_x: float,
        rect_y: float,
        size: float,
        corner_radius: float
    ) -> tuple[float, float]:
        """Get point on rounded rectangle perimeter based on parameter t (0-1)"""
        width = height = size
        straight_width = width - 2 * corner_radius
        straight_height = height - 2 * corner_radius
        perimeter_progress = t * 4  # 4 sides
        if perimeter_progress < 1:  # Top edge
            progress = perimeter_progress
            x = rect_x + corner_radius + progress * straight_width
            y = rect_y
        elif perimeter_progress < 2:  # Right edge
            progress = perimeter_progress - 1
            x = rect_x + width
            y = rect_y + corner_radius + progress * straight_height
        elif perimeter_progress < 3:  # Bottom edge
            progress = perimeter_progress - 2
            x = rect_x + width - corner_radius - progress * straight_width
            y = rect_y + height
        else:  # Left edge
            progress = perimeter_progress - 3
            x = rect_x
            y = rect_y + height - corner_radius - progress * straight_height
        return x, y

# --- Enhanced Circle mask widget with rounded rectangle outer layer ---
class CircleMaskWidget(QWidget):
    def __init__(self, child_widget: QWidget, diameter: int):
        super().__init__()
        self.child = child_widget
        self.diameter = diameter
        self.child.setParent(self)
        self.child.setGeometry(0, 0, diameter, diameter)
        self.setFixedSize(diameter, diameter)
        # Tidak ada animasi border rounded rectangle, hanya circular mask

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Hanya circular mask, tanpa border
        painter.setClipRegion(QRegion(self.rect(), QRegion.RegionType.Ellipse))
        from PySide6.QtCore import QPoint
        self.child.render(painter, QPoint(0, 0))

# --- Glow mask widget with radial gradient ---
class GlowMaskWidget(QWidget):
    def __init__(self, child_widget: QWidget, diameter: int, glow_color: QColor = QColor(255,255,255,90), parent: QWidget | None = None):
        super().__init__(parent)
        self.child_widget = child_widget
        self.diameter = diameter
        self.glow_color = glow_color
        self.setFixedSize(diameter, diameter)
        self.child_widget.setParent(self)
        self.child_widget.move(0, 0)
    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QRadialGradient(self.diameter/2, self.diameter/2, self.diameter/2 * 0.7)  # Glow radius lebih kecil
        grad.setColorAt(0.0, QColor(255,255,255,0))
        grad.setColorAt(0.7, self.glow_color)
        grad.setColorAt(1.0, QColor(255,255,255,0))
        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, self.diameter, self.diameter)
        # Child widget (globe) will be drawn automatically

# --- Main boot window ---
class AcrylicWindow(QDialog):

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setFixedSize(405, int(18.5 * 0.3937 * 96))  # Samakan dengan lock.py
        # Tempatkan window di tengah layar
        screen = QApplication.primaryScreen().geometry()
        x = int((screen.width() - self.width()) / 2)
        y = int((screen.height() - self.height()) / 2)
        self.move(x, y)
        # Efek kaca/transparan dan rounded rectangle
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #222a36, stop:1 #3a4a5c);
                border-radius: 24px;
                border: 1px solid rgba(255,255,255,0.18);
            }
            QLabel {
                color: white;
                font-family: 'SF Pro Display';
                font-size: 16px;
            }
        """)

        # Logo globe
        spinner_diameter = int(100 * 0.65 * 1.1)  # Perbesar diameter spinner 10%
        globe_diameter = 92  # fixed globe diameter, never changes again
        globe_area = math.pi * (globe_diameter / 2) ** 2
        print(f"Luas lingkaran logo globe: {globe_area:.2f} px^2, diameter: {globe_diameter} px")
        logo_path = os.path.join(os.path.dirname(__file__), '../../assets/logo_splash.svg')
        self.anchor_widget = QWidget(self)
        self.anchor_widget.setFixedSize(spinner_diameter, spinner_diameter)
        self.spinner = CircularProgress(diameter=spinner_diameter, parent=self.anchor_widget)
        self.spinner.move(0, 0)
        if os.path.exists(logo_path):
            logo = QSvgWidget(logo_path, parent=self.anchor_widget)
            logo.setFixedSize(globe_diameter, globe_diameter)
            globe_widget = GlowMaskWidget(logo, globe_diameter, glow_color=QColor(255,255,255,90), parent=self.anchor_widget)
            print("✅ Logo SVG loaded successfully")
        else:
            globe_widget = QLabel("🌍", parent=self.anchor_widget)
            globe_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            globe_widget.setStyleSheet("font-size: 48px; color: cyan;")
            globe_widget.setFixedSize(globe_diameter, globe_diameter)
        # Position globe at center of spinner
        globe_x = (spinner_diameter - globe_diameter) // 2
        globe_y = (spinner_diameter - globe_diameter) // 2
        globe_widget.setFixedSize(globe_diameter, globe_diameter)
        globe_widget.move(globe_x, globe_y)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addStretch(1)
        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(0)
        hbox.addStretch(1)
        hbox.addWidget(self.anchor_widget)
        hbox.addStretch(1)
        layout.addLayout(hbox)
        layout.addStretch(1)
        self.setLayout(layout)


# --- Show boot dialog function ---
def show_boot():
    boot = AcrylicWindow()
    boot.setModal(True)
    from PySide6.QtGui import QGuiApplication
    screen = QGuiApplication.primaryScreen()
    screen_geometry = screen.geometry()
    width_px = boot.width()
    height_px = boot.height()
    boot.move(
        screen_geometry.x() + (screen_geometry.width() - width_px) // 2,
        screen_geometry.y() + (screen_geometry.height() - height_px) // 2
    )
    print("[DEBUG] Boot dialog shown.")
    from PySide6.QtCore import QTimer
    QTimer.singleShot(3000, lambda: (print("[DEBUG] Boot dialog closing."), boot.accept()))
    boot.exec()
    print("[DEBUG] Boot dialog closed.")