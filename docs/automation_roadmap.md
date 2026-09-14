# Deniz Automation Roadmap

## Overview

The **Automation Layer** is responsible for executing actions on the operating system. It acts as the bridge between the AI reasoning system and the desktop environment.

Its responsibilities include:

* Controlling the mouse and keyboard
* Managing windows and applications
* Discovering and interacting with UI elements
* Reading information from applications
* Handling dialogs and forms
* Providing OCR and computer vision fallbacks
* Supporting multiple operating systems through interchangeable backends

---

# Architecture

```
User
   │
   ▼
AI Reasoning
   │
   ▼
Planning
   │
   ▼
Execution
   │
   ▼
Automation Manager
   │
   ├── Controllers
   ├── Search Engine
   ├── Readers
   ├── Application Adapters
   ├── Vision
   └── Backend
   │
   ▼
Operating System
```

---

# Design Principles

* Platform-independent architecture
* Backend abstraction (Windows, Linux, macOS)
* Reusable controllers
* Application-specific adapters
* UI Automation first
* Vision as a fallback
* Modular and testable design

---

# Development Roadmap

---

## Phase 1 — Foundation

### Goal

Build the automation framework architecture.

### Learn

* Windows UI Automation (UIA)
* Accessibility Tree
* Win32 APIs
* pywin32
* Control Types
* UI Automation Patterns
* Coordinate systems

### Build

* Automation Manager
* Automation Session
* Base Backend
* Windows Backend
* Logging
* Error Handling

### Deliverables

* Automation manager
* Windows backend
* Basic automation pipeline

---

## Phase 2 — Window Management

### Goal

Control desktop windows.

### Features

* Find window
* Focus window
* Activate window
* Maximize
* Minimize
* Restore
* Resize
* Move
* Close
* Enumerate windows

### Deliverables

* Window Controller
* Window Reader

---

## Phase 3 — Mouse Automation

### Goal

Human-like mouse interaction.

### Features

* Move mouse
* Left click
* Right click
* Double click
* Middle click
* Drag and drop
* Hover
* Scroll
* Smooth movement

### Deliverables

* Mouse Controller

---

## Phase 4 — Keyboard Automation

### Goal

Keyboard interaction.

### Features

* Press key
* Release key
* Type text
* Keyboard shortcuts
* Copy
* Paste
* Undo
* Redo
* Select all

### Deliverables

* Keyboard Controller
* Clipboard Controller

---

## Phase 5 — UI Element Discovery

### Goal

Locate interface elements using Windows UI Automation.

### Supported Controls

* Window
* Button
* TextBox
* Label
* Menu
* Menu Item
* Checkbox
* Radio Button
* ComboBox
* Tree
* List
* Table
* Tab
* Toolbar
* Pane
* Custom Control

### Search Methods

* Name
* Automation ID
* Class Name
* Control Type
* Parent
* Children
* Regular Expression
* Path-based lookup

### Deliverables

* Finder
* Selectors
* Search cache

---

## Phase 6 — UI Interaction

### Goal

Interact with discovered controls.

### Features

* Click element
* Invoke action
* Set text
* Clear text
* Toggle checkbox
* Select radio button
* Select dropdown item
* Expand node
* Collapse node
* Scroll into view

### Deliverables

* Form Controller
* Menu Controller
* Tree Controller

---

## Phase 7 — Reading UI

### Goal

Allow Deniz to understand the current interface.

### Features

* Read text
* Read values
* Window title
* Parent element
* Child elements
* Bounding rectangle
* Selected item
* Enabled state
* Visibility state
* Focus state

### Deliverables

* UI Reader
* Element Reader
* Window Reader

---

## Phase 8 — Advanced Controls

### Goal

Support complex desktop applications.

### Components

* Tree View
* List View
* Data Grid
* Calendar
* Ribbon
* Toolbar
* Context Menu
* Status Bar
* Tabs

### Deliverables

Advanced controller support.

---

## Phase 9 — Application Adapters

### Goal

Provide high-level workflows for commonly used applications.

### Initial Applications

* File Explorer
* Chrome
* Microsoft Edge
* Visual Studio Code
* Paint
* Notepad
* Windows Terminal
* Microsoft Word
* Microsoft Excel
* Microsoft PowerPoint

### Example

Instead of:

```
Move mouse
Click
Type text
```

Deniz can execute:

```
paint.draw_rectangle()

chrome.open_tab()

explorer.open_folder()

vscode.open_workspace()
```

### Deliverables

Application-specific adapters.

---

## Phase 10 — Vision Fallback

### Goal

Support applications where UI Automation is unavailable.

### Features

* Screenshot capture
* OCR
* Region selection
* Template matching
* Image detection

### Priority Order

```
UI Automation
      ↓
Native Backend APIs
      ↓
OCR
      ↓
Template Matching
```

Vision should only be used when native automation is unavailable.

---

# Folder Structure

```
src/
└── automation/
    ├── __init__.py
    │
    ├── manager.py
    ├── session.py
    │
    ├── backends/
    │   ├── base_backend.py
    │   ├── windows_backend.py
    │   ├── linux_backend.py
    │   └── macos_backend.py
    │
    ├── controllers/
    │   ├── mouse_controller.py
    │   ├── keyboard_controller.py
    │   ├── window_controller.py
    │   ├── clipboard_controller.py
    │   ├── dialog_controller.py
    │   ├── form_controller.py
    │   ├── menu_controller.py
    │   ├── table_controller.py
    │   ├── tree_controller.py
    │   └── tab_controller.py
    │
    ├── search/
    │   ├── finder.py
    │   ├── selectors.py
    │   ├── cache.py
    │   └── filters.py
    │
    ├── readers/
    │   ├── ui_reader.py
    │   ├── window_reader.py
    │   └── element_reader.py
    │
    ├── applications/
    │   ├── chrome.py
    │   ├── edge.py
    │   ├── explorer.py
    │   ├── vscode.py
    │   ├── paint.py
    │   ├── terminal.py
    │   ├── word.py
    │   ├── excel.py
    │   └── powerpoint.py
    │
    ├── vision/
    │   ├── screenshot.py
    │   ├── ocr.py
    │   ├── template_matching.py
    │   └── regions.py
    │
    ├── models/
    └── utils/
```

---

# Long-Term Vision

The Automation Layer should never contain AI reasoning or decision-making logic.

Its responsibility is solely to execute actions requested by the Execution Layer.

```
Perception
      │
      ▼
AI Reasoning
      │
      ▼
Planning
      │
      ▼
Execution
      │
      ▼
Automation
      │
      ▼
Operating System
```

This separation ensures that Deniz remains modular, maintainable, and scalable as it evolves into a full-fledged AI desktop agent capable of interacting intelligently with applications across multiple operating systems.
