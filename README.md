# Gesture-Controlled Virtual Mouse and Keyboard

> A real-time touchless Human–Computer Interaction system built using **Python**, **OpenCV**, **MediaPipe**, and **PyAutoGUI**.

## Features

- 🖱️ Virtual mouse control
- ⌨️ Virtual keyboard
- 🔊 Volume & brightness control
- 📜 Scrolling
- 🤏 Drag and drop
- ⚡ Low-latency gesture recognition

## Project Structure

```text
.github/
demo_media/
gest/
src/
.gitignore
README.md
requirements.txt
```

## Installation

```bash
git clone <repo-url>
cd Gesture-Controlled-Virtual-Mouse-and-Keyboard
pip install -r requirements.txt
python src/main.py
```

## Gesture Demonstration

> Place the extracted screenshots below inside the `demo_media/` folder and keep these filenames.

| Gesture | Image | Action |
|---------|-------|--------|
| Cursor Movement | ![](demo_media/cursor_movement.png) | Move cursor using Index + Middle finger |
| Left Click | ![](demo_media/left_click.png) | Thumbs-Up |
| Double Click | ![](demo_media/double_click.png) | Index finger overlapping middle finger |
| Drag & Drop | ![](demo_media/drag_drop.png) | Closed fist |
| Volume/Brightness | ![](demo_media/volume_brightness.png) | Major hand pinch |
| Scrolling | ![](demo_media/scrolling.png) | Minor hand pinch |
| Virtual Keyboard | ![](demo_media/virtual_keyboard.png) | Shaka gesture |

## Results

Add the figures exported from your documentation into `demo_media/` and they will appear here.


![](demo_media/cursor_movement.png)

![](demo_media/drag_drop.png)

![](demo_media/volume_brightness.png)

![](demo_media/scrolling.png)

![](demo_media/keyboard_output.png)

![](demo_media/typing_output.png)

![](demo_media/left_click.png)


## Performance

| Metric | Value |
|-------|------:|
| FPS | 30–45 |
| Latency | ≤50 ms |
| Detection | 21 landmarks |
| Camera | 640×480 |
| CPU | ~20% |
| Memory | ~200 MB |

## Tech Stack

- Python
- OpenCV
- MediaPipe
- PyAutoGUI
- PyCAW
- Screen Brightness Control

## Future Work

- Multi-user support
- Custom gestures
- Better low-light performance
- Deep-learning gesture recognition

## Authors

- L. Rahul
- Mohd Abdul Muqeet
- Mohammed Abdul Matheen
- Mohammed Talha

## License

MIT License

