<p align="center">
  <img align="center" alt="Logo" src="icon-large.svg" width=256>
</p>

# DMD Page Builder

Create Images for [DMD Page Loader](https://github.com/meowmeowahr/DMD_PageLoader)

# Features

* Load 32x32 image in 12 different formats
* Built-in example images
* Screen preview
* Export DMD v2

## DMD File Format

| Byte Range             | Description                  |
|------------------------|------------------------------|
| 0 (h0)                 | Page Time Multiplier         |
| 1 (h1) ... 1024 (h400) | Image Data (0 = OFF, 1 = ON) |